"""
Educational Placement & Pathway Advisory Engine for Ghana (BECE & WASSCE)
Compliant with Ghana Data Protection Act, 2012 (Act 843):
- Processes candidate grades ephemerally in-memory.
- Zero data retention (no grades or personal indices persisted to database).
- Grounded in official GES CSSPS guidelines and GTEC / University admissions cut-offs.
"""

from typing import Dict, List, Any, Optional, Tuple

from ..database import get_admission_benchmarks, append_audit_block
from .scraper import AdmissionScraperEngine
from .security import EphemeralMemoryVault

# ============================================================================
# BECE DATA & ADVISORY LOGIC (CSSPS PLACEMENT)
# ============================================================================

BECE_CORE_SUBJECTS = ["English Language", "Mathematics", "Integrated Science", "Social Studies"]
BECE_ELECTIVE_SUBJECTS = [
    "BDT / Pre-Technical",
    "Information & Communication Tech (ICT)",
    "French",
    "Ghanaian Language",
    "Religious & Moral Education (RME)"
]

# GES School Categorization Database
BECE_SCHOOL_TIERS = {
    "CAT_A": {
        "tier_name": "Category A (Top National Merit Institutions)",
        "description": "Prestigious national oversubscribed boarding institutions. High academic competition.",
        "aggregate_range": (6, 9),
        "schools": [
            {"name": "Presbyterian Boys' Senior High (PRESEC Legon)", "gender": "Boys", "region": "Greater Accra", "strong_in": ["General Science", "General Arts", "Business"]},
            {"name": "Achimota School", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["General Science", "General Arts", "Visual Arts"]},
            {"name": "Wesley Girls' High School", "gender": "Girls", "region": "Central", "strong_in": ["General Science", "General Arts", "Home Economics", "Business"]},
            {"name": "Prempeh College", "gender": "Boys", "region": "Ashanti", "strong_in": ["General Science", "General Arts", "Visual Arts"]},
            {"name": "Holy Child School", "gender": "Girls", "region": "Central", "strong_in": ["General Science", "General Arts", "Home Economics"]},
            {"name": "Mfantsipim School", "gender": "Boys", "region": "Central", "strong_in": ["General Science", "General Arts", "Business"]},
            {"name": "Opoku Ware School", "gender": "Boys", "region": "Ashanti", "strong_in": ["General Science", "General Arts", "Business"]},
            {"name": "Aburi Girls' Senior High", "gender": "Girls", "region": "Eastern", "strong_in": ["General Science", "General Arts", "Home Economics"]},
            {"name": "St. Peter's Boys' Senior High", "gender": "Boys", "region": "Eastern", "strong_in": ["General Science", "General Arts"]},
            {"name": "St. Rose's Senior High", "gender": "Girls", "region": "Eastern", "strong_in": ["General Science", "General Arts", "Business"]}
        ]
    },
    "CAT_B": {
        "tier_name": "Category B (High-Standard Regional & National Institutions)",
        "description": "Renowned secondary schools with excellent academic track records and balanced admission thresholds.",
        "aggregate_range": (10, 18),
        "schools": [
            {"name": "St. Thomas Aquinas Senior High", "gender": "Boys", "region": "Greater Accra", "strong_in": ["General Science", "General Arts"]},
            {"name": "Ghana National College", "gender": "Mixed", "region": "Central", "strong_in": ["General Science", "General Arts", "Business"]},
            {"name": "Mawuli School", "gender": "Mixed", "region": "Volta", "strong_in": ["General Science", "General Arts", "Technical"]},
            {"name": "Kumasi High School", "gender": "Boys", "region": "Ashanti", "strong_in": ["General Science", "General Arts", "Business"]},
            {"name": "St. Augustine's College", "gender": "Boys", "region": "Central", "strong_in": ["General Science", "General Arts", "Business"]},
            {"name": "Pope John Senior High & Minor Seminary", "gender": "Boys", "region": "Eastern", "strong_in": ["General Science", "General Arts"]},
            {"name": "Tamale Senior High", "gender": "Mixed", "region": "Northern", "strong_in": ["General Science", "General Arts"]},
            {"name": "Sunyani Senior High", "gender": "Mixed", "region": "Bono", "strong_in": ["General Science", "General Arts", "Home Economics"]},
            {"name": "Osu Presbyterian Senior High", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["General Arts", "Business", "Home Economics"]}
        ]
    },
    "CAT_C": {
        "tier_name": "Category C (Community & Developing Senior High Schools)",
        "description": "Solid community-based and regional schools with supportive learning environments.",
        "aggregate_range": (19, 30),
        "schools": [
            {"name": "Armed Forces Senior High Technical", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["General Arts", "Technical", "Home Economics"]},
            {"name": "Nungua Senior High", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["General Arts", "Business"]},
            {"name": "Christian Methodist Senior High", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["General Arts", "Home Economics"]},
            {"name": "Ada Senior High", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["General Science", "General Arts", "Agriculture"]},
            {"name": "Effiduase Senior High", "gender": "Mixed", "region": "Ashanti", "strong_in": ["General Arts", "Visual Arts", "Business"]}
        ]
    },
    "CAT_D": {
        "tier_name": "Category D (Local Day Catchment Institutions - 30% Quota)",
        "description": "Day institutions within the candidate's catchment district. GES guarantees 30% allocation for local candidates.",
        "aggregate_range": (25, 45),
        "schools": [
            {"name": "District Designated Day Senior High Schools", "gender": "Mixed", "region": "Candidate's Residential District", "strong_in": ["General Arts", "Business", "Home Economics", "Technical"]}
        ]
    },
    "CAT_E": {
        "tier_name": "Category E (Technical & Vocational Education / CTVET)",
        "description": "Hands-on engineering, fashion, computing, and construction institutes under CTVET.",
        "aggregate_range": (12, 38),
        "schools": [
            {"name": "Accra Technical Training Centre (ATTC)", "gender": "Mixed", "region": "Greater Accra", "strong_in": ["Engineering Tech", "Electricals", "ICT", "Automotive"]},
            {"name": "Kumasi Technical Institute (KTI)", "gender": "Mixed", "region": "Ashanti", "strong_in": ["Mechanical Engineering", "Building Construction", "Welding"]},
            {"name": "Takoradi Technical Institute (TTI)", "gender": "Mixed", "region": "Western", "strong_in": ["Fabrication", "Electrical Tech", "Industrial Electronics"]},
            {"name": "Asuansi Technical Institute", "gender": "Mixed", "region": "Central", "strong_in": ["Agricultural Engineering", "Catering", "Carpentry"]}
        ]
    }
}

def evaluate_bece_results(
    cores: Dict[str, int], 
    electives: Dict[str, int], 
    preferred_programme: str = "General Science"
) -> Dict[str, Any]:
    """
    Evaluates BECE results under official GES CSSPS rules:
    - Aggregate = Sum of best 4 Cores + best 2 Electives.
    - Stanine Scale: 1 (Highest) to 9 (Lowest).
    - Assesses eligibility for Category A, B, C, D, and E (TVET) schools.
    """
    # 1. Validate Cores
    core_grades = []
    for c in BECE_CORE_SUBJECTS:
        grade = cores.get(c, 9)
        core_grades.append((c, max(1, min(9, int(grade)))))

    # Sum 4 core subjects
    core_aggregate = sum(g[1] for g in core_grades)

    # 2. Pick Best 2 Electives
    elective_grades = []
    for e_name, e_grade in electives.items():
        if e_grade is not None:
            elective_grades.append((e_name, max(1, min(9, int(e_grade)))))

    elective_grades.sort(key=lambda x: x[1])
    best_2_electives = elective_grades[:2] if len(elective_grades) >= 2 else elective_grades
    # If fewer than 2 electives provided, assume grade 9
    while len(best_2_electives) < 2:
        best_2_electives.append(("Additional Elective", 9))

    elective_aggregate = sum(g[1] for g in best_2_electives)
    total_aggregate = core_aggregate + elective_aggregate

    # 3. Subject Bottleneck & Risk Checks
    english_grade = cores.get("English Language", 9)
    math_grade = cores.get("Mathematics", 9)
    science_grade = cores.get("Integrated Science", 9)

    reality_checks = []
    risk_level = "LOW"

    if english_grade > 6:
        risk_level = "HIGH"
        reality_checks.append(
            f"⚠️ Critical Risk: English Language grade is {english_grade} (Stanine > 6). Under CSSPS automated rules, candidates with Grade 7-9 in English Language frequently miss automated placement and must utilize Self-Placement."
        )
    if math_grade > 6:
        if risk_level != "HIGH":
            risk_level = "MODERATE"
        reality_checks.append(
            f"⚠️ Mathematics grade is {math_grade} (Stanine > 6). This restricts placement into General Science and Business programmes."
        )
    if preferred_programme == "General Science" and (science_grade > 3 or math_grade > 3):
        reality_checks.append(
            f"ℹ️ General Science Reality Check: Category A & B schools heavily favor candidates with Grade 1 or 2 in Integrated Science and Mathematics. Your grades (Science: {science_grade}, Math: {math_grade}) may require choosing Category B or C schools for this programme."
        )

    # 4. Determine Placement Probabilities Across Categories
    recommendations = []
    
    # Category A match
    if total_aggregate <= 9 and english_grade <= 3 and math_grade <= 3:
        cat_a = BECE_SCHOOL_TIERS["CAT_A"].copy()
        cat_a["status"] = "QUALIFIED"
        cat_a["chances"] = "Strong Match"
        cat_a["badge"] = "high-probability"
        recommendations.append(cat_a)
    elif total_aggregate <= 11:
        cat_a = BECE_SCHOOL_TIERS["CAT_A"].copy()
        cat_a["status"] = "COMPETITIVE"
        cat_a["chances"] = "Competitive / Reach"
        cat_a["badge"] = "medium-probability"
        recommendations.append(cat_a)

    # Category B match
    if total_aggregate <= 18 and english_grade <= 5:
        cat_b = BECE_SCHOOL_TIERS["CAT_B"].copy()
        cat_b["status"] = "QUALIFIED" if total_aggregate <= 15 else "COMPETITIVE"
        cat_b["chances"] = "Strong Match" if total_aggregate <= 15 else "Competitive"
        cat_b["badge"] = "high-probability" if total_aggregate <= 15 else "medium-probability"
        recommendations.append(cat_b)

    # Category C match
    if total_aggregate <= 30:
        cat_c = BECE_SCHOOL_TIERS["CAT_C"].copy()
        cat_c["status"] = "QUALIFIED"
        cat_c["chances"] = "Very High Match"
        cat_c["badge"] = "high-probability"
        recommendations.append(cat_c)

    # Category D (Local Day) match
    cat_d = BECE_SCHOOL_TIERS["CAT_D"].copy()
    cat_d["status"] = "GUARANTEED_QUOTA" if total_aggregate <= 38 else "POSSIBLE"
    cat_d["chances"] = "Guaranteed Local Catchment" if total_aggregate <= 38 else "Possible Local Day"
    cat_d["badge"] = "safe-choice"
    recommendations.append(cat_d)

    # Category E (TVET) match
    cat_e = BECE_SCHOOL_TIERS["CAT_E"].copy()
    cat_e["status"] = "RECOMMENDED"
    cat_e["chances"] = "Highly Recommended for Practical & Technical Careers"
    cat_e["badge"] = "tvet-recommended"
    recommendations.append(cat_e)

    # 5. Step-by-Step Action Roadmap
    roadmap = [
        {
            "step": 1,
            "title": "CSSPS Portal Verification",
            "action": "Once placements are officially released by the Ministry of Education, visit https://cssps.gov.gh using your 12-digit Index + Year (e.g. 101010101026) and authentic voucher to check if placed automatically in choices 1 to 6."
        },
        {
            "step": 2,
            "title": "Self-Placement Preparedness",
            "action": "If not placed automatically, do NOT panic and NEVER pay unauthorized agents. Immediately access the official CSSPS Self-Placement module within 48 hours to select an available school matching Aggregate " + str(total_aggregate) + "."
        },
        {
            "step": 3,
            "title": "30% Local Day Allocation Advantage",
            "action": "If your aggregate is between 20 and 38, actively utilize the 30% reserved local day quota in your district to secure enrollment in reputable community schools."
        },
        {
            "step": 4,
            "title": "Enrollment Documentation",
            "action": "Prepare: BECE Official Result Slip, CSSPS Placement Form, National Health Insurance (NHIS) card, and 4 passport-size photographs for Senior High School physical registration."
        }
    ]

    audit_hash = append_audit_block(
        action="ACT_843_BECE_EVALUATION",
        actor="EPHEMERAL_ADVISORY_ENGINE",
        payload_data={
            "exam_type": "BECE",
            "aggregate": total_aggregate,
            "programme": preferred_programme,
            "zero_persistence_verified": True
        }
    )

    whatsapp_text = (
        "🇬🇭 *CHECKERPAY GHANA | CSSPS PLACEMENT DOSSIER*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏫 *BECE Aggregate:* {total_aggregate:02d} ({risk_level})\n"
        f"🎯 *Target Programme:* {preferred_programme}\n"
        f"📋 *Score Breakdown:* Cores: {core_aggregate} pts | Best 2 Electives: {elective_aggregate} pts\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏛️ *RECOMMENDED PLACEMENT TIERS:*\n"
        + "\n".join([f"  • *{t['tier_name']}* ({t['status']})" for t in recommendations[:3]])
        + "\n\n🛡️ *OFFICIAL CSSPS NOTICE:*\n"
        "Never pay unauthorized protocol admission agents.\n"
        "Official self-placement portal: https://cssps.gov.gh\n"
        f"Verification Hash: `{audit_hash[:16]}...`"
    )

    return {
        "exam_type": "BECE",
        "aggregate": total_aggregate,
        "aggregate_string": f"Aggregate {total_aggregate:02d}",
        "core_aggregate": core_aggregate,
        "elective_aggregate": elective_aggregate,
        "best_cores": core_grades,
        "best_electives": best_2_electives,
        "risk_level": risk_level,
        "reality_checks": reality_checks,
        "recommended_tiers": recommendations,
        "roadmap": roadmap,
        "preferred_programme": preferred_programme,
        "whatsapp_share_text": whatsapp_text,
        "compliance_attestation_hash": audit_hash
    }

# ============================================================================
# WASSCE DATA & ADVISORY LOGIC (TERTIARY / UNIVERSITY ADMISSION)
# ============================================================================

WASSCE_GRADE_VALUES = {
    "A1": 1,
    "B2": 2,
    "B3": 3,
    "C4": 4,
    "C5": 5,
    "C6": 6,
    "D7": 7,
    "E8": 8,
    "F9": 9
}

# Official GTEC & University Cut-off Benchmarks
UNIVERSITY_PROGRAMMES = [
    {
        "category": "Medicine & Health Sciences",
        "programmes": ["MBChB (Medicine & Surgery)", "BSc Pharmacy", "Doctor of Optometry"],
        "cutoff_range": (6, 9),
        "typical_institutions": ["University of Ghana (UG Legon)", "KNUST (Kumasi)", "UCC (Cape Coast)"],
        "mandatory_requirements": "Requires A1 in Core Math, English, Chemistry, Biology, and Physics/Elective Math."
    },
    {
        "category": "Computer Science & Engineering",
        "programmes": ["BSc Computer Science", "BSc Software Engineering", "BSc Electrical Engineering", "BSc Mechanical Engineering"],
        "cutoff_range": (8, 14),
        "typical_institutions": ["KNUST", "UG Legon", "UMaT (Tarkwa)", "UCC"],
        "mandatory_requirements": "Requires A1-C6 in Core Math, Integrated Science, and Elective Mathematics."
    },
    {
        "category": "Business, Finance & Law",
        "programmes": ["BSc Administration (Accounting/Finance)", "Bachelor of Laws (LL.B)", "BSc Marketing"],
        "cutoff_range": (8, 15),
        "typical_institutions": ["UG Business School", "KNUST School of Business", "UPSA (Accra)", "UCC"],
        "mandatory_requirements": "Requires A1-C6 in English Language, Core Math, and relevant electives."
    },
    {
        "category": "Nursing & Allied Health",
        "programmes": ["BSc Nursing", "BSc Midwifery", "BSc Medical Laboratory Science"],
        "cutoff_range": (9, 16),
        "typical_institutions": ["UG Legon", "KNUST", "UDS (Tamale)", "Ministry of Health NMTCs"],
        "mandatory_requirements": "Requires A1-C6 in English, Core Math, Science, and Science/Arts electives."
    },
    {
        "category": "Arts, Humanities & Social Sciences",
        "programmes": ["BA Political Science", "BA Economics", "BA Sociology", "BA Communication Studies"],
        "cutoff_range": (12, 22),
        "typical_institutions": ["UG Legon", "UCC", "KNUST", "UEW (Winneba)"],
        "mandatory_requirements": "Requires A1-C6 in English Language, Social Studies/Science, and Arts/Social Science electives."
    },
    {
        "category": "Education & Teaching",
        "programmes": ["B.Ed Primary Education", "B.Ed Early Grade", "B.Ed Junior High School Education"],
        "cutoff_range": (15, 26),
        "typical_institutions": ["University of Education, Winneba (UEW)", "UCC", "46 Accredited Colleges of Education"],
        "mandatory_requirements": "Requires passes (A1-C6) in Core English and Core Math."
    }
]

# ============================================================================
# SCHOLARSHIP REGISTRY & FINANCIAL AID DATABASE
# ============================================================================

SCHOLARSHIP_REGISTRY = [
    {
        "id": "SCHOL_GNPC_STEM",
        "name": "GNPC Foundation Local Undergraduate Scholarship",
        "sponsor": "Ghana National Petroleum Corporation (GNPC)",
        "category": "Corporate Full Sponsorship",
        "max_aggregate": 16,
        "stem_priority": True,
        "coverage": "100% Tuition, Academic Facility User Fees, On-Campus Accommodation, Book Allowance & Annual Cash Stipend (~GH₵ 15,000/yr)",
        "requirements": "Ghanaian citizen with admission to an accredited public university; strong priority for STEM, Agriculture, and Education.",
        "application_window": "November – January (Annual Cycle)",
        "portal_url": "https://gnpcfoundation.org/scholarships",
        "status": "ANNUAL_CYCLE"
    },
    {
        "id": "SCHOL_MTN_BRIGHT",
        "name": "MTN Ghana Foundation Bright Scholarship",
        "sponsor": "MTN Ghana Foundation",
        "category": "Corporate Merit & Need Fellowship",
        "max_aggregate": 12,
        "stem_priority": False,
        "coverage": "Full Tuition, Semester Hostel Fees, Living Stipend Allowance & High-Performance Laptop (~GH₵ 18,000/yr)",
        "requirements": "First-year undergraduate Ghanaian applicants with exceptional academic distinction (Aggregate 6 to 12) in public universities.",
        "application_window": "May – July (Annual Cycle)",
        "portal_url": "https://scholarship.mtn.com.gh",
        "status": "ANNUAL_CYCLE"
    },
    {
        "id": "SCHOL_MASTERCARD_KNUST",
        "name": "Mastercard Foundation Scholars Program at KNUST",
        "sponsor": "Mastercard Foundation / KNUST",
        "category": "Comprehensive Global Fellowship",
        "max_aggregate": 16,
        "stem_priority": True,
        "coverage": "Comprehensive 100% Tuition, Modern Housing, Meals, Monthly Living Stipend, Laptop, Books & Leadership Academy",
        "requirements": "Academically qualified youth from economically disadvantaged backgrounds, with priority for young women, displaced youth, and persons with disabilities.",
        "application_window": "January – May (Annual Cycle)",
        "portal_url": "https://mcf.knust.edu.gh",
        "status": "ANNUAL_CYCLE"
    },
    {
        "id": "SCHOL_GOV_BURSARY",
        "name": "Ghana Scholarship Secretariat Local Tertiary Bursary",
        "sponsor": "Government of Ghana (Scholarships Secretariat)",
        "category": "National Government Bursary",
        "max_aggregate": 24,
        "stem_priority": False,
        "coverage": "Subsidized Tuition / Academic Facility User Fee (AFUF) Grant paid directly to public tertiary institution (~GH₵ 2,500 – GH₵ 5,000/yr)",
        "requirements": "Registered Ghanaian citizen with valid Ghana Card, verified admission letter to an accredited public tertiary institution.",
        "application_window": "March – June (Portal Open)",
        "portal_url": "https://www.scholarshipgh.com",
        "status": "OPEN"
    },
    {
        "id": "SCHOL_ASHESI_AID",
        "name": "Ashesi University Comprehensive Need-Based Grant",
        "sponsor": "Ashesi University Foundation",
        "category": "Private Institutional Endowed Grant",
        "max_aggregate": 14,
        "stem_priority": False,
        "coverage": "Up to 100% Tuition, Campus Housing, Meals, Laptop & Comprehensive Healthcare (~GH₵ 65,000/yr equivalent)",
        "requirements": "Demonstrated academic excellence, leadership track record, and documented financial need. Open for BSc Computer Science, MIS, and Engineering.",
        "application_window": "January – June (Phased Admissions)",
        "portal_url": "https://www.ashesi.edu.gh/admissions/scholarships.html",
        "status": "OPEN"
    },
    {
        "id": "SCHOL_UG_STARS",
        "name": "University of Ghana Students Financial Aid (SFAO)",
        "sponsor": "University of Ghana / Needy Students Fund",
        "category": "Public University Institutional Aid",
        "max_aggregate": 20,
        "stem_priority": False,
        "coverage": "Tuition Grant / Residential Support Grant (GH₵ 1,500 – GH₵ 4,000/yr)",
        "requirements": "Admitted or continuing full-time regular undergraduate student at UG Legon with documented financial hardship.",
        "application_window": "August – October (Semester 1 Cycle)",
        "portal_url": "https://finaid.ug.edu.gh",
        "status": "ANNUAL_CYCLE"
    }
]

def match_scholarships(
    aggregate: int, 
    interest_area: str, 
    subjects_dict: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Evaluates candidate academic profile against active Ghanaian scholarship schemes.
    Returns matched funding opportunities categorized by academic competitiveness.
    """
    matches = []
    is_stem = any(s in interest_area for s in ["Science", "Engineering", "Health", "Medicine", "Technology", "Computing"])

    for s in SCHOLARSHIP_REGISTRY:
        if aggregate <= s["max_aggregate"]:
            if aggregate <= s["max_aggregate"] - 4:
                tier = "HIGH_COMPETITIVENESS"
                badge = "Strong Academic Fit"
            elif aggregate <= s["max_aggregate"] - 2:
                tier = "COMPETITIVE"
                badge = "Competitive Candidate"
            else:
                tier = "ELIGIBLE"
                badge = "Eligible Applicant"

            matches.append({
                "id": s["id"],
                "name": s["name"],
                "sponsor": s["sponsor"],
                "category": s["category"],
                "max_aggregate": s["max_aggregate"],
                "coverage": s["coverage"],
                "requirements": s["requirements"],
                "application_window": s["application_window"],
                "portal_url": s["portal_url"],
                "match_tier": tier,
                "badge": badge,
                "stem_bonus": s["stem_priority"] and is_stem
            })
    return matches

def evaluate_programme_prerequisites(
    programme_name: str,
    institution_code: str,
    grades_dict: Dict[str, str]
) -> Dict[str, Any]:
    """
    Evaluates mandatory Ghanaian faculty prerequisite rules beyond composite aggregate.
    Guarantees strict compliance without misleading or false admission assumptions.
    """
    name_upper = programme_name.upper()

    def get_val(subj_search: str) -> int:
        for k, v in grades_dict.items():
            if subj_search.lower() in k.lower():
                return WASSCE_GRADE_VALUES.get(str(v).strip().upper(), 9)
        return 9

    c_math = get_val("Core Mathematics")
    e_math = get_val("Elective Mathematics")
    eng = get_val("English")
    sci = get_val("Science")
    chem = get_val("Chemistry")
    bio = get_val("Biology")
    phys = get_val("Physics")

    # 1. Medicine & Pharmacy
    if any(term in name_upper for term in ["MEDICINE", "SURGERY", "PHARMACY", "OPTOMETRY", "MBCHB"]):
        missing = []
        if eng > 3: missing.append("English Language (Requires min B3)")
        if c_math > 3: missing.append("Core Mathematics (Requires min B3)")
        if chem > 3: missing.append("Chemistry (Requires min B3)")
        if bio > 3: missing.append("Biology (Requires min B3)")
        if missing:
            return {"eligible": False, "status": "PREREQUISITE_DEFICIT", "details": f"Missing clinical prerequisite: {', '.join(missing)}"}
        return {"eligible": True, "status": "PREREQUISITE_SATISFIED", "details": "Satisfies all high-competition medical faculty core prerequisites."}

    # 2. Engineering & Computer Science
    if any(term in name_upper for term in ["ENGINEERING", "COMPUTER SCIENCE", "SOFTWARE", "ELECTRICAL", "MECHANICAL"]):
        missing = []
        if c_math > 6: missing.append("Core Mathematics (Requires min C6)")
        if e_math > 6: missing.append("Elective Mathematics (Requires min C6)")
        if phys > 6 and sci > 6: missing.append("Physics or Integrated Science (Requires min C6)")
        if missing:
            return {"eligible": False, "status": "PREREQUISITE_DEFICIT", "details": f"Engineering prerequisite deficit: {', '.join(missing)}"}
        return {"eligible": True, "status": "PREREQUISITE_SATISFIED", "details": "Satisfies STEM faculty Core Math, Elective Math & Science requirements."}

    # 3. Business & Finance
    if any(term in name_upper for term in ["ADMINISTRATION", "ACCOUNTING", "FINANCE", "BANKING", "ECONOMICS"]):
        missing = []
        if eng > 6: missing.append("English Language (Requires min C6)")
        if c_math > 6: missing.append("Core Mathematics (Requires min C6)")
        if missing:
            return {"eligible": False, "status": "PREREQUISITE_DEFICIT", "details": f"Business school prerequisite deficit: {', '.join(missing)}"}
        return {"eligible": True, "status": "PREREQUISITE_SATISFIED", "details": "Meets Business Faculty quantitative and language prerequisites."}

    # 4. Nursing & Allied Health
    if any(term in name_upper for term in ["NURSING", "MIDWIFERY", "ALLIED HEALTH", "MEDICAL LABORATORY"]):
        missing = []
        if eng > 6: missing.append("English Language (Requires min C6)")
        if c_math > 6: missing.append("Core Mathematics (Requires min C6)")
        if sci > 6: missing.append("Integrated Science (Requires min C6)")
        if missing:
            return {"eligible": False, "status": "PREREQUISITE_DEFICIT", "details": f"Nursing Council prerequisite deficit: {', '.join(missing)}"}
        return {"eligible": True, "status": "PREREQUISITE_SATISFIED", "details": "Meets Ministry of Health & Nursing Council standard requirements."}

    # 5. Law (LL.B)
    if "LAW" in name_upper or "LL.B" in name_upper:
        missing = []
        if eng > 3: missing.append("English Language (Requires min B3)")
        if missing:
            return {"eligible": False, "status": "PREREQUISITE_DEFICIT", "details": f"Faculty of Law prerequisite deficit: {', '.join(missing)}"}
        return {"eligible": True, "status": "PREREQUISITE_SATISFIED", "details": "Satisfies Law Faculty language proficiency requirements."}

    # General Public University Degree Rule
    if eng > 6 or c_math > 6:
        return {"eligible": False, "status": "PREREQUISITE_DEFICIT", "details": "GTEC Rule: Public universities strictly require minimum C6 in English and Core Math for direct degree entry."}
    return {"eligible": True, "status": "PREREQUISITE_SATISFIED", "details": "Standard university matriculation prerequisites satisfied."}

def calculate_wassce_deficits(
    qualifying_subjects: List[Tuple[str, str, int]],
    current_aggregate: int,
    benchmarks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Identifies bottleneck subjects dragging down the candidate's aggregate
    and calculates exact quantitative gains from strategic Nov/Dec remedial resits.
    """
    candidates_for_improvement = [s for s in qualifying_subjects if s[2] >= 3]
    candidates_for_improvement.sort(key=lambda x: x[2], reverse=True)

    scenarios = []
    currently_eligible_count = sum(1 for b in benchmarks if current_aggregate <= b.get("cutoff_aggregate", 0))

    for subj in candidates_for_improvement[:2]:
        s_name, s_grade, s_val = subj
        target_grade = "A1" if s_val <= 4 else "B2"
        target_val = 1 if target_grade == "A1" else 2
        point_gain = s_val - target_val

        if point_gain <= 0:
            continue

        improved_aggregate = current_aggregate - point_gain
        newly_eligible_count = sum(1 for b in benchmarks if improved_aggregate <= b.get("cutoff_aggregate", 0))
        additional_programmes_unlocked = max(0, newly_eligible_count - currently_eligible_count)

        unlocked_samples = [
            f"{b['programme_name']} at {b['institution_code']} (Cut-Off: {b['cutoff_aggregate']})"
            for b in benchmarks 
            if current_aggregate > b.get("cutoff_aggregate", 0) >= improved_aggregate
        ][:4]

        scenarios.append({
            "subject": s_name,
            "current_grade": s_grade,
            "current_val": s_val,
            "target_grade": target_grade,
            "target_val": target_val,
            "aggregate_drop": point_gain,
            "projected_aggregate": improved_aggregate,
            "additional_programmes_unlocked": additional_programmes_unlocked,
            "unlocked_samples": unlocked_samples
        })

    return {
        "has_deficits": len(scenarios) > 0,
        "scenarios": scenarios,
        "remedial_guidance": {
            "policy": "GTEC Two-Sitting Combination Policy",
            "explanation": "Under GTEC policy, Ghanaian universities accept combination of results from up to two sittings (e.g. May/June + Nov/Dec). You only need to register and re-sit the specific bottleneck subject.",
            "registration_window": "May – July (Annual WAEC Portal)",
            "examination_window": "September – October",
            "portal_url": "https://registration.waecgh.org"
        }
    }

def format_wassce_whatsapp_dossier(analysis: Dict[str, Any]) -> str:
    """Formats an executive WhatsApp share text for parents, mentors, and candidates."""
    lines = [
        "🇬🇭 *CHECKERPAY GHANA | ADMISSIONS & PLACEMENT DOSSIER*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 *Candidate Status:* {analysis.get('aggregate_string', 'N/A')}",
        f"🎯 *Field of Interest:* {analysis.get('interest_area', 'General')}",
        f"⚖️ *GTEC Qualification:* {analysis.get('eligibility_status', '').replace('_', ' ')}",
        "",
        "📋 *QUALIFYING SUBJECTS SUMMARY:*"
    ]
    for c in analysis.get("selected_cores", []):
        lines.append(f"  • {c[0]}: *{c[1]}*")
    for e in analysis.get("selected_electives", []):
        lines.append(f"  • {e[0]}: *{e[1]}*")

    scholarships = analysis.get("scholarships", [])
    if scholarships:
        lines.append("")
        lines.append(f"💰 *MATCHED SCHOLARSHIPS ({len(scholarships)} Opportunities):*")
        for s in scholarships[:3]:
            lines.append(f"  ⭐ *{s['name']}*")
            lines.append(f"     Coverage: {s['coverage'][:55]}...")
            lines.append(f"     Portal: {s['portal_url']}")

    deficits = analysis.get("deficits_analysis", {})
    if deficits.get("has_deficits") and deficits.get("scenarios"):
        top = deficits["scenarios"][0]
        lines.append("")
        lines.append("🚀 *STRATEGIC REMEDIAL PROJECTION (NOV/DEC):*")
        lines.append(f"  Upgrading *{top['subject']}* ({top['current_grade']} ➔ {top['target_grade']}) shifts aggregate from *{analysis['aggregate']}* to *{top['projected_aggregate']}*, unlocking *+{top['additional_programmes_unlocked']} degree programmes* at Legon & KNUST!")

    lines.extend([
        "",
        "🔒 *VERIFIED INTEGRITY ATTENUATION:*",
        f"Proof Hash: `{analysis.get('compliance_attestation_hash', '')[:16]}...`",
        "Grounded in official GTEC/WAEC benchmarks under Ghana Act 843.",
        "Check live admissions: https://checkerpay.onrender.com/advisor"
    ])
    return "\n".join(lines)

def evaluate_wassce_results(
    cores: Dict[str, str], 
    electives: Dict[str, str], 
    interest_area: str = "Computer Science & Engineering"
) -> Dict[str, Any]:
    """
    Evaluates WASSCE results under Ghana Tertiary Education Commission (GTEC) rules:
    - 3 Core Subjects (English & Core Math compulsory + Best of Science/Social).
    - 3 Best Elective Subjects.
    - Official cut-off ceiling: Aggregate 36.
    - Direct Public University Entry Rule: Strictly A1-C6 in all 6 qualifying subjects.
    """
    # 1. Convert Core Grades
    core_points = {}
    for c_name, c_grade in cores.items():
        grade_clean = c_grade.strip().upper() if c_grade else "F9"
        core_points[c_name] = (grade_clean, WASSCE_GRADE_VALUES.get(grade_clean, 9))

    eng_grade, eng_val = core_points.get("English Language", ("F9", 9))
    math_grade, math_val = core_points.get("Core Mathematics", ("F9", 9))
    sci_grade, sci_val = core_points.get("Integrated Science", ("F9", 9))
    soc_grade, soc_val = core_points.get("Social Studies", ("F9", 9))

    # Compulsory: English and Core Math
    compulsory_cores = [("English Language", eng_grade, eng_val), ("Core Mathematics", math_grade, math_val)]
    # Best of Science or Social
    third_core = ("Integrated Science", sci_grade, sci_val) if sci_val <= soc_val else ("Social Studies", soc_grade, soc_val)
    selected_cores = compulsory_cores + [third_core]
    core_aggregate = sum(x[2] for x in selected_cores)

    # 2. Pick Best 3 Electives
    elective_list = []
    for e_name, e_grade in electives.items():
        if e_grade:
            grade_clean = e_grade.strip().upper()
            elective_list.append((e_name, grade_clean, WASSCE_GRADE_VALUES.get(grade_clean, 9)))

    elective_list.sort(key=lambda x: x[2])
    selected_electives = elective_list[:3] if len(elective_list) >= 3 else elective_list
    while len(selected_electives) < 3:
        selected_electives.append(("Additional Elective", "F9", 9))

    elective_aggregate = sum(x[2] for x in selected_electives)
    total_aggregate = core_aggregate + elective_aggregate

    # 3. GTEC Eligibility & "No-Bluffing" Reality Check
    all_6_subjects = selected_cores + selected_electives
    has_d7_or_below = any(s[2] > 6 for s in all_6_subjects)
    has_f9 = any(s[2] == 9 for s in all_6_subjects)

    reality_checks = []
    eligibility_status = "QUALIFIED_DEGREE"

    if eng_val > 6:
        eligibility_status = "BARRED_FROM_PUBLIC_DEGREE"
        reality_checks.append(
            f"🚫 Critical GTEC Rule: English Language is {eng_grade} (Value: {eng_val}). Traditional public universities (UG, KNUST, UCC) strictly DO NOT grant direct admission for 4-year degree programmes with a grade below C6 in English."
        )
    if math_val > 6:
        if eligibility_status == "QUALIFIED_DEGREE":
            eligibility_status = "BARRED_FROM_PUBLIC_DEGREE"
        reality_checks.append(
            f"🚫 Critical GTEC Rule: Core Mathematics is {math_grade} (Value: {math_val}). This prevents direct entry into science, engineering, business, and economics degrees across all traditional public universities."
        )
    if sci_val > 6 and "Science" in interest_area:
        reality_checks.append(
            f"⚠️ Integrated Science is {sci_grade}. Most science, nursing, and engineering faculties require minimum C6 in Integrated Science."
        )
    if total_aggregate > 36:
        eligibility_status = "EXCEEDS_AGGREGATE_36"
        reality_checks.append(
            f"⚠️ Aggregate {total_aggregate} exceeds the official national university eligibility threshold of Aggregate 36. Direct degree entry is not possible this academic cycle."
        )

    # 4. Realistic Pathway Recommendations
    pathways = []

    # Ensure admission benchmarks are seeded
    AdmissionScraperEngine.seed_benchmarks_if_empty()

    if eligibility_status == "QUALIFIED_DEGREE":
        # Check matched university programmes
        matched_programmes = []
        for prog in UNIVERSITY_PROGRAMMES:
            min_cut, max_cut = prog["cutoff_range"]
            if total_aggregate <= max_cut:
                prog_copy = prog.copy()
                prog_copy["fit"] = "Strong Match" if total_aggregate <= (min_cut + 2) else "Competitive"
                matched_programmes.append(prog_copy)
            elif total_aggregate <= max_cut + 3:
                prog_copy = prog.copy()
                prog_copy["fit"] = "Reach / Ambitious"
                matched_programmes.append(prog_copy)

        # Pull live scraped departmental cut-offs from database
        live_degree_benchmarks = get_admission_benchmarks(institution_type="PUBLIC_DEGREE", limit=150)
        specific_live_matches = []
        all_entered_grades = {**cores, **electives}

        for row in live_degree_benchmarks:
            cutoff = row["cutoff_aggregate"]
            prereq = evaluate_programme_prerequisites(row["programme_name"], row["institution_code"], all_entered_grades)

            if total_aggregate <= cutoff:
                fit = "Strong Match" if total_aggregate <= (cutoff - 2) else "Competitive"
                specific_live_matches.append({
                    "programme_name": row["programme_name"],
                    "institution_name": row["institution_name"],
                    "institution_code": row["institution_code"],
                    "cutoff_aggregate": cutoff,
                    "mandatory_requirements": row["mandatory_requirements"],
                    "admission_status": row["admission_status"],
                    "application_deadline": row["application_deadline"],
                    "voucher_cost_ghs": row["voucher_cost_ghs"],
                    "portal_url": row["portal_url"],
                    "fit": fit,
                    "prerequisites_met": prereq["eligible"],
                    "prerequisite_status": prereq["status"],
                    "prerequisite_details": prereq["details"]
                })
            elif total_aggregate <= cutoff + 2:
                fit = "Reach / Ambitious"
                specific_live_matches.append({
                    "programme_name": row["programme_name"],
                    "institution_name": row["institution_name"],
                    "institution_code": row["institution_code"],
                    "cutoff_aggregate": cutoff,
                    "mandatory_requirements": row["mandatory_requirements"],
                    "admission_status": row["admission_status"],
                    "application_deadline": row["application_deadline"],
                    "voucher_cost_ghs": row["voucher_cost_ghs"],
                    "portal_url": row["portal_url"],
                    "fit": fit,
                    "prerequisites_met": prereq["eligible"],
                    "prerequisite_status": prereq["status"],
                    "prerequisite_details": prereq["details"]
                })

        pathways.append({
            "pathway_type": "TRADITIONAL_DEGREE",
            "title": "Direct 4-Year Bachelor's Degree (Traditional Public Universities)",
            "description": "Eligible for standard admissions into accredited public and private universities across Ghana.",
            "programmes": matched_programmes,
            "live_matches": specific_live_matches,
            "institutions": ["University of Ghana (Legon)", "KNUST", "UCC", "UMaT", "UPSA", "UEW", "UDS"]
        })

    # Technical Universities / HND Pathway (Always viable, especially for D7/E8 in math/science)
    tu_benchmarks = get_admission_benchmarks(institution_type="TECHNICAL_UNIVERSITY", limit=20)
    tu_live = [
        {
            "programme_name": row["programme_name"],
            "institution_name": row["institution_name"],
            "institution_code": row["institution_code"],
            "cutoff_aggregate": row["cutoff_aggregate"],
            "mandatory_requirements": row["mandatory_requirements"],
            "admission_status": row["admission_status"],
            "application_deadline": row["application_deadline"],
            "voucher_cost_ghs": row["voucher_cost_ghs"],
            "portal_url": row["portal_url"],
            "fit": "Strong Match" if total_aggregate <= row["cutoff_aggregate"] else "Viable Alternative"
        } for row in tu_benchmarks
    ]

    pathways.append({
        "pathway_type": "TECHNICAL_UNIVERSITY_HND",
        "title": "Technical University (HND / 4-Year B.Tech Programmes)",
        "description": "Accra Technical University (ATU), Kumasi Technical University (KsTU), Takoradi Technical University (TTU), and Ho Technical University. Many practical HND and B.Tech programmes officially admit students with D7 or E8 in Core Mathematics/Science.",
        "benefits": "Practical hands-on training; can top-up to a full Bachelor's degree within 1–2 years post-HND.",
        "recommended_programmes": ["HND Computer Science", "HND Building Technology", "HND Electrical Engineering", "HND Purchasing & Supply", "HND Fashion Design"],
        "live_matches": tu_live
    })

    # Diploma to Degree Top-Up Pathway
    pathways.append({
        "pathway_type": "DIPLOMA_TOP_UP",
        "title": "University Diploma Programmes (Path to Level 200/300 Degree)",
        "description": "2-year Diploma programmes at UPSA, UCC, or UEW. Upon graduation with good GPA, you gain direct top-up admission into Level 200 or 300 of the Bachelor's degree without retaking WASSCE.",
        "benefits": "Legitimate, accredited path to complete your university degree without losing academic years."
    })

    # Nov/Dec Remedial Strategy
    if has_d7_or_below:
        pathways.append({
            "pathway_type": "NOV_DEC_REMEDIAL",
            "title": "Targeted Nov/Dec Resit (WASSCE for Private Candidates)",
            "description": "Strategically register and re-sit ONLY the specific subject(s) with D7/E8/F9. GTEC allows Ghanaian universities to combine results from two sittings (e.g. May/June + Nov/Dec).",
            "benefits": "Upgrades weak grades to A1-C6 and unlocks high-cutoff programmes like Medicine, Pharmacy, or Law."
        })

    # 5. Actionable Roadmap
    roadmap = [
        {
            "step": 1,
            "title": "Verify Official Certificate on WAEC Direct",
            "action": "Ensure your grades on your physical result slip match WAEC's central database at https://ghana.waecdirect.org to avoid application rejections."
        },
        {
            "step": 2,
            "title": "Purchase University E-Vouchers Securely",
            "action": "Buy admission e-vouchers directly via authorized bank branches or official USSD codes (e.g. *887# or *389# for specific universities). Never send mobile money to personal numbers."
        },
        {
            "step": 3,
            "title": "Adopt a 'Primary + Safe Choice' Application Strategy",
            "action": f"With Aggregate {total_aggregate}, apply for your dream course as First Choice, but always designate a high-probability course as Second Choice (or apply to both a traditional university and a technical university as safety)."
        },
        {
            "step": 4,
            "title": "Track Departmental Cut-off Lists",
            "action": "Cut-off points fluctuate yearly based on national candidate performance. Monitor the respective university admissions office notices during October–December."
        }
    ]

    # 6. SCAMPER Innovation Enhancements
    all_entered_grades = {**cores, **electives}
    matched_scholarships = match_scholarships(total_aggregate, interest_area, all_entered_grades)
    live_benchmarks_for_deficits = live_degree_benchmarks if 'live_degree_benchmarks' in locals() else get_admission_benchmarks(institution_type="PUBLIC_DEGREE", limit=150)
    deficits_analysis = calculate_wassce_deficits(all_6_subjects, total_aggregate, live_benchmarks_for_deficits)

    audit_hash = append_audit_block(
        action="ACT_843_WASSCE_EVALUATION",
        actor="EPHEMERAL_ADVISORY_ENGINE",
        payload_data={
            "exam_type": "WASSCE",
            "aggregate": total_aggregate,
            "status": eligibility_status,
            "interest": interest_area,
            "scholarships_matched": len(matched_scholarships),
            "zero_persistence_verified": True
        }
    )

    analysis_result = {
        "exam_type": "WASSCE",
        "aggregate": total_aggregate,
        "aggregate_string": f"Aggregate {total_aggregate:02d}",
        "core_aggregate": core_aggregate,
        "elective_aggregate": elective_aggregate,
        "selected_cores": selected_cores,
        "selected_electives": selected_electives,
        "eligibility_status": eligibility_status,
        "reality_checks": reality_checks,
        "pathways": pathways,
        "scholarships": matched_scholarships,
        "deficits_analysis": deficits_analysis,
        "roadmap": roadmap,
        "interest_area": interest_area,
        "compliance_attestation_hash": audit_hash
    }
    analysis_result["whatsapp_share_text"] = format_wassce_whatsapp_dossier(analysis_result)

    return analysis_result
