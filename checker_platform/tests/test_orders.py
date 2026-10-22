"""
Unit tests for CheckerPay Ghana - Database, Phone Validation & Order Flow
"""

import unittest
import os
import tempfile
import sqlite3

# Set test DB path before importing modules
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.database import (
    init_db,
    get_product_catalog,
    reserve_vouchers,
    complete_voucher_sale,
    create_order,
    get_order_details,
    lookup_orders_by_customer,
    bulk_insert_vouchers,
    release_expired_reservations,
    cancel_order
)
from checker_platform.services.payment import (
    validate_ghana_phone,
    detect_ghana_telco,
    GhanaMoMoSimulator
)
from checker_platform.services.dispatch import DispatchManager, format_ghana_phone

class TestOrderLifecycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_ghana_phone_validation(self):
        self.assertTrue(validate_ghana_phone("0241234567"))
        self.assertTrue(validate_ghana_phone("0509998888"))
        self.assertTrue(validate_ghana_phone("+233241234567"))
        self.assertTrue(validate_ghana_phone("233271234567"))
        self.assertFalse(validate_ghana_phone("12345"))
        self.assertFalse(validate_ghana_phone("0123456789123"))

    def test_telco_detection(self):
        self.assertEqual(detect_ghana_telco("0241112222"), "MTN")
        self.assertEqual(detect_ghana_telco("0549998888"), "MTN")
        self.assertEqual(detect_ghana_telco("0201234567"), "TELECEL")
        self.assertEqual(detect_ghana_telco("0500001111"), "TELECEL")
        self.assertEqual(detect_ghana_telco("0275556666"), "AT")

    def test_inventory_and_purchase_cycle(self):
        # Insert test vouchers
        sample_vouchers = [
            {"serial_number": "TST_WSC_001", "pin": "123456789012"},
            {"serial_number": "TST_WSC_002", "pin": "987654321098"}
        ]
        res = bulk_insert_vouchers("WASSCE", sample_vouchers)
        self.assertEqual(res["inserted"], 2)

        # Create Order
        order_ref = "ORD-TEST-001"
        order = create_order(
            order_ref=order_ref,
            category="WASSCE",
            quantity=1,
            unit_price=22.00,
            customer_phone="0241234567",
            customer_email="test@waec.gh",
            payment_method="MOMO_MTN"
        )
        self.assertEqual(order["payment_status"], "PENDING")

        # Reserve
        reserved = reserve_vouchers("WASSCE", 1, order_ref)
        self.assertIsNotNone(reserved)
        self.assertEqual(len(reserved), 1)

        # Before payment, credentials should not be exposed
        details_before = get_order_details(order_ref)
        self.assertEqual(len(details_before["vouchers"]), 0)
        self.assertEqual(details_before["vouchers_reserved_count"], 1)

        # Complete Payment
        sold = complete_voucher_sale(order_ref)
        self.assertEqual(len(sold), 1)
        self.assertEqual(sold[0]["serial_number"], reserved[0]["serial_number"])

        # After payment, credentials must be returned
        details_after = get_order_details(order_ref)
        self.assertEqual(details_after["payment_status"], "PAID")
        self.assertEqual(len(details_after["vouchers"]), 1)

        # Test lookup by customer phone
        found_orders = lookup_orders_by_customer("0241234567")
        self.assertTrue(any(o["order_reference"] == order_ref for o in found_orders))

    def test_order_cancellation_and_inventory_release(self):
        # Insert test vouchers for cancellation test
        bulk_insert_vouchers("BECE", [{"serial_number": "TST_BEC_CANCEL", "pin": "112233445566"}])
        
        cancel_ref = "ORD-TEST-CANCEL-001"
        order = create_order(
            order_ref=cancel_ref,
            category="BECE",
            quantity=1,
            unit_price=22.00,
            customer_phone="0241234567",
            customer_email="cancel@waec.gh",
            payment_method="MOMO_MTN"
        )
        self.assertEqual(order["payment_status"], "PENDING")

        # Reserve
        reserved = reserve_vouchers("BECE", 1, cancel_ref)
        self.assertEqual(len(reserved), 1)

        # Cancel the pending order
        success, msg, released = cancel_order(cancel_ref)
        self.assertTrue(success)
        self.assertEqual(released, 1)

        # Verify order marked CANCELLED
        details = get_order_details(cancel_ref)
        self.assertEqual(details["payment_status"], "CANCELLED")

        # Verify voucher was released back to UNSOLD and can be reserved again
        new_ref = "ORD-TEST-RESERVE-AFTER-CANCEL"
        re_reserved = reserve_vouchers("BECE", 1, new_ref)
        self.assertIsNotNone(re_reserved)
        self.assertEqual(re_reserved[0]["serial_number"], "TST_BEC_CANCEL")

    def test_paid_order_cannot_be_cancelled(self):
        bulk_insert_vouchers("CSSPS", [{"serial_number": "TST_CSS_PAID", "pin": "998877665544"}])
        paid_ref = "ORD-TEST-PAID-001"
        create_order(
            order_ref=paid_ref,
            category="CSSPS",
            quantity=1,
            unit_price=20.00,
            customer_phone="0241234567",
            customer_email="paid@cssps.gov.gh",
            payment_method="MOMO_MTN"
        )
        reserve_vouchers("CSSPS", 1, paid_ref)
        complete_voucher_sale(paid_ref)

        # Attempt to cancel fulfilled order must fail
        success, msg, released = cancel_order(paid_ref)
        self.assertFalse(success)
        self.assertIn("already been paid", msg)
        self.assertEqual(released, 0)

    def test_momo_prompt_generation(self):
        prompt = GhanaMoMoSimulator.trigger_momo_prompt(
            order_ref="ORD-TEST-MOMO",
            phone="0241234567",
            amount_ghs=22.0,
            provider="MOMO_MTN"
        )
        self.assertTrue(prompt["success"])
        self.assertIn("*170#", prompt["manual_steps"])

    def test_sms_phone_normalization(self):
        self.assertEqual(format_ghana_phone("024 123 4567"), "233241234567")
        self.assertEqual(format_ghana_phone("+233 24 123 4567"), "233241234567")
        self.assertEqual(format_ghana_phone("233241234567"), "233241234567")

    def test_sms_dispatch_fallback(self):
        res = DispatchManager.dispatch_sms("0241234567", "Test SMS message")
        self.assertEqual(res["status"], "SENT")
        self.assertEqual(res["provider"], "SMS_GATEWAY_SIMULATOR")
        self.assertEqual(res["recipient"], "0241234567")

if __name__ == "__main__":
    unittest.main()
