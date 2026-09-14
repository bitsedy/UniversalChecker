"""
Tests for Admin Stealth 404 Security and Ghana Act 843 Educational Advisory Engine
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
from checker_platform.database import init_db
from checker_platform.services.advisory import (
    evaluate_bece_results,
    evaluate_wassce_results,
)

class TestStealthAdminAndAdvisory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    # ========================================================================
    # 1. ADMIN STEALTH 404 SECURITY TESTS
    # ========================================================================

    def test_unauthorized_ip_gets_404_on_admin(self):
        """Random unauthorized IP must receive genuine 404, not 401 or login redirect."""
        res = self.client.get("/admin", headers={"X-Forwarded-For": "198.51.100.44"})
        self.assertEqual(res.status_code, 404)
        self.assertIn("Not Found", res.text)

    def test_unauthorized_ip_gets_404_on_admin_login(self):
        """Random unauthorized IP navigating to /admin/login receives 404."""
        res = self.client.get("/admin/login", headers={"X-Forwarded-For": "198.51.100.44"})
        self.assertEqual(res.status_code, 404)
        self.assertIn("Not Found", res.text)

    def test_unauthorized_ip_gets_404_on_admin_api(self):
        """Random unauthorized IP probing /api/admin/settings receives 404."""
        res = self.client.post("/api/admin/settings", json={}, headers={"X-Forwarded-For": "198.51.100.44"})
        self.assertEqual(res.status_code, 404)

    def test_unauthorized_ip_with_gate_key_unlocks_login(self):
        """Remote/unauthorized IP with secret gate key ?gate=ghana2026_gate is granted access."""
        res = self.client.get("/admin/login?gate=ghana2026_gate", headers={"X-Forwarded-For": "198.51.100.44"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Merchant Admin Sign-In", res.text)

    def test_unauthorized_ip_with_gate_header_unlocks_access(self):
        """Remote/unauthorized IP with X-Admin-Gate header is granted access."""
        res = self.client.get("/admin/login", headers={
            "X-Forwarded-For": "198.51.100.44",
            "X-Admin-Gate": "ghana2026_gate"
        })
        self.assertEqual(res.status_code, 200)

    def test_unauthorized_ip_with_wrong_gate_key_remains_404(self):
        """Remote/unauthorized IP with invalid gate key still gets 404."""
        res = self.client.get("/admin/login?gate=wrong_key", headers={"X-Forwarded-For": "198.51.100.44"})
        self.assertEqual(res.status_code, 404)

    def test_whitelisted_ip_can_access_admin_login(self):
        """Localhost / whitelisted IP can access admin login directly."""
        res = self.client.get("/admin/login", headers={"X-Forwarded-For": "127.0.0.1"})
        self.assertEqual(res.status_code, 200)

    def test_remote_browser_full_login_flow(self):
        """Verifies that a remote browser using gate parameter can view login, submit credentials, and receive session."""
        from fastapi.testclient import TestClient
        from checker_platform.main import app
        isolated_client = TestClient(app)
        remote_headers = {
            "X-Forwarded-For": "41.215.160.77",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            "Accept": "text/html"
        }
        # 1. First visit /admin with gate key -> redirects to /admin/login with cookie
        res1 = isolated_client.get("/admin?gate=ghana2026_gate", headers=remote_headers, follow_redirects=False)
        self.assertEqual(res1.status_code, 303)
        self.assertIn("admin_gate_pass=ghana2026_gate", res1.headers.get("set-cookie", ""))

        # 2. View login page
        res2 = isolated_client.get("/admin/login", headers=remote_headers)
        self.assertEqual(res2.status_code, 200)

        # 3. Submit credentials (case-insensitive username 'Admin')
        res3 = isolated_client.post(
            "/admin/login",
            data={"username": "Admin", "password": "ghana2026"},
            headers=remote_headers,
            follow_redirects=False
        )
        self.assertEqual(res3.status_code, 303)
        self.assertIn("admin_session=", res3.headers.get("set-cookie", ""))

        # 4. Access admin dashboard with session
        res4 = isolated_client.get("/admin", headers=remote_headers)
        self.assertEqual(res4.status_code, 200)

    # ========================================================================
    # 2. ACT 843 COMPLIANT ADVISORY PORTAL TESTS
    # ========================================================================

    def test_advisor_page_get(self):
        """Advisory page renders with Act 843 privacy notice."""
        res = self.client.get("/advisor")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Placement & Pathway Advisor", res.text)
        self.assertIn("Ghana Data Protection Act, 2012 (Act 843)", res.text)

    def test_advisor_analyze_requires_consent(self):
        """Refuses to process examination results if consent_given is False."""
        payload = {
            "exam_type": "BECE",
            "consent_given": False,
            "cores": {"English Language": 1},
            "electives": {}
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertIn("Consent is required", data["message"])

    def test_bece_advisory_high_merit(self):
        """BECE Aggregate 06 analysis matches Category A prestige schools."""
        payload = {
            "exam_type": "BECE",
            "consent_given": True,
            "cores": {
                "English Language": 1,
                "Mathematics": 1,
                "Integrated Science": 1,
                "Social Studies": 1
            },
            "electives": {
                "BDT / Pre-Technical": 1,
                "Information & Communication Tech (ICT)": 1,
                "French": 2
            },
            "programme": "General Science"
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["compliance"]["retention"], "Zero Persistence (Ephemeral In-Memory Analysis)")
        
        analysis = data["analysis"]
        self.assertEqual(analysis["aggregate"], 6)
        self.assertEqual(analysis["risk_level"], "LOW")
        # Check that Category A is qualified
        cat_a = next((t for t in analysis["recommended_tiers"] if "Category A" in t["tier_name"]), None)
        self.assertIsNotNone(cat_a)
        self.assertEqual(cat_a["status"], "QUALIFIED")

    def test_bece_bottleneck_warning(self):
        """BECE with weak English/Math (Grade 7) produces explicit bottleneck reality check."""
        payload = {
            "exam_type": "BECE",
            "consent_given": True,
            "cores": {
                "English Language": 7,
                "Mathematics": 7,
                "Integrated Science": 2,
                "Social Studies": 2
            },
            "electives": {
                "BDT / Pre-Technical": 2,
                "Information & Communication Tech (ICT)": 2
            }
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        analysis = res.json()["analysis"]
        # Must have reality checks for English and Math
        checks_text = " ".join(analysis["reality_checks"])
        self.assertIn("English Language grade is 7", checks_text)
        self.assertIn("Mathematics grade is 7", checks_text)

    def test_wassce_advisory_qualified_degree(self):
        """WASSCE with all A1-C6 qualifies for public university degree."""
        payload = {
            "exam_type": "WASSCE",
            "consent_given": True,
            "cores": {
                "English Language": "B2",
                "Core Mathematics": "A1",
                "Integrated Science": "B3",
                "Social Studies": "C4"
            },
            "electives": {
                "Elective Mathematics": "B2",
                "Physics": "B3",
                "Chemistry": "C4"
            },
            "programme": "Computer Science & Engineering"
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        analysis = data["analysis"]
        self.assertEqual(analysis["eligibility_status"], "QUALIFIED_DEGREE")
        # Direct degree pathway should be included
        degree_pathway = next((p for p in analysis["pathways"] if p["pathway_type"] == "TRADITIONAL_DEGREE"), None)
        self.assertIsNotNone(degree_pathway)

    def test_wassce_d7_math_reality_check_and_hnd_alternative(self):
        """WASSCE with D7 in Core Math produces non-bluffing warning and HND/Technical University route."""
        payload = {
            "exam_type": "WASSCE",
            "consent_given": True,
            "cores": {
                "English Language": "C5",
                "Core Mathematics": "D7",
                "Integrated Science": "C6",
                "Social Studies": "C4"
            },
            "electives": {
                "Elective Mathematics": "C4",
                "Economics": "B3",
                "Geography": "C5"
            },
            "programme": "Computer Science & Engineering"
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        analysis = res.json()["analysis"]
        
        # Reality check must highlight GTEC restriction
        self.assertEqual(analysis["eligibility_status"], "BARRED_FROM_PUBLIC_DEGREE")
        checks_text = " ".join(analysis["reality_checks"])
        self.assertIn("Core Mathematics is D7", checks_text)
        
        # Practical alternatives must be present
        pathway_types = [p["pathway_type"] for p in analysis["pathways"]]
        self.assertIn("TECHNICAL_UNIVERSITY_HND", pathway_types)
        self.assertIn("DIPLOMA_TOP_UP", pathway_types)
        self.assertIn("NOV_DEC_REMEDIAL", pathway_types)

    # ========================================================================
    # 4. INSTITUTIONAL SUGGESTIONS & PROBABILITY ENGINE TESTS
    # ========================================================================

    def test_bece_suggested_schools_with_probabilities(self):
        """Verifies BECE evaluation generates specific school suggestions with computed probabilities."""
        payload = {
            "exam_type": "BECE",
            "consent_given": True,
            "cores": {
                "English Language": 1,
                "Mathematics": 1,
                "Integrated Science": 1,
                "Social Studies": 1
            },
            "electives": {
                "BDT / Pre-Technical": 1,
                "Information & Communication Tech (ICT)": 1
            },
            "programme": "General Science"
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        analysis = res.json()["analysis"]

        self.assertIn("suggested_schools", analysis)
        schools = analysis["suggested_schools"]
        self.assertGreaterEqual(len(schools), 5)

        # High distinction candidate (Agg 06) must have high probability in Cat A/B
        top_school = schools[0]
        self.assertIn("school_name", top_school)
        self.assertIn("probability_percent", top_school)
        self.assertIn("strategic_role", top_school)
        self.assertIn("rationale", top_school)
        self.assertGreaterEqual(top_school["probability_percent"], 80)
        self.assertEqual(top_school["prerequisites_met"], True)

        # WhatsApp share text must contain the suggestions
        self.assertIn("TOP SUGGESTED SCHOOLS & CHANCES", analysis["whatsapp_share_text"])
        self.assertIn("% Chance", analysis["whatsapp_share_text"])

    def test_wassce_suggested_institutions_with_probabilities(self):
        """Verifies WASSCE evaluation ranks institutions with admission probabilities and strategic roles."""
        payload = {
            "exam_type": "WASSCE",
            "consent_given": True,
            "cores": {
                "English Language": "A1",
                "Core Mathematics": "A1",
                "Integrated Science": "B2",
                "Social Studies": "A1"
            },
            "electives": {
                "Elective Mathematics": "A1",
                "Physics": "B2",
                "Chemistry": "B3"
            },
            "programme": "Computer Science & Engineering"
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        analysis = res.json()["analysis"]

        self.assertIn("suggested_institutions", analysis)
        institutions = analysis["suggested_institutions"]
        self.assertGreaterEqual(len(institutions), 5)

        # Agg 08 with A1 Math should have high admission probability in STEM
        top_inst = institutions[0]
        self.assertIn("programme_name", top_inst)
        self.assertIn("institution_code", top_inst)
        self.assertIn("probability_percent", top_inst)
        self.assertIn("strategic_role", top_inst)
        self.assertIn("rationale", top_inst)
        self.assertGreaterEqual(top_inst["probability_percent"], 80)
        self.assertEqual(top_inst["prerequisites_met"], True)

        # WhatsApp dossier must include suggested institutions
        self.assertIn("TOP SUGGESTED INSTITUTIONS & CHANCES", analysis["whatsapp_share_text"])

    def test_wassce_prerequisite_deficit_drops_probability(self):
        """Failing a required prerequisite (e.g. D7 in Elective Math for Engineering) drops probability."""
        payload = {
            "exam_type": "WASSCE",
            "consent_given": True,
            "cores": {
                "English Language": "B2",
                "Core Mathematics": "B2",
                "Integrated Science": "B3",
                "Social Studies": "A1"
            },
            "electives": {
                "Elective Mathematics": "D7",  # Engineering prerequisite failure (requires min C6)
                "Physics": "B3",
                "Chemistry": "C4"
            },
            "programme": "Computer Science & Engineering"
        }
        res = self.client.post("/api/advisor/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        analysis = res.json()["analysis"]

        institutions = analysis["suggested_institutions"]
        # Find any public degree Engineering/CS programme that requires Elective Math
        eng_degrees = [i for i in institutions if "Engineering" in i["programme_name"] or "Computer Science" in i["programme_name"]]
        self.assertTrue(len(eng_degrees) > 0)
        
        for eng in eng_degrees:
            if eng["institution_type"] == "PUBLIC_DEGREE":
                self.assertFalse(eng["prerequisites_met"])
                self.assertLessEqual(eng["probability_percent"], 25)
                self.assertEqual(eng["match_tier"], "PREREQUISITE_DEFICIT")
                self.assertIn("deficit", eng["prerequisite_details"].lower())

