"""
Dispatch and Fulfillment Service for Ghanaian Result Checker Reseller Platform
Handles multi-channel voucher delivery: on-screen reveal, printable card,
SMS dispatch logging, and WhatsApp share formatting.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger("checker.dispatch")

OFFICIAL_PORTAL_DETAILS = {
    "WASSCE": {
        "title": "WAEC WASSCE",
        "portal_name": "Official WAEC WASSCE Checking Portal",
        "portal_url": "https://ghana.waecdirect.org",
        "rules": [
            "Card strictly allows a MAXIMUM OF 3 CHECKS.",
            "Voucher permanently binds to the 1st Candidate Index Number entered.",
            "Never refresh the page while waiting for the result slip to load to prevent burning a check."
        ]
    },
    "BECE": {
        "title": "WAEC BECE",
        "portal_name": "Official WAEC BECE eResults Portal",
        "portal_url": "https://eresults.waecgh.org",
        "rules": [
            "Valid for BECE School and Private Candidates.",
            "Maximum 3 checks allowed per voucher.",
            "Ensure you select 'BECE (School)' or 'BECE (Private)' correctly."
        ]
    },
    "CSSPS": {
        "title": "CSSPS Senior High School Placement",
        "portal_name": "Official CSSPS Placement Portal",
        "portal_url": "https://cssps.gov.gh",
        "rules": [
            "CRITICAL: Enter your 10-Digit BECE Index + 2-Digit Exam Year (12 digits total, e.g. 101010101026).",
            "Enter Candidate Date of Birth matching official school records.",
            "Self-Placement choice locks permanently once confirmed."
        ]
    },
    "CTVET": {
        "title": "CTVET / NABPTEX Examination",
        "portal_name": "Official CTVET / NABPTEX Checking Portal",
        "portal_url": "https://ctvet.gov.gh",
        "rules": [
            "Select the correct Examination Series (May/June or Nov/Dec).",
            "Provide Region and Center Code before entering Index Number."
        ]
    }
}

class DispatchManager:
    """Manages multi-channel delivery of purchased vouchers."""

    @staticmethod
    def format_on_screen_delivery(order: Dict[str, Any], vouchers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Formats the payload for immediate on-screen card reveal and download."""
        category = order.get("category", "WASSCE")
        portal_info = OFFICIAL_PORTAL_DETAILS.get(category, OFFICIAL_PORTAL_DETAILS["WASSCE"])

        cards = []
        for idx, v in enumerate(vouchers, 1):
            cards.append({
                "item_number": idx,
                "serial_number": v["serial_number"],
                "pin": v["pin"],
                "category": category,
                "portal_url": portal_info["portal_url"],
                "rules": portal_info["rules"]
            })

        return {
            "order_reference": order["order_reference"],
            "category": category,
            "category_title": portal_info["title"],
            "portal_name": portal_info.get("portal_name", portal_info["title"]),
            "portal_url": portal_info["portal_url"],
            "customer_phone": order["customer_phone"],
            "total_amount": order["total_amount"],
            "cards": cards,
            "purchased_at": datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p")
        }

    @staticmethod
    def generate_sms_text(order_ref: str, category: str, vouchers: List[Dict[str, Any]]) -> str:
        """Generates standard Ghanaian telco SMS notification text."""
        portal = OFFICIAL_PORTAL_DETAILS.get(category, OFFICIAL_PORTAL_DETAILS["WASSCE"])
        
        voucher_lines = []
        for idx, v in enumerate(vouchers, 1):
            voucher_lines.append(f"SN: {v['serial_number']} | PIN: {v['pin']}")
            
        cards_text = "\n".join(voucher_lines)
        return (
            f"VOUCHER READY ({portal['title']})\n"
            f"Order: {order_ref}\n"
            f"{cards_text}\n"
            f"Check at: {portal['portal_url']}\n"
            f"Keep PIN private. Ghana Result Checkers."
        )

    @staticmethod
    def generate_whatsapp_share_text(order_ref: str, category: str, vouchers: List[Dict[str, Any]]) -> str:
        """Formats encoded text for sharing via WhatsApp."""
        portal = OFFICIAL_PORTAL_DETAILS.get(category, OFFICIAL_PORTAL_DETAILS["WASSCE"])
        
        lines = [f"*Your {portal['title']} Result Checker* (Ref: {order_ref})"]
        for idx, v in enumerate(vouchers, 1):
            lines.append(f"Card #{idx}:")
            lines.append(f"• *Serial Number:* `{v['serial_number']}`")
            lines.append(f"• *PIN:* `{v['pin']}`")
            
        lines.append(f"\n🌐 *Check Official Portal:* {portal['portal_url']}")
        lines.append("⚠️ *Reminder:* Check official guidelines to avoid burning your attempts.")
        return "\n".join(lines)

    @classmethod
    def dispatch_sms_mock(cls, phone: str, message: str) -> Dict[str, Any]:
        """Logs simulated SMS dispatch to telco gateway (Hubtel/Arkesel/Twilio)."""
        logger.info(f"[SMS GATEWAY SIMULATION] To: {phone} | Message:\n{message}")
        return {
            "status": "SENT",
            "recipient": phone,
            "provider": "SMS_GATEWAY_SIMULATOR",
            "dispatched_at": datetime.now(timezone.utc).isoformat()
        }
