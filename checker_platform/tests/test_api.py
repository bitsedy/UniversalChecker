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

    def test_admin_page_get(self):
        response = self.client.get("/admin")
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

if __name__ == "__main__":
    unittest.main()
