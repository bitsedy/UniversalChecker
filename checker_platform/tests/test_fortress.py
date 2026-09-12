"""
Enterprise Fortress Test Suite - CheckerPay Ghana
Validates:
1. SSRF Firewall & Educational Domain Allowlist
2. Ephemeral Memory Vault (Act 843 zero-persistence shredding)
3. Cryptographic Merkle Audit Ledger & Tamper Detection
4. Session Fingerprinting & Anti-Hijacking
5. Idempotency Lock & Duplicate Prevention
6. Webhook Signature & Pesewa-Level Reconciliation
7. Perimeter Defense & Server Cloaking (CSP, HSTS, Stripped Headers)
8. High-Concurrency Double-Spend Defense (50 parallel threads)
"""

import concurrent.futures
import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

# Point test suite to temporary isolated SQLite database
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from fastapi.testclient import TestClient
from checker_platform.main import app
from checker_platform.database import (
    init_db,
    get_db_connection,
    bulk_insert_vouchers,
    create_order,
    reserve_vouchers,
    complete_voucher_sale,
    get_order_details,
    append_audit_block,
    verify_audit_chain_integrity,
    verify_database_integrity,
    acquire_idempotency_lock,
    complete_idempotency_record
)
from checker_platform.services.security import (
    SSRFValidator,
    SSRFSecurityViolation,
    EphemeralMemoryVault,
    CryptographicAuditLedger,
    SessionFingerprinter,
    SecurityHeadersGuard,
    GENESIS_BLOCK_HASH
)
from checker_platform.services.payment import PaystackProvider


class TestFortressSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        # Clean vouchers, orders, idempotency, and audit records for predictable testing
        conn = get_db_connection()
        conn.execute("DELETE FROM transactions;")
        conn.execute("DELETE FROM vouchers;")
        conn.execute("DELETE FROM orders;")
        conn.execute("DELETE FROM idempotency_records;")
        conn.execute("DELETE FROM compliance_audit_ledger;")
        conn.commit()
        conn.close()

    # ========================================================================
    # 1. SSRF FIREWALL & OUTBOUND IP PROBING DEFENSE
    # ========================================================================

    def test_ssrf_blocks_loopback_and_internal_ips(self):
        """Validates that loopback and cloud metadata targets are aggressively blocked."""
        forbidden_targets = [
            "http://127.0.0.1:8000/admin",
            "http://localhost/internal",
            "http://169.254.169.254/latest/meta-data",
            "http://10.0.0.1/secrets",
            "http://192.168.1.1/router",
            "http://172.16.0.1/config",
            "ftp://files.example.com",
            "file:///etc/passwd"
        ]
        for url in forbidden_targets:
            with self.subTest(url=url):
                with self.assertRaises(SSRFSecurityViolation):
                    SSRFValidator.validate_url(url)

    @patch("socket.getaddrinfo")
    def test_ssrf_strict_educational_domain_allowlist(self, mock_getaddr):
        """Strict educational mode allows legitimate Ghanaian universities and blocks others."""
        mock_getaddr.return_value = [(2, 1, 6, '', ('197.255.125.10', 443))]
        valid_edu = "https://ug.edu.gh/admissions"
        validated = SSRFValidator.validate_url(valid_edu, enforce_ghana_domains=True)
        self.assertEqual(validated, valid_edu)

        unauthorized_domain = "https://evil-unauthorized-target.com/exploit"
        with self.assertRaises(SSRFSecurityViolation):
            SSRFValidator.validate_url(unauthorized_domain, enforce_ghana_domains=True)

    # ========================================================================
    # 2. EPHEMERAL MEMORY VAULT (ACT 843 ZERO-PERSISTENCE)
    # ========================================================================

    def test_ephemeral_memory_vault_zeroizes_pii(self):
        """Validates that candidate PII and grades are shredded upon context exit."""
        grades = {"English": 1, "Mathematics": 2, "Integrated Science": 1}
        secret_bytes = bytearray(b"SENSITIVE_STUDENT_ID_987654321")

        with EphemeralMemoryVault.shred_after(grades, secret_bytes):
            self.assertEqual(grades["English"], 1)
            self.assertIn(b"SENSITIVE", secret_bytes)

        # Post-scope verification: dictionaries cleared, bytearrays overwritten with null bytes
        self.assertEqual(len(grades), 0)
        self.assertTrue(all(b == 0 for b in secret_bytes))

    # ========================================================================
    # 3. CRYPTOGRAPHIC MERKLE AUDIT LEDGER & TAMPER DETECTION
    # ========================================================================

    def test_audit_ledger_hash_chain_and_tamper_detection(self):
        """Appends blocks to Merkle hash chain, verifies integrity, then tests tamper detection."""
        # Append 3 audit blocks
        h1 = append_audit_block("STUDENT_CONSENT", "0241234567", {"consent": True, "exam": "WASSCE"})
        h2 = append_audit_block("ORDER_RESERVATION", "0241234567", {"vouchers": 2, "category": "WASSCE"})
        h3 = append_audit_block("PAYMENT_FULFILLED", "0241234567", {"amount": 44.0})

        # Verify intact chain
        is_intact, block_count, msg = verify_audit_chain_integrity()
        self.assertTrue(is_intact)
        self.assertGreaterEqual(block_count, 3)

        # Artificially tamper with the payload digest of Block 2
        conn = get_db_connection()
        conn.execute(
            "UPDATE compliance_audit_ledger SET payload_digest = 'tampered_bad_digest' WHERE current_block_hash = ?",
            (h2,)
        )
        conn.commit()
        conn.close()

        # Chain verification must immediately flag cryptographic corruption
        is_intact_post_tamper, failed_block, tamper_msg = verify_audit_chain_integrity()
        self.assertFalse(is_intact_post_tamper)
        self.assertIn("Tampered block hash", tamper_msg)

    # ========================================================================
    # 4. SESSION FINGERPRINTING & ANTI-HIJACKING
    # ========================================================================

    def test_session_fingerprint_anti_hijacking(self):
        """Validates that session tokens are bound to client subnet and browser profile."""
        secret = "fortress_secret_test_key_123"
        client_ip = "197.251.130.45"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122"

        fp = SessionFingerprinter.generate_fingerprint(client_ip, user_agent, secret)
        self.assertTrue(SessionFingerprinter.verify_fingerprint(client_ip, user_agent, secret, fp))

        # Legitimate IP within same /24 cellular subnet
        same_subnet_ip = "197.251.130.99"
        self.assertTrue(SessionFingerprinter.verify_fingerprint(same_subnet_ip, user_agent, secret, fp))

        # Hijacker on completely different subnet / network
        hijacker_ip = "41.215.160.12"
        self.assertFalse(SessionFingerprinter.verify_fingerprint(hijacker_ip, user_agent, secret, fp))

        # Hijacker with altered User-Agent
        hijacker_ua = "curl/7.88.1"
        self.assertFalse(SessionFingerprinter.verify_fingerprint(client_ip, hijacker_ua, secret, fp))

    # ========================================================================
    # 5. IDEMPOTENCY LOCK & DUPLICATE PROTECTION
    # ========================================================================

    def test_idempotency_duplicate_order_prevention(self):
        """Validates that replaying an order with the same Idempotency-Key returns cached response."""
        # Seed 10 WASSCE vouchers
        vouchers = [{"serial_number": f"IDEM_WSC_{i}", "pin": f"PIN_{i:06d}"} for i in range(1, 11)]
        bulk_insert_vouchers("WASSCE", vouchers)

        idem_headers = {"Idempotency-Key": "test-idem-unique-uuid-999"}
        payload = {
            "category": "WASSCE",
            "quantity": 1,
            "customer_phone": "0241234567",
            "payment_method": "MOMO_MTN"
        }

        # First request
        res1 = self.client.post("/api/orders/create", json=payload, headers=idem_headers)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        order_ref_1 = data1["order"]["order_reference"]

        # Duplicate request with same Idempotency-Key
        res2 = self.client.post("/api/orders/create", json=payload, headers=idem_headers)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        order_ref_2 = data2["order"]["order_reference"]

        # Must return the identical order reference without reserving another voucher
        self.assertEqual(order_ref_1, order_ref_2)

        # Inspect DB: only 1 voucher reserved, not 2
        conn = get_db_connection()
        reserved_count = conn.execute("SELECT COUNT(*) FROM vouchers WHERE status = 'RESERVED'").fetchone()[0]
        conn.close()
        self.assertEqual(reserved_count, 1)

    # ========================================================================
    # 6. PAYSTACK WEBHOOK SIGNATURE & PESEWA PARITY
    # ========================================================================

    def test_webhook_pesewa_reconciliation_and_signature(self):
        """Validates HMAC-SHA512 verification and pesewa-level exact matching."""
        # Seed 1 voucher and create paid order for 22.00 GHS (2200 pesewas)
        bulk_insert_vouchers("WASSCE", [{"serial_number": "WEBHOOK_WSC_01", "pin": "PIN_123456"}])
        order_ref = "ORD_WEBHOOK_TEST_01"
        reserve_vouchers("WASSCE", 1, order_ref)
        create_order(
            order_ref=order_ref,
            category="WASSCE",
            quantity=1,
            unit_price=22.00,
            customer_phone="0241234567",
            customer_email=None,
            payment_method="PAYSTACK"
        )

        test_secret = "sk_test_fortress_secure_key_123"

        # Update DB setting to use test_secret
        from checker_platform.database import update_setting
        update_setting("paystack_secret_key", test_secret)

        # 1. Underpayment attack: payload claims 2100 pesewas instead of 2200
        underpay_body = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": order_ref,
                "amount": 2100,  # 21.00 GHS (1 GHS short!)
                "id": 99999
            }
        }).encode("utf-8")

        underpay_sig = hmac.new(test_secret.encode("utf-8"), underpay_body, hashlib.sha512).hexdigest()
        res_underpay = self.client.post(
            "/api/webhooks/paystack",
            content=underpay_body,
            headers={"X-Paystack-Signature": underpay_sig, "Content-Type": "application/json"}
        )
        self.assertEqual(res_underpay.status_code, 400)
        self.assertIn("Pesewa reconciliation failed", res_underpay.text)

        # 2. Forged signature attack
        res_forged = self.client.post(
            "/api/webhooks/paystack",
            content=underpay_body,
            headers={"X-Paystack-Signature": "forged_invalid_signature_hex", "Content-Type": "application/json"}
        )
        self.assertEqual(res_forged.status_code, 400)

        # 3. Legitimate exact payment: 2200 pesewas
        exact_body = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": order_ref,
                "amount": 2200,  # Exactly 22.00 GHS
                "id": 100001
            }
        }).encode("utf-8")

        exact_sig = hmac.new(test_secret.encode("utf-8"), exact_body, hashlib.sha512).hexdigest()
        res_exact = self.client.post(
            "/api/webhooks/paystack",
            content=exact_body,
            headers={"X-Paystack-Signature": exact_sig, "Content-Type": "application/json"}
        )
        self.assertEqual(res_exact.status_code, 200)
        self.assertEqual(res_exact.json(), {"status": "ok"})

        # Verify order was fulfilled to PAID
        order = get_order_details(order_ref)
        self.assertEqual(order["payment_status"], "PAID")

    # ========================================================================
    # 7. PERIMETER DEFENSE & SERVER CLOAKING
    # ========================================================================

    def test_security_headers_and_server_cloaking(self):
        """Validates that security headers are injected and identifying server headers stripped."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        # Injected enterprise headers
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))
        self.assertIn("max-age=63072000", res.headers.get("Strict-Transport-Security", ""))

        # Cloaked headers
        self.assertNotIn("server", res.headers)
        self.assertNotIn("x-powered-by", res.headers)

    def test_health_check_integrity_reporting(self):
        """Validates /health reports realtime SQLite integrity and audit chain status."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["integrity"]["database"]["intact"])
        self.assertTrue(data["integrity"]["audit_ledger"]["intact"])

    # ========================================================================
    # 8. HIGH-CONCURRENCY DOUBLE-SPEND DEFENSE (50 THREADS)
    # ========================================================================

    def test_50_thread_concurrency_race_condition(self):
        """
        Stress test: 50 concurrent threads contest exactly 5 available vouchers.
        Proves atomic SQLite locking guarantees exactly 5 successes and 45 rejections,
        with zero voucher collisions and zero stock overselling.
        """
        # Seed exactly 5 vouchers
        vouchers = [{"serial_number": f"RACE_VOUCHER_{i}", "pin": f"PIN_{i:06d}"} for i in range(1, 6)]
        bulk_insert_vouchers("BECE", vouchers)

        def purchase_attempt(buyer_id: int):
            order_ref = f"ORD_RACE_{buyer_id}"
            try:
                create_order(
                    order_ref=order_ref,
                    category="BECE",
                    quantity=1,
                    unit_price=18.00,
                    customer_phone=f"024999{buyer_id:04d}",
                    customer_email=None,
                    payment_method="MOMO_MTN"
                )
                reserved = reserve_vouchers("BECE", 1, order_ref)
                if reserved:
                    complete_voucher_sale(order_ref)
                    return ("SUCCESS", reserved[0]["serial_number"])
                else:
                    return ("OUT_OF_STOCK", None)
            except Exception as e:
                return ("ERROR", str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(purchase_attempt, i) for i in range(1, 51)]
            results = [f.result() for f in futures]

        successes = [r for r in results if r[0] == "SUCCESS"]
        out_of_stocks = [r for r in results if r[0] == "OUT_OF_STOCK"]

        # Exactly 5 must succeed, 45 must be safely turned away
        self.assertEqual(len(successes), 5)
        self.assertEqual(len(out_of_stocks), 45)

        # Ensure all 5 allocated vouchers are distinct (no duplicate assignment)
        allocated_serials = [r[1] for r in successes]
        self.assertEqual(len(set(allocated_serials)), 5)

        # Verify DB final state
        conn = get_db_connection()
        sold_count = conn.execute("SELECT COUNT(*) FROM vouchers WHERE category = 'BECE' AND status = 'SOLD'").fetchone()[0]
        unsold_count = conn.execute("SELECT COUNT(*) FROM vouchers WHERE category = 'BECE' AND status = 'UNSOLD'").fetchone()[0]
        conn.close()

        self.assertEqual(sold_count, 5)
        self.assertEqual(unsold_count, 0)

    # ========================================================================
    # 9. P0 AUDIT FORTIFICATIONS
    # ========================================================================

    def test_webhook_currency_arbitrage_rejection(self):
        """Validates that webhooks with non-GHS currencies (e.g. NGN, USD) are rejected."""
        from checker_platform.database import bulk_insert_vouchers, reserve_vouchers, create_order, update_setting
        bulk_insert_vouchers("WASSCE", [{"serial_number": "CURR_WSC_01", "pin": "PIN_CURR_01"}])
        order_ref = "ORD_CURR_TEST_01"
        reserve_vouchers("WASSCE", 1, order_ref)
        create_order(
            order_ref=order_ref,
            category="WASSCE",
            quantity=1,
            unit_price=22.00,
            customer_phone="0241234567",
            customer_email=None,
            payment_method="PAYSTACK"
        )
        test_secret = "sk_test_fortress_secure_key_123"
        update_setting("paystack_secret_key", test_secret)

        foreign_curr_body = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": order_ref,
                "amount": 2200,
                "currency": "NGN",
                "id": 88888
            }
        }).encode("utf-8")
        foreign_sig = hmac.new(test_secret.encode("utf-8"), foreign_curr_body, hashlib.sha512).hexdigest()
        res = self.client.post(
            "/api/webhooks/paystack",
            content=foreign_curr_body,
            headers={"X-Paystack-Signature": foreign_sig, "Content-Type": "application/json"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Currency mismatch", res.text)

    def test_admin_backdoor_eradication(self):
        """Validates that changing admin password strictly revokes default 'ghana2026'."""
        from checker_platform.database import update_setting
        from checker_platform.main import hash_password
        
        # Change password to new custom secure password
        new_pass = "ultra_secure_custom_password_2026"
        update_setting("admin_password", hash_password(new_pass))
        
        # 1. Attempt login with old default password 'ghana2026' - MUST FAIL
        res_old = self.client.get("/admin", auth=("admin", "ghana2026"))
        self.assertEqual(res_old.status_code, 401)
        
        # 2. Attempt login with new password - MUST SUCCEED
        res_new = self.client.get("/admin", auth=("admin", new_pass))
        self.assertEqual(res_new.status_code, 200)

        # Restore default for test isolation
        update_setting("admin_password", hash_password("ghana2026"))

    def test_api_and_phone_lookup_pin_masking(self):
        """Validates that GET /api/orders and phone lookups mask sensitive PINs."""
        from checker_platform.database import bulk_insert_vouchers, reserve_vouchers, create_order, complete_voucher_sale
        bulk_insert_vouchers("BECE", [{"serial_number": "MASK_BEC_01", "pin": "987654321000"}])
        order_ref = "ORD_MASK_TEST_01"
        phone = "0249876543"
        reserve_vouchers("BECE", 1, order_ref)
        create_order(
            order_ref=order_ref,
            category="BECE",
            quantity=1,
            unit_price=18.00,
            customer_phone=phone,
            customer_email=None,
            payment_method="MOMO_MTN"
        )
        complete_voucher_sale(order_ref)

        # 1. Public API lookup must return masked PIN
        res_api = self.client.get(f"/api/orders/{order_ref}")
        self.assertEqual(res_api.status_code, 200)
        api_data = res_api.json()
        self.assertTrue(api_data["vouchers"][0].get("pin_masked"))
        self.assertIn("••••••••", api_data["vouchers"][0]["pin"])
        self.assertNotIn("987654321000", api_data["vouchers"][0]["pin"])

        # 2. Phone query on /lookup must mask PIN and show security notice
        res_phone = self.client.get(f"/lookup?q={phone}")
        self.assertEqual(res_phone.status_code, 200)
        self.assertIn("Security Notice", res_phone.text)
        self.assertIn("••••••••1000", res_phone.text)
        self.assertNotIn("987654321000", res_phone.text)

        # 3. Order reference query on /lookup reveals full PIN
        res_ref = self.client.get(f"/lookup?q={order_ref}")
        self.assertEqual(res_ref.status_code, 200)
        self.assertIn("987654321000", res_ref.text)


if __name__ == "__main__":
    unittest.main()
