"""
Integration and Unit Tests for CheckerPay Ghana Operational Analytics & Telemetry Engine.
Verifies multi-dimensional business telemetry, stock burn rates, stealth 404 access gates,
Merkle audit chain verification, and strict Act 843 zero-PII compliance.
"""

import unittest
import os
import tempfile
from fastapi.testclient import TestClient

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.main import app, create_admin_session_token
from checker_platform.database import init_db, bulk_insert_vouchers, log_advisory_telemetry
from checker_platform.services.analytics import get_system_analytics
from checker_platform.services.advisory import evaluate_wassce_results, evaluate_bece_results


class TestOperationalAnalytics(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        # Seed test inventory
        vouchers = [
            {"serial_number": "ANL_WSC_001", "pin": "111111111111"},
            {"serial_number": "ANL_WSC_002", "pin": "222222222222"},
            {"serial_number": "ANL_WSC_003", "pin": "333333333333"},
            {"serial_number": "ANL_CSS_001", "pin": "444444444444"},
            {"serial_number": "ANL_BEC_001", "pin": "555555555555"},
        ]
        bulk_insert_vouchers("WASSCE", vouchers[:3])
        bulk_insert_vouchers("CSSPS", vouchers[3:4])
        bulk_insert_vouchers("BECE", vouchers[4:])
        cls.client = TestClient(app)

    def test_get_system_analytics_structure_and_windows(self):
        """Verifies get_system_analytics returns all required sections across varied time windows."""
        for window in ["24h", "7d", "30d", "all", "invalid_fallback"]:
            data = get_system_analytics(time_window=window)
            self.assertTrue(data.get("success"))
            self.assertIn("financials", data)
            self.assertIn("inventory", data)
            self.assertIn("placement_intelligence", data)
            self.assertIn("scraper_fleet", data)
            self.assertIn("security", data)

            # Financial telemetry assertions
            fin = data["financials"]
            self.assertIn("window_revenue", fin)
            self.assertIn("window_orders", fin)
            self.assertIn("window_vouchers_sold", fin)
            self.assertIn("average_order_value", fin)
            self.assertIn("conversion_rate_pct", fin)
            self.assertIn("revenue_by_category", fin)
            self.assertIn("timeline", fin)
            self.assertIn("payment_methods", fin)
            self.assertIn("funnel", fin)

            # Ensure all 4 categories exist in breakdown
            cat_names = {c["category"] for c in fin["revenue_by_category"]}
            self.assertTrue({"WASSCE", "BECE", "CSSPS", "CTVET"}.issubset(cat_names))

            # Inventory health assertions
            inv = data["inventory"]
            self.assertIn("total_unsold", inv)
            self.assertIn("overall_availability_pct", inv)
            self.assertTrue(len(inv["categories"]) > 0)
            for cat_stat in inv["categories"]:
                self.assertIn(cat_stat["health_status"], ["HEALTHY", "SUFFICIENT", "LOW", "DEPLETED"])
                self.assertIn("daily_burn_rate", cat_stat)
                self.assertIn("days_remaining", cat_stat)

            # Placement Intelligence assertions
            pl = data["placement_intelligence"]
            self.assertIn("total_evaluations", pl)
            self.assertIn("aggregate_distribution", pl)
            self.assertIn("top_disciplines", pl)
            self.assertIn("scholarships_matched", pl)

            # Scraper Fleet assertions
            sf = data["scraper_fleet"]
            self.assertGreaterEqual(sf.get("tracked_institutions", 0), 1)
            self.assertEqual(sf.get("status"), "OPERATIONAL")

            # Cryptographic Security assertions
            sec = data["security"]
            self.assertTrue(sec.get("merkle_chain_intact"))
            self.assertTrue(sec.get("database_intact"))
            self.assertTrue(sec.get("zero_persistence_verified"))
            self.assertIsInstance(sec.get("recent_ledger_blocks"), list)

    def test_analytics_strict_act_843_zero_pii(self):
        """Verifies that no student PII or customer identifiers leak into analytics payloads."""
        data = get_system_analytics(time_window="7d")
        import json
        payload_str = json.dumps(data)

        # Confirm strictly aggregated metrics without candidate PII
        forbidden_terms = [
            "phone_number",
            "candidate_name",
            "student_name",
            "index_number",
            "pin_hash",
            "0244123456",
            "0551234567"
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, payload_str)

    def test_api_admin_analytics_unauthorized(self):
        """Verifies GET /api/admin/analytics rejects unauthorized requests with 401."""
        res = self.client.get("/api/admin/analytics")
        self.assertEqual(res.status_code, 401)

    def test_api_admin_analytics_stealth_shield(self):
        """Verifies stealth 404 conceals the analytics endpoint from unauthorized external probes."""
        probe_headers = {
            "x-forwarded-for": "198.51.100.99",
            "user-agent": "Shodan-Scanner/1.0"
        }
        res = self.client.get("/api/admin/analytics", headers=probe_headers)
        self.assertEqual(res.status_code, 404)
        self.assertIn("Not Found", res.text)

    def test_api_admin_analytics_authorized_session_and_basic_auth(self):
        """Verifies authorized admin session cookie or credentials can query analytics."""
        session_token = create_admin_session_token("admin")

        # 1. Query with session cookie
        res = self.client.get(
            "/api/admin/analytics?window=24h",
            cookies={"admin_session": session_token}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("window"), "24h")
        self.assertIn("financials", data)
        self.assertIn("inventory", data)

        # 2. Query with HTTP Basic Auth
        res_basic = self.client.get(
            "/api/admin/analytics?window=30d",
            auth=("admin", "ghana2026")
        )
        self.assertEqual(res_basic.status_code, 200)
        data_basic = res_basic.json()
        self.assertTrue(data_basic.get("success"))
        self.assertEqual(data_basic.get("window"), "30d")

    def test_advisory_telemetry_live_logging(self):
        """Verifies that running an advisory evaluation updates live telemetry counts."""
        initial_analytics = get_system_analytics(time_window="all")
        initial_evals = initial_analytics["placement_intelligence"]["total_evaluations"]

        cores = {
            "English Language": "B2",
            "Core Mathematics": "A1",
            "Integrated Science": "B3",
            "Social Studies": "C4"
        }
        electives = {
            "Elective Mathematics": "A1",
            "Physics": "B2",
            "Chemistry": "B3"
        }
        evaluate_wassce_results(
            cores=cores,
            electives=electives,
            interest_area="Computer Science & Engineering"
        )

        updated_analytics = get_system_analytics(time_window="all")
        updated_evals = updated_analytics["placement_intelligence"]["total_evaluations"]
        self.assertGreater(updated_evals, initial_evals)


if __name__ == "__main__":
    unittest.main()
