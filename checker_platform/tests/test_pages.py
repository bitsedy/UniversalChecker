"""
Integration and statutory compliance tests for CheckerPay Ghana customer service
and legal pages (/about, /faq, /feedback, /terms, /privacy, /delivery-returns).
"""

import unittest
import os
import tempfile
from fastapi.testclient import TestClient

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.main import app, _FEEDBACK_RATE_LIMIT
from checker_platform.database import init_db, get_customer_feedback, bulk_insert_vouchers, get_db_connection, update_setting

class TestCustomerPagesAndFeedback(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        # Clear rate limit dict between tests
        _FEEDBACK_RATE_LIMIT.clear()

    def test_about_page_rendering_and_statutory_pillars(self):
        response = self.client.get("/about")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Democratizing Access to Ghanaian Educational Milestones", response.text)
        self.assertIn("Act 843", response.text)
        self.assertIn("Act 772", response.text)
        self.assertIn("Concurrency-Safe Inventory", response.text)
        self.assertIn("Sub-Millisecond Mobile Money Processing", response.text)

    def test_faq_page_rendering_and_categories(self):
        response = self.client.get("/faq")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Frequently Asked Questions", response.text)
        self.assertIn("Are CheckerPay vouchers authentic and accepted on official portals?", response.text)
        self.assertIn("Which payment methods are supported?", response.text)
        self.assertIn("Placement &amp; Pathway Advisor", response.text)
        self.assertIn("Rate Your Experience &amp; Share Feedback", response.text)

    def test_feedback_page_alias(self):
        response = self.client.get("/feedback")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Rate Your Experience &amp; Share Feedback", response.text)
        self.assertIn("shouldScrollToFeedback = true", response.text)
        self.assertIn("feedback-section", response.text)

    def test_terms_of_service_ghana_statutory_compliance(self):
        response = self.client.get("/terms")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Terms of Service", response.text)
        self.assertIn("Electronic Transactions Act, 2008 (Act 772)", response.text)
        self.assertIn("Cybersecurity Act, 2020 (Act 1038)", response.text)
        self.assertIn("Refund &amp; Replacement Policy", response.text)
        self.assertIn("Academic Boards of individual universities", response.text)

    def test_privacy_policy_ghana_act_843_compliance(self):
        response = self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Privacy Policy", response.text)
        self.assertIn("Data Protection Act, 2012 (Act 843)", response.text)
        self.assertIn("Section 20 of Act 843", response.text)
        self.assertIn("Zero-Persistence Guarantee for Academic Records", response.text)
        self.assertIn("Data Protection &amp; Compliance Office", response.text)

    def test_delivery_returns_policy(self):
        response = self.client.get("/delivery-returns")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Delivery &amp; Returns Policy", response.text)
        self.assertIn("100% Instant Digital Delivery", response.text)
        self.assertIn("Self-Service Voucher Recovery", response.text)
        self.assertIn("100% Replacement Guarantee for Defective Vouchers", response.text)
        self.assertIn("Duplicate Telecom Debits", response.text)

    def test_navigation_and_footer_links_on_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Verify header nav links
        self.assertIn('href="/about"', response.text)
        self.assertIn('href="/faq"', response.text)
        self.assertIn('href="/advisor"', response.text)
        self.assertIn('href="/guides"', response.text)
        self.assertIn('href="/lookup"', response.text)
        # Verify footer links
        self.assertIn('href="/terms"', response.text)
        self.assertIn('href="/privacy"', response.text)
        self.assertIn('href="/delivery-returns"', response.text)
        self.assertIn('href="/feedback"', response.text)

    def test_submit_customer_feedback_success(self):
        payload = {
            "rating": 5,
            "category": "VOUCHER_DELIVERY",
            "message": "Purchased my WASSCE checker card at 2 AM and received it in under 3 seconds! Best service ever.",
            "customer_name": "Kofi Asante",
            "customer_phone": "0244123456",
            "order_reference": "ORD-TEST-001"
        }
        response = self.client.post("/api/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("feedback_id", data)

        # Verify record was persisted in database
        feedback_list = get_customer_feedback(limit=10)
        self.assertGreaterEqual(len(feedback_list), 1)
        latest = feedback_list[0]
        self.assertEqual(latest["rating"], 5)
        self.assertEqual(latest["category"], "VOUCHER_DELIVERY")
        self.assertEqual(latest["customer_name"], "Kofi Asante")
        self.assertEqual(latest["order_reference"], "ORD-TEST-001")

    def test_submit_customer_feedback_validation_error(self):
        # Invalid: message too short (< 5 chars)
        invalid_payload = {
            "rating": 4,
            "category": "SUPPORT",
            "message": "hi"
        }
        response = self.client.post("/api/feedback", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

        # Invalid: rating > 5
        invalid_rating = {
            "rating": 10,
            "category": "SUPPORT",
            "message": "Great service but invalid rating scale."
        }
        response = self.client.post("/api/feedback", json=invalid_rating)
        self.assertEqual(response.status_code, 422)

    def test_customer_feedback_rate_limiting(self):
        payload = {
            "rating": 4,
            "category": "GENERAL_FEEDBACK",
            "message": "Testing automated rate limiting protection on customer feedback."
        }
        # First 5 submissions succeed
        for _ in range(5):
            res = self.client.post("/api/feedback", json=payload)
            self.assertEqual(res.status_code, 200)

        # 6th submission should trigger 429 Too Many Requests
        res = self.client.post("/api/feedback", json=payload)
        self.assertEqual(res.status_code, 429)
        self.assertIn("Too many feedback submissions", res.json().get("message", ""))

    def test_storefront_qualitative_stock_indicators(self):
        """Verifies qualitative stock messages (In Stock, Almost Out of Stock, Out of Stock) without exposing raw counts."""
        update_setting("inventory_mode", "BATCH")
        conn = get_db_connection()
        conn.execute("DELETE FROM vouchers WHERE category = 'WASSCE';")
        conn.commit()
        conn.close()

        # 1. Zero stock -> 'Out of Stock' and disabled button
        res_zero = self.client.get("/")
        self.assertEqual(res_zero.status_code, 200)
        self.assertIn("Out of Stock", res_zero.text)
        self.assertIn("stock-bullet out-of-stock", res_zero.text)
        self.assertIn("disabled", res_zero.text)

        # 2. Low stock (<= 10, e.g. 5) -> 'Almost Out of Stock'
        low_vouchers = [{"serial_number": f"LOW_WSC_{i:03d}", "pin": f"12345678901{i}"} for i in range(5)]
        bulk_insert_vouchers("WASSCE", low_vouchers)
        res_low = self.client.get("/")
        self.assertEqual(res_low.status_code, 200)
        self.assertIn("Almost Out of Stock", res_low.text)
        self.assertIn("stock-bullet low-stock", res_low.text)
        self.assertNotIn("5 In Stock", res_low.text)

        # 3. Healthy stock (> 10, add 10 more to reach 15) -> 'In Stock'
        more_vouchers = [{"serial_number": f"HIGH_WSC_{i:03d}", "pin": f"98765432101{i}"} for i in range(10)]
        bulk_insert_vouchers("WASSCE", more_vouchers)
        res_high = self.client.get("/")
        self.assertEqual(res_high.status_code, 200)
        self.assertIn("In Stock", res_high.text)
        self.assertIn("stock-bullet in-stock", res_high.text)
        self.assertNotIn("15 In Stock", res_high.text)

if __name__ == "__main__":
    unittest.main()
