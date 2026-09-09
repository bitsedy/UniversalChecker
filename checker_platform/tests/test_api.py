"""
Integration tests for CheckerPay Ghana FastAPI application endpoints
"""

import unittest
import os
import tempfile
from fastapi.testclient import TestClient

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.main import app
from checker_platform.database import init_db, bulk_insert_vouchers

class TestApiEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        # Seed test inventory
        vouchers = [
            {"serial_number": "API_WSC_001", "pin": "847192847192"},
            {"serial_number": "API_WSC_002", "pin": "918273645102"},
            {"serial_number": "API_CSSPS_001", "pin": "7192837482"},
        ]
        bulk_insert_vouchers("WASSCE", vouchers[:2])
        bulk_insert_vouchers("CSSPS", vouchers[2:])
        bulk_insert_vouchers("BECE", [{"serial_number": "API_BEC_001", "pin": "998877665544"}])
        bulk_insert_vouchers("CTVET", [{"serial_number": "API_CTV_001", "pin": "112233445566"}])
        cls.client = TestClient(app)

    def test_storefront_get(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("CheckerPay Ghana", response.text)
        self.assertIn("WASSCE", response.text)
        self.assertIn("CSSPS", response.text)

    def test_lookup_page_get(self):
        response = self.client.get("/lookup")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Retrieve Lost Result Checker", response.text)

    def test_guides_page_get(self):
        response = self.client.get("/guides")
        self.assertEqual(response.status_code, 200)
        self.assertIn("The 10 vs 12-Digit Index Rule", response.text)
        self.assertIn("The 3-Check Limit & Index Binding", response.text)

    def test_admin_page_unauthorized(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 401)

    def test_admin_page_authorized(self):
        response = self.client.get("/admin", auth=("admin", "ghana2026"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Merchant Inventory & Operations", response.text)

    def test_api_catalog(self):
        response = self.client.get("/api/catalog")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("WASSCE", data)
        self.assertIn("CSSPS", data)
        self.assertGreaterEqual(data["WASSCE"]["available_stock"], 2)

    def test_end_to_end_purchase_flow(self):
        # 1. Create order
        order_payload = {
            "category": "WASSCE",
            "quantity": 1,
            "customer_phone": "024 123 4567",
            "customer_email": "candidate@waec.gh",
            "payment_method": "MOMO_MTN"
        }
        res_create = self.client.post("/api/orders/create", json=order_payload)
        self.assertEqual(res_create.status_code, 200)
        create_data = res_create.json()
        self.assertTrue(create_data["success"])
        order_ref = create_data["order"]["order_reference"]
        self.assertIn("*170#", create_data["payment_prompt"]["manual_steps"])

        # 2. Verify payment (Simulate MoMo approval)
        verify_payload = {
            "order_reference": order_ref,
            "provider": "MOMO_SIMULATOR"
        }
        res_verify = self.client.post("/api/orders/verify", json=verify_payload)
        self.assertEqual(res_verify.status_code, 200)
        verify_data = res_verify.json()
        self.assertTrue(verify_data["success"])
        self.assertEqual(len(verify_data["fulfillment"]["cards"]), 1)
        card = verify_data["fulfillment"]["cards"][0]
        self.assertIn("serial_number", card)
        self.assertIn("pin", card)
        self.assertEqual(card["category"], "WASSCE")
        self.assertEqual(verify_data["fulfillment"]["portal_url"], "https://ghana.waecdirect.org")
        self.assertEqual(verify_data["fulfillment"]["portal_name"], "Official WAEC WASSCE Checking Portal")

        # 3. Lookup order via self-service
        res_lookup = self.client.get(f"/lookup?q={order_ref}")
        self.assertEqual(res_lookup.status_code, 200)
        self.assertIn(order_ref, res_lookup.text)
        self.assertIn(card["serial_number"], res_lookup.text)

        # 4. Lookup order via API
        res_api_order = self.client.get(f"/api/orders/{order_ref}")
        self.assertEqual(res_api_order.status_code, 200)
        api_order_data = res_api_order.json()
        self.assertEqual(api_order_data["payment_status"], "PAID")
        self.assertEqual(len(api_order_data["vouchers"]), 1)

    def test_bece_specific_redirect_portal(self):
        # Test BECE routes specifically to eresults.waecgh.org
        res = self.client.post("/api/orders/create", json={
            "category": "BECE",
            "quantity": 1,
            "customer_phone": "054 999 8888",
            "payment_method": "MOMO_MTN"
        })
        order_ref = res.json()["order"]["order_reference"]
        verify = self.client.post("/api/orders/verify", json={"order_reference": order_ref, "provider": "MOMO_SIMULATOR"})
        f = verify.json()["fulfillment"]
        self.assertEqual(f["portal_url"], "https://eresults.waecgh.org")
        self.assertIn("BECE", f["portal_name"])

    def test_cssps_specific_redirect_portal(self):
        # Test CSSPS routes to cssps.gov.gh
        res = self.client.post("/api/orders/create", json={
            "category": "CSSPS",
            "quantity": 1,
            "customer_phone": "020 123 4567",
            "payment_method": "MOMO_TELECEL"
        })
        order_ref = res.json()["order"]["order_reference"]
        verify = self.client.post("/api/orders/verify", json={"order_reference": order_ref, "provider": "MOMO_SIMULATOR"})
        f = verify.json()["fulfillment"]
        self.assertEqual(f["portal_url"], "https://cssps.gov.gh")
        self.assertIn("CSSPS", f["portal_name"])

    def test_demo_batch_generate_api(self):
        # Without auth should fail
        unauth = self.client.post("/api/admin/inventory/generate-demo", json={"category": "WASSCE", "count": 5})
        self.assertEqual(unauth.status_code, 401)

        # With auth should succeed
        res = self.client.post("/api/admin/inventory/generate-demo", json={
            "category": "WASSCE",
            "count": 5
        }, auth=("admin", "ghana2026"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_inserted"], 5)

    def test_dynamic_demo_generation_mode(self):
        # Switch mode to DEMO_GENERATE with auth
        res = self.client.post("/api/admin/settings", json={
            "price_WASSCE": "22.00",
            "price_BECE": "18.00",
            "price_CSSPS": "15.00",
            "price_CTVET": "25.00",
            "sms_sender_id": "CHECKER_GH",
            "inventory_mode": "DEMO_GENERATE"
        }, auth=("admin", "ghana2026"))
        self.assertEqual(res.status_code, 200)
        
        # Verify catalog reflects demo mode
        cat_res = self.client.get("/api/catalog")
        self.assertTrue(cat_res.json()["WASSCE"]["is_demo_mode"])

        # Order should succeed and mint unique random vouchers dynamically
        order_res = self.client.post("/api/orders/create", json={
            "category": "WASSCE",
            "quantity": 2,
            "customer_phone": "055 777 6655",
            "payment_method": "MOMO_MTN"
        })
        self.assertEqual(order_res.status_code, 200)
        order_data = order_res.json()
        self.assertTrue(order_data["success"])
        
        # Verify and complete purchase
        order_ref = order_data["order"]["order_reference"]
        verify = self.client.post("/api/orders/verify", json={
            "order_reference": order_ref,
            "provider": "MOMO_SIMULATOR"
        })
        cards = verify.json()["fulfillment"]["cards"]
        self.assertEqual(len(cards), 2)
        # Serials must be distinct
        self.assertNotEqual(cards[0]["serial_number"], cards[1]["serial_number"])
        self.assertTrue(cards[0]["serial_number"].startswith("WSC2026D"))

        # Switch back to BATCH mode
        self.client.post("/api/admin/settings", json={
            "price_WASSCE": "22.00",
            "price_BECE": "18.00",
            "price_CSSPS": "15.00",
            "price_CTVET": "25.00",
            "sms_sender_id": "CHECKER_GH",
            "inventory_mode": "BATCH"
        }, auth=("admin", "ghana2026"))

    def test_admin_logout(self):
        """Verifies that the /admin/logout endpoint issues 401 with a fresh realm to discard cached auth."""
        res = self.client.get("/admin/logout")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Logged Out", res.headers.get("WWW-Authenticate", ""))
        self.assertIn("Logged Out Successfully", res.text)

    def test_admin_security_headers(self):
        """Verifies that security headers are applied to prevent caching, sniffing, and clickjacking."""
        res = self.client.get("/admin", auth=("admin", "ghana2026"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("no-store", res.headers.get("Cache-Control", ""))

    def test_admin_password_hash_and_validation(self):
        """Verifies password length validation and PBKDF2 salted hashing."""
        from checker_platform.database import get_setting

        # 1. Reject password under 8 characters
        res_short = self.client.post("/api/admin/settings", json={
            "price_WASSCE": "22.00",
            "price_BECE": "18.00",
            "price_CSSPS": "15.00",
            "price_CTVET": "25.00",
            "sms_sender_id": "CHECKER_GH",
            "admin_password": "short"
        }, auth=("admin", "ghana2026"))
        self.assertEqual(res_short.status_code, 400)
        self.assertIn("8 characters", res_short.json()["message"])

        # 2. Accept strong password and verify salted PBKDF2 hash stored
        strong_pass = "GhanaSecretPass2026!"
        res_ok = self.client.post("/api/admin/settings", json={
            "price_WASSCE": "22.00",
            "price_BECE": "18.00",
            "price_CSSPS": "15.00",
            "price_CTVET": "25.00",
            "sms_sender_id": "CHECKER_GH",
            "admin_password": strong_pass
        }, auth=("admin", "ghana2026"))
        self.assertEqual(res_ok.status_code, 200)

        stored = get_setting("admin_password")
        self.assertTrue(stored.startswith("pbkdf2:sha256:100000$"))

        # 3. Verify login succeeds with new password
        res_login = self.client.get("/admin", auth=("admin", strong_pass))
        self.assertEqual(res_login.status_code, 200)

        # 4. Restore test suite password
        from checker_platform.main import hash_password
        from checker_platform.database import update_setting
        update_setting("admin_password", "ghana2026")

    def test_admin_rate_limiter_lockout(self):
        """Verifies that 5 failed login attempts trigger a 429 Too Many Requests lockout."""
        from checker_platform.main import AdminSecurityManager
        AdminSecurityManager.reset()

        # 4 failed attempts should yield 401
        for i in range(4):
            res = self.client.get("/admin", auth=("admin", f"wrong_pass_{i}"))
            self.assertEqual(res.status_code, 401)

        # 5th failed attempt should trigger 401 and lock out
        res5 = self.client.get("/admin", auth=("admin", "wrong_pass_5"))
        self.assertEqual(res5.status_code, 401)

        # 6th attempt should now be blocked with 429 Too Many Requests
        res_locked = self.client.get("/admin", auth=("admin", "ghana2026"))
        self.assertEqual(res_locked.status_code, 429)
        self.assertIn("Too many failed login attempts", res_locked.json()["detail"])

        # Reset for subsequent tests
        AdminSecurityManager.reset()

if __name__ == "__main__":
    unittest.main()
