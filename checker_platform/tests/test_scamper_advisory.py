"""
Unit & Integration Tests for SCAMPER Innovation Upgrades:
- Universal Admissions Dossier & Eligibility Gatekeeper
- Scholarship & Bursary Matching Engine
- WASSCE Deficit & NOV/DEC Remedial Strategy Engine
- Act 843 Zero-Persistence Proof Minting
"""

import os
import tempfile
import unittest

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["CHECKER_DB_PATH"] = temp_db_path

from checker_platform.database import init_db, verify_audit_chain_integrity
from checker_platform.services.advisory import (
    evaluate_wassce_results,
    evaluate_bece_results,
    evaluate_programme_prerequisites,
    match_scholarships,
    calculate_wassce_deficits,
    SCHOLARSHIP_REGISTRY
)


class TestScamperAdvisory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    # ========================================================================
    # 1. ELIGIBILITY GATEKEEPER & PREREQUISITE DEFICIT TESTS
    # ========================================================================

    def test_prerequisite_medicine_deficit(self):
        """High-achieving student (Aggregate 8) with D7 in Chemistry must be flagged as blocked for Medicine."""
        grades = {
            "English Language": "A1",
            "Core Mathematics": "A1",
            "Integrated Science": "A1",
            "Social Studies": "A1",
            "Biology": "A1",
            "Physics": "B2",
            "Chemistry": "D7"
        }
        res = evaluate_programme_prerequisites("MBChB (Medicine & Surgery)", "UG", grades)
        self.assertFalse(res["eligible"])
        self.assertEqual(res["status"], "PREREQUISITE_DEFICIT")
        self.assertIn("Chemistry", res["details"])

    def test_prerequisite_engineering_satisfied(self):
        """Engineering applicant with A1-C6 in Core Math, Elective Math, and Physics satisfies prerequisites."""
        grades = {
            "English Language": "B3",
            "Core Mathematics": "B2",
            "Integrated Science": "B3",
            "Elective Mathematics": "B2",
            "Physics": "C4",
            "Chemistry": "C5"
        }
        res = evaluate_programme_prerequisites("BSc Electrical & Electronic Engineering", "KNUST", grades)
        self.assertTrue(res["eligible"])
        self.assertEqual(res["status"], "PREREQUISITE_SATISFIED")

    def test_prerequisite_engineering_math_deficit(self):
        """Engineering applicant with D7 in Elective Math is blocked."""
        grades = {
            "English Language": "B3",
            "Core Mathematics": "B2",
            "Integrated Science": "B3",
            "Elective Mathematics": "D7",
            "Physics": "C4"
        }
        res = evaluate_programme_prerequisites("BSc Computer Engineering", "KNUST", grades)
        self.assertFalse(res["eligible"])
        self.assertEqual(res["status"], "PREREQUISITE_DEFICIT")
        self.assertIn("Elective Mathematics", res["details"])

    # ========================================================================
    # 2. SCHOLARSHIP MATCHING ENGINE TESTS
    # ========================================================================

    def test_scholarship_matching_top_distinction(self):
        """Candidate with Aggregate 08 matches full suite of corporate and government scholarships."""
        grades = {"English Language": "A1", "Core Mathematics": "A1", "Elective Mathematics": "B2"}
        matches = match_scholarships(aggregate=8, interest_area="Computer Science & Engineering", subjects_dict=grades)
        
        match_ids = [m["id"] for m in matches]
        self.assertIn("SCHOL_MTN_BRIGHT", match_ids)
        self.assertIn("SCHOL_GNPC_STEM", match_ids)
        self.assertIn("SCHOL_MASTERCARD_KNUST", match_ids)
        self.assertIn("SCHOL_GOV_BURSARY", match_ids)

        mtn = next(m for m in matches if m["id"] == "SCHOL_MTN_BRIGHT")
        self.assertEqual(mtn["badge"], "Strong Academic Fit")

    def test_scholarship_matching_moderate_aggregate(self):
        """Candidate with Aggregate 22 matches broad government bursaries, not high-distinction corporate awards."""
        grades = {"English Language": "C4", "Core Mathematics": "C5"}
        matches = match_scholarships(aggregate=22, interest_area="Arts, Humanities & Social Sciences", subjects_dict=grades)
        
        match_ids = [m["id"] for m in matches]
        self.assertIn("SCHOL_GOV_BURSARY", match_ids)
        self.assertNotIn("SCHOL_MTN_BRIGHT", match_ids)  # max 12
        self.assertNotIn("SCHOL_GNPC_STEM", match_ids)    # max 16

    # ========================================================================
    # 3. WASSCE DEFICIT & REMEDIAL STRATEGY ENGINE TESTS
    # ========================================================================

    def test_deficit_calculator_identifies_bottlenecks(self):
        """Verifies bottleneck subjects are targeted and upgrade scenario mathematically projects gains."""
        qualifying_subjects = [
            ("English Language", "B3", 3),
            ("Core Mathematics", "B2", 2),
            ("Integrated Science", "C5", 5),
            ("Elective Mathematics", "B3", 3),
            ("Physics", "C6", 6),
            ("Chemistry", "C4", 4)
        ]
        current_aggregate = 23
        mock_benchmarks = [
            {"programme_name": "BSc Computer Science", "institution_code": "UG", "cutoff_aggregate": 14},
            {"programme_name": "BSc Information Technology", "institution_code": "UPSA", "cutoff_aggregate": 19},
            {"programme_name": "BSc Telecom Engineering", "institution_code": "KNUST", "cutoff_aggregate": 18}
        ]

        deficits = calculate_wassce_deficits(qualifying_subjects, current_aggregate, mock_benchmarks)
        self.assertTrue(deficits["has_deficits"])
        self.assertGreater(len(deficits["scenarios"]), 0)

        # Physics (C6=6) is the worst subject; upgrading to B2 drops 4 points
        top_scenario = deficits["scenarios"][0]
        self.assertEqual(top_scenario["subject"], "Physics")
        self.assertEqual(top_scenario["current_grade"], "C6")
        self.assertEqual(top_scenario["aggregate_drop"], 4)
        self.assertEqual(top_scenario["projected_aggregate"], 19)
        self.assertGreaterEqual(top_scenario["additional_programmes_unlocked"], 1)

    # ========================================================================
    # 4. FULL EVALUATION & WHATSAPP DOSSIER FORMATTING
    # ========================================================================

    def test_full_wassce_evaluation_integration(self):
        """Validates that evaluate_wassce_results returns all enriched SCAMPER attributes."""
        cores = {
            "English Language": "B3",
            "Core Mathematics": "A1",
            "Integrated Science": "B2",
            "Social Studies": "C4"
        }
        electives = {
            "Elective Mathematics": "A1",
            "Physics": "B2",
            "Chemistry": "B3",
            "Biology": "C5"
        }
        res = evaluate_wassce_results(cores, electives, "Computer Science & Engineering")
        
        self.assertIn("scholarships", res)
        self.assertIn("deficits_analysis", res)
        self.assertIn("whatsapp_share_text", res)
        self.assertIn("compliance_attestation_hash", res)
        self.assertIn("CHECKERPAY GHANA | ADMISSIONS & PLACEMENT DOSSIER", res["whatsapp_share_text"])
        self.assertIn("Proof Hash:", res["whatsapp_share_text"])

    def test_full_bece_evaluation_integration(self):
        """Validates that evaluate_bece_results returns WhatsApp dossier text and Act 843 hash."""
        cores = {
            "English Language": 2,
            "Mathematics": 1,
            "Integrated Science": 1,
            "Social Studies": 2
        }
        electives = {
            "BDT / Pre-Technical": 2,
            "Information & Communication Tech (ICT)": 1
        }
        res = evaluate_bece_results(cores, electives, "General Science")
        self.assertIn("whatsapp_share_text", res)
        self.assertIn("compliance_attestation_hash", res)
        self.assertIn("CHECKERPAY GHANA | CSSPS PLACEMENT DOSSIER", res["whatsapp_share_text"])

    def test_audit_chain_stays_intact_after_advisory(self):
        """Proves every advisory run mints a valid, unbroken block in the Merkle audit chain."""
        cores = {
            "English Language": "A1",
            "Core Mathematics": "B2",
            "Integrated Science": "A1",
            "Social Studies": "B3"
        }
        electives = {
            "Elective Mathematics": "B2",
            "Physics": "B3",
            "Chemistry": "C4"
        }
        res = evaluate_wassce_results(cores, electives, "Engineering")
        self.assertTrue(res["compliance_attestation_hash"])
        is_ok, count, msg = verify_audit_chain_integrity()
        self.assertTrue(is_ok, f"Audit chain verification failed: {msg}")
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
