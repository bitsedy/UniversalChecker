"""
Tests for Admission Benchmarks, Scraper Engine, Public Admissions API, and Stealth Scraper Sync
"""

import unittest
import os
import tempfile
import asyncio
from fastapi.testclient import TestClient

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.main import app
from checker_platform.database import (
    init_db,
    get_admission_benchmarks,
    upsert_admission_benchmark,
    get_admissions_summary_metrics,
)
from checker_platform.services.scraper import AdmissionScraperEngine
from checker_platform.services.advisory import evaluate_wassce_results

from unittest.mock import patch

class MockHttpResponse:
    def __init__(self, status_code=200, text="<html><body>Admission Deadline: 30th November 2026</body></html>"):
        self.status_code = status_code
        self.text = text

async def mock_client_get(self, *args, **kwargs):
    return MockHttpResponse(200)

class TestAdmissionScraperAndBenchmarks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.http_patcher = patch("httpx.AsyncClient.get", new=mock_client_get)
        cls.http_patcher.start()
        AdmissionScraperEngine.seed_benchmarks_if_empty()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.http_patcher.stop()

    # ========================================================================
    # 1. DATABASE BENCHMARKS CRUD & METRICS
    # ========================================================================

    def test_database_seeding_and_retrieval(self):
        """Verify baseline admission benchmarks are seeded and retrieved correctly."""
        benchmarks = get_admission_benchmarks(limit=100)
        self.assertGreater(len(benchmarks), 30)
        
        first = benchmarks[0]
        self.assertIn("institution_code", first)
        self.assertIn("programme_name", first)
        self.assertIn("cutoff_aggregate", first)
        self.assertIn("portal_url", first)
        self.assertIn("application_deadline", first)

    def test_filter_benchmarks_by_institution_type(self):
        """Filter benchmarks by PUBLIC_DEGREE, TECHNICAL_UNIVERSITY, etc."""
        degree_items = get_admission_benchmarks(institution_type="PUBLIC_DEGREE", limit=100)
        self.assertTrue(all(item["institution_type"] == "PUBLIC_DEGREE" for item in degree_items))
        self.assertGreater(len(degree_items), 10)

        tu_items = get_admission_benchmarks(institution_type="TECHNICAL_UNIVERSITY", limit=100)
        self.assertTrue(all(item["institution_type"] == "TECHNICAL_UNIVERSITY" for item in tu_items))
        self.assertGreater(len(tu_items), 5)

    def test_filter_benchmarks_by_institution_code(self):
        """Filter benchmarks specifically by institution code (e.g. UG, KNUST, UCC)."""
        ug_items = get_admission_benchmarks(institution_code="UG", limit=100)
        self.assertTrue(all(item["institution_code"] == "UG" for item in ug_items))
        self.assertGreater(len(ug_items), 5)

    def test_search_benchmarks_by_query(self):
        """Search query matches programme name, institution, or mandatory requirements."""
        nursing_items = get_admission_benchmarks(search_query="Nursing", limit=50)
        self.assertGreater(len(nursing_items), 0)
        for item in nursing_items:
            match_found = ("nursing" in item["programme_name"].lower() or 
                           "nursing" in item["faculty_category"].lower() or
                           "nursing" in item["institution_name"].lower() or
                           "nursing" in item["mandatory_requirements"].lower())
            self.assertTrue(match_found)

    def test_upsert_admission_benchmark(self):
        """Upserting a benchmark correctly inserts or updates by (institution_code, programme_name)."""
        upsert_admission_benchmark(
            institution_code="TEST_UNI",
            institution_name="Test University of Ghana",
            institution_type="PUBLIC_DEGREE",
            faculty_category="Computer Science & ICT",
            programme_name="BSc Artificial Intelligence",
            cutoff_aggregate=10,
            mandatory_requirements="A1-C6 in Core Math and Elective Math",
            admission_status="OPEN (2026/2027)",
            application_deadline="31st December 2026",
            voucher_cost_ghs=250.0,
            portal_url="https://test.edu.gh/apply",
            source_engine="manual_test"
        )

        matches = get_admission_benchmarks(institution_code="TEST_UNI", limit=5)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["programme_name"], "BSc Artificial Intelligence")
        self.assertEqual(matches[0]["cutoff_aggregate"], 10)

        # Update cut-off to 9
        upsert_admission_benchmark(
            institution_code="TEST_UNI",
            institution_name="Test University of Ghana",
            institution_type="PUBLIC_DEGREE",
            faculty_category="Computer Science & ICT",
            programme_name="BSc Artificial Intelligence",
            cutoff_aggregate=9,
            mandatory_requirements="A1-C6 in Core Math and Elective Math",
            admission_status="OPEN (2026/2027)",
            application_deadline="31st December 2026",
            voucher_cost_ghs=250.0,
            portal_url="https://test.edu.gh/apply",
            source_engine="manual_test_updated"
        )

        updated_matches = get_admission_benchmarks(institution_code="TEST_UNI", limit=5)
        self.assertEqual(len(updated_matches), 1)
        self.assertEqual(updated_matches[0]["cutoff_aggregate"], 9)

    def test_admissions_summary_metrics(self):
        """Metrics calculation returns valid counts and timestamps."""
        metrics = get_admissions_summary_metrics()
        self.assertGreater(metrics["total_programmes"], 30)
        self.assertGreater(metrics["total_institutions"], 5)
        self.assertIn("open_admissions", metrics)
        self.assertIn("latest_scrape", metrics)

    # ========================================================================
    # 2. SCRAPER ENGINE UNIT & SYNC
    # ========================================================================

    def test_scrape_institution_portal(self):
        """Scraper returns structured admission data with reliable fallback."""
        data = asyncio.run(AdmissionScraperEngine.scrape_institution_portal("KNUST"))
        self.assertEqual(data["code"], "KNUST")
        self.assertEqual(data["name"], "Kwame Nkrumah University of Science and Technology")
        self.assertGreater(len(data["programmes"]), 5)
        self.assertIn("portal_url", data)

    def test_scrape_unknown_institution_graceful_handling(self):
        """Scraping an unknown code returns empty programmes list without crashing."""
        data = asyncio.run(AdmissionScraperEngine.scrape_institution_portal("NONEXISTENT"))
        self.assertEqual(data["code"], "NONEXISTENT")
        self.assertEqual(len(data["programmes"]), 0)

    def test_sync_all_institutions(self):
        """Multi-institution synchronizer processes all portals and updates database."""
        result = asyncio.run(AdmissionScraperEngine.sync_all_institutions())
        self.assertTrue(result["success"])
        self.assertGreater(result["total_upserted"], 20)
        self.assertIn("duration_seconds", result)

    # ========================================================================
    # 3. PUBLIC API ENDPOINTS
    # ========================================================================

    def test_public_admissions_live_api(self):
        """GET /api/admissions/live returns public benchmarks without authentication."""
        res = self.client.get("/api/admissions/live")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["count"], 20)
        self.assertIsInstance(data["benchmarks"], list)

    def test_public_admissions_live_api_with_filters(self):
        """GET /api/admissions/live with institution_type and q search query."""
        res = self.client.get("/api/admissions/live?institution_type=PUBLIC_DEGREE&q=Computer")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        for item in data["benchmarks"]:
            self.assertEqual(item["institution_type"], "PUBLIC_DEGREE")
            self.assertTrue("computer" in item["programme_name"].lower() or "ict" in item["faculty_category"].lower())

    # ========================================================================
    # 4. ADMIN STEALTH 404 SCRAPER SYNC ENDPOINT
    # ========================================================================

    def test_unauthorized_ip_gets_404_on_scraper_sync(self):
        """Random unauthorized IP gets genuine 404 on POST /api/admin/scraper/sync."""
        res = self.client.post("/api/admin/scraper/sync", headers={"X-Forwarded-For": "198.51.100.77"})
        self.assertEqual(res.status_code, 404)

    def test_authorized_admin_can_trigger_scraper_sync(self):
        """Authorized IP or request with gate key can trigger live scraper sync."""
        res = self.client.post(
            "/api/admin/scraper/sync?gate=ghana2026_gate",
            auth=("admin", "ghana2026"),
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("summary", data)
        self.assertGreater(data["summary"]["total_upserted"], 20)

    # ========================================================================
    # 5. ADVISORY INTEGRATION WITH LIVE CUT-OFF BENCHMARKS
    # ========================================================================

    def test_wassce_advisory_includes_live_matches(self):
        """WASSCE evaluation matches real scraped departmental cut-offs."""
        result = evaluate_wassce_results(
            cores={
                "English Language": "A1",
                "Core Mathematics": "A1",
                "Integrated Science": "A1",
                "Social Studies": "B2"
            },
            electives={
                "Elective Mathematics": "A1",
                "Physics": "A1",
                "Chemistry": "A1"
            },
            interest_area="Computer Science & Engineering"
        )

        self.assertEqual(result["aggregate"], 6)
        self.assertEqual(result["eligibility_status"], "QUALIFIED_DEGREE")

        # Find traditional degree pathway
        degree_path = next((p for p in result["pathways"] if p["pathway_type"] == "TRADITIONAL_DEGREE"), None)
        self.assertIsNotNone(degree_path)
        self.assertIn("live_matches", degree_path)
        self.assertGreater(len(degree_path["live_matches"]), 0)

        first_match = degree_path["live_matches"][0]
        self.assertIn(first_match["fit"], ["Strong Match", "Competitive"])
        self.assertIn("portal_url", first_match)
        self.assertIn("application_deadline", first_match)
        self.assertIn("voucher_cost_ghs", first_match)

if __name__ == "__main__":
    unittest.main()
