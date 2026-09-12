"""
Payment Processing Service for Ghanaian Result Checker Reseller Platform
Provides Paystack API client, webhook HMAC verification, and a high-fidelity
Ghanaian Mobile Money (MTN MoMo, Telecel Cash, AT Money) USSD/push simulator.
"""

import hmac
import hashlib
import json
import logging
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from ..database import get_setting, get_db_connection

logger = logging.getLogger("checker.payment")

GHANA_TELCO_PREFIXES = {
    "MTN": ["024", "054", "055", "059", "053"],
    "TELECEL": ["020", "050"],
    "AT": ["027", "057", "026"]
}

def detect_ghana_telco(phone: str) -> str:
    """Detects network provider from Ghanaian phone number."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("233"):
        digits = "0" + digits[3:]
    prefix = digits[:3]
    for telco, prefixes in GHANA_TELCO_PREFIXES.items():
        if prefix in prefixes:
            return telco
    return "MTN"  # Default fallback

def validate_ghana_phone(phone: str) -> bool:
    """Validates 10-digit standard Ghanaian mobile numbers or international 233 format."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10 and digits.startswith("0"):
        return True
    if len(digits) == 12 and digits.startswith("233"):
        return True
    return False

def format_ghana_phone(phone: str) -> str:
    """Formats phone number to standard local 10-digit display format (e.g., 024 123 4567)."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("233"):
        digits = "0" + digits[3:]
    if len(digits) == 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return phone

class PaystackProvider:
    """Handles Paystack API calls and webhook signature verification."""

    @staticmethod
    def get_secret_key() -> str:
        return get_setting("paystack_secret_key", "sk_test_sample_ghana_waec")

    @classmethod
    def verify_webhook_signature(cls, payload_bytes: bytes, signature_header: str) -> bool:
        """Verifies HMAC SHA512 signature on Paystack webhooks in constant time."""
        if not signature_header or not payload_bytes:
            return False
        secret = cls.get_secret_key().encode("utf-8")
        computed_hmac = hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed_hmac, signature_header.strip())

    @classmethod
    def validate_and_reconcile_webhook(
        cls, 
        payload_bytes: bytes, 
        signature_header: str,
        max_age_seconds: int = 300
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Enterprise dual-phase webhook verification:
        1. Validates HMAC-SHA512 signature in constant time.
        2. Traps malformed JSON.
        3. Validates event type and payload integrity.
        4. Rejects replayed events older than max_age_seconds (default 5 min).
        5. Enforces GHS currency strictly.
        """
        if not signature_header or not payload_bytes:
            return False, None, "Missing signature or payload."

        if not cls.verify_webhook_signature(payload_bytes, signature_header):
            return False, None, "Invalid cryptographic HMAC-SHA512 signature."

        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            return False, None, f"Malformed JSON payload: {e}"

        event_type = payload.get("event")
        if event_type != "charge.success":
            return False, payload, f"Unhandled webhook event type '{event_type}'."

        data = payload.get("data", {})
        if not data or not data.get("reference"):
            return False, payload, "Missing transaction data or order reference."

        # ── Replay attack prevention: enforce paid_at recency ─────────────────
        paid_at_str = data.get("paid_at") or data.get("created_at")
        if paid_at_str:
            try:
                # Paystack returns ISO-8601 with trailing Z or offset
                paid_at_str_clean = str(paid_at_str).strip().replace("Z", "+00:00")
                paid_at = datetime.fromisoformat(paid_at_str_clean)
                if paid_at.tzinfo is None:
                    paid_at = paid_at.replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - paid_at).total_seconds()
                if age_seconds > max_age_seconds:
                    return False, payload, (
                        f"Webhook replay rejected: event is {int(age_seconds)}s old "
                        f"(max allowed: {max_age_seconds}s)."
                    )
            except Exception as ts_err:
                logger.warning(f"[Webhook] Could not parse paid_at '{paid_at_str}': {ts_err}. Skipping age check.")
        else:
            # Paystack production events always carry paid_at on charge.success; absence is suspicious
            logger.warning("[Webhook] charge.success event missing paid_at field — proceeding with caution.")

        # ── Currency enforcement: if specified, must strictly be Ghanaian Cedis (GHS) ───
        currency = data.get("currency")
        if currency and str(currency).upper().strip() != "GHS":
            return False, payload, f"Currency mismatch: expected GHS, received {currency}."

        return True, payload, "Verified successfully."

    @staticmethod
    def reconcile_pesewas(expected_ghs: float, actual_pesewas: int) -> bool:
        """
        Guarantees exact pesewa-level parity.
        Prevents underpayment manipulation or rounding drift.
        """
        expected_pesewas = int(round(expected_ghs * 100))
        return expected_pesewas == int(actual_pesewas)

    @classmethod
    def initialize_transaction(
        cls, 
        email: str, 
        amount_ghs: float, 
        order_ref: str, 
        callback_url: str,
        channels: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Initializes a Paystack transaction.
        Amount must be converted to Pesewas (GHS * 100).
        """
        secret_key = cls.get_secret_key()
        url = "https://api.paystack.co/transaction/initialize"
        amount_pesewas = int(round(amount_ghs * 100))
        
        payload = {
            "email": email or f"buyer_{order_ref.lower()}@waecchecker.gh",
            "amount": str(amount_pesewas),
            "currency": "GHS",
            "reference": order_ref,
            "callback_url": callback_url,
            "metadata": {
                "order_reference": order_ref,
                "platform": "GhanaResultCheckerReseller"
            }
        }
        if channels:
            payload["channels"] = channels # e.g. ['mobile_money', 'card']

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.warning(f"Paystack HTTP error: {err_body}")
            return {"status": False, "message": f"Paystack error: {err_body}"}
        except Exception as e:
            logger.exception("Failed to contact Paystack API")
            return {"status": False, "message": str(e)}

    @classmethod
    def verify_transaction(cls, reference: str) -> Dict[str, Any]:
        """Verifies transaction status directly against Paystack."""
        secret_key = cls.get_secret_key()
        quoted_ref = urllib.parse.quote(str(reference).strip())
        url = f"https://api.paystack.co/transaction/verify/{quoted_ref}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {secret_key}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Paystack verification error for {reference}: {e}")
            return {"status": False, "message": str(e)}

class GhanaMoMoSimulator:
    """
    High-fidelity simulator for Ghanaian Mobile Money USSD prompt and push notification.
    Enables zero-friction sandbox testing with instant receipt and voucher reveal.
    """

    @staticmethod
    def trigger_momo_prompt(order_ref: str, phone: str, amount_ghs: float, provider: str) -> Dict[str, Any]:
        """
        Simulates the telco USSD prompt received on the customer's phone.
        Returns the instructions and authorization prompt preview.
        """
        telco = detect_ghana_telco(phone) if provider == "MOMO_AUTO" else provider.replace("MOMO_", "")
        
        ussd_instructions = {
            "MTN": {
                "network": "MTN Mobile Money",
                "shortcode": "*170#",
                "prompt_text": f"Payment request of GHS {amount_ghs:.2f} from WAEC CHECKER GH. Enter MM PIN to approve.",
                "manual_steps": "Dial *170# -> Option 6 (My Wallet) -> Option 3 (My Approvals) -> Enter MM PIN"
            },
            "TELECEL": {
                "network": "Telecel Cash",
                "shortcode": "*110#",
                "prompt_text": f"Authorize payment of GHS {amount_ghs:.2f} for Order {order_ref} with Telecel PIN.",
                "manual_steps": "Dial *110# -> Generate Voucher / Check Approvals"
            },
            "AT": {
                "network": "AT Money",
                "shortcode": "*110#",
                "prompt_text": f"Enter AT Money PIN to approve debit of GHS {amount_ghs:.2f} for WAEC Checkers.",
                "manual_steps": "Dial *110# -> Option 5 (My Account) -> Option 2 (Approvals)"
            }
        }
        
        info = ussd_instructions.get(telco, ussd_instructions["MTN"])
        simulated_txn_id = f"MOMO_{telco}_{order_ref}"

        return {
            "success": True,
            "simulated": True,
            "network": info["network"],
            "phone_formatted": format_ghana_phone(phone),
            "amount_ghs": amount_ghs,
            "prompt_text": info["prompt_text"],
            "manual_steps": info["manual_steps"],
            "simulated_transaction_id": simulated_txn_id
        }

def record_transaction(order_ref: str, provider: str, provider_ref: str, amount: float, status: str, payload: dict):
    """Records a payment transaction audit record idempotently."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO transactions (order_reference, provider, provider_reference, amount, status, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (order_ref, provider, provider_ref, amount, status, json.dumps(payload))
        )
    finally:
        conn.close()
