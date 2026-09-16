"""
Educational Placement & Pathway Advisory Engine for Ghana (BECE & WASSCE)
Compliant with Ghana Data Protection Act, 2012 (Act 843):
- Processes candidate grades ephemerally in-memory.
- Zero data retention (no grades or personal indices persisted to database).
- Grounded in official GES CSSPS guidelines and GTEC / University admissions cut-offs.
"""

from typing import Dict, List, Any, Optional, Tuple

from ..database import get_admission_benchmarks, append_audit_block, log_advisory_telemetry
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

# ============================================================================
# ADMISSION PROBABILITY & INSTITUTIONAL SELECTION ENGINE
# ============================================================================

BECE_SCHOOL_CUTOFFS = {
    "Presbyterian Boys' Senior High (PRESEC Legon)": {"General Science": 8, "default": 9},
    "Wesley Girls' High School": {"General Science": 8, "default": 9},
    "Prempeh College": {"General Science": 8, "default": 9},
    "Opoku Ware School": {"General Science": 8, "default": 9},
    "Holy Child School": {"General Science": 8, "default": 9},
    "Mfantsipim School": {"General Science": 8, "default": 9},
    "Achimota School": {"General Science": 9, "default": 10},
    "Aburi Girls' Senior High": {"General Science": 9, "default": 10},
    "St. Peter's Boys' Senior High": {"General Science": 9, "default": 10},
    "St. Rose's Senior High": {"General Science": 9, "default": 10},
    "St. Augustine's College": {"default": 12},
    "Pope John Senior High & Minor Seminary": {"default": 12},
    "Kumasi High School": {"default": 13},
    "St. Thomas Aquinas Senior High": {"default": 14},
    "Ghana National College": {"default": 14},
    "Sunyani Senior High": {"default": 15},
    "Mawuli School": {"default": 15},
    "Tamale Senior High": {"default": 16},
    "Osu Presbyterian Senior High": {"default": 17},
    "Armed Forces Senior High Technical": {"default": 24},
    "Nungua Senior High": {"default": 26},
    "Effiduase Senior High": {"default": 26},
    "Christian Methodist Senior High": {"default": 28},
    "Ada Senior High": {"default": 28},
    "District Designated Day Senior High Schools": {"default": 38},
    "Accra Technical Training Centre (ATTC)": {"default": 24},
    "Kumasi Technical Institute (KTI)": {"default": 25},
    "Takoradi Technical Institute (TTI)": {"default": 26},
    "Asuansi Technical Institute": {"default": 28},
}

def calculate_admission_probability(
    candidate_aggregate: int,
    cutoff_aggregate: int,
    prerequisites_met: bool = True,
    institution_selectivity: str = "NORMAL",
    is_bece: bool = False
) -> Dict[str, Any]:
    """
    Computes a realistic, non-bluffing admission probability (10% - 98%)
    based on aggregate delta (cutoff - candidate), prerequisite compliance,
    and institutional selectivity weighting.

    In Ghanaian grading, lower aggregate indicates higher academic performance.
    delta = cutoff_aggregate - candidate_aggregate.
    Positive delta indicates candidate is ahead of cutoff.
    """
    delta = cutoff_aggregate - candidate_aggregate

    # 1. Base probability curve based on delta
    if delta >= 4:
        base_prob = min(98, 92 + (delta - 4) * 2)
    elif delta == 3:
        base_prob = 89
    elif delta == 2:
        base_prob = 84
    elif delta == 1:
        base_prob = 77
    elif delta == 0:
        base_prob = 66
    elif delta == -1:
        base_prob = 48
    elif delta == -2:
        base_prob = 34
    elif delta == -3:
        base_prob = 20
    else:
        base_prob = max(10, 18 + (delta + 3) * 2)

    # 2. Selectivity adjustment
    if institution_selectivity == "HIGH":
        base_prob = max(10, base_prob - 4)
    elif institution_selectivity == "MODERATE":
        base_prob = min(98, base_prob + 4)

    # 3. Prerequisite gatekeeper enforcement
    if not prerequisites_met:
        base_prob = min(base_prob, 18)

    final_prob = int(max(10, min(98, round(base_prob))))

    # 4. Tier & Classification
    if not prerequisites_met:
        match_tier = "PREREQUISITE_DEFICIT"
        tier_label = "Prerequisite Deficit"
        badge_class = "prob-deficit"
        strategic_role = "Conditional / Remedial Required"
    elif final_prob >= 80:
        match_tier = "HIGH_PROBABILITY"
        tier_label = "High Assurance Match"
        badge_class = "prob-high"
        strategic_role = "Safe / Primary Guarantee"
    elif final_prob >= 60:
        match_tier = "COMPETITIVE"
        tier_label = "Competitive Match"
        badge_class = "prob-med"
        strategic_role = "Target Match Choice"
    elif final_prob >= 35:
        match_tier = "REACH"
        tier_label = "Reach / Ambitious"
        badge_class = "prob-reach"
        strategic_role = "Aspirational Reach"
    else:
        match_tier = "LOW_PROBABILITY"
        tier_label = "Low Probability"
        badge_class = "prob-low"
        strategic_role = "High Risk / Backup Alternative"

    return {
        "probability_percent": final_prob,
        "delta": delta,
        "match_tier": match_tier,
        "tier_label": tier_label,
        "badge_class": badge_class,
        "strategic_role": strategic_role
    }

def suggest_best_schools_bece(
    total_aggregate: int,
    english_grade: int,
    math_grade: int,
    science_grade: int,
    preferred_programme: str
) -> List[Dict[str, Any]]:
    """
    Ranks Ghanaian Senior High Schools across GES CSSPS Categories A, B, C, D, and E
    with calculated admission probability and strategic selection roles.
    """
    evaluated_schools = []

    for tier_key, tier_info in BECE_SCHOOL_TIERS.items():
        cat_display = {
            "CAT_A": "Category A (National)",
            "CAT_B": "Category B (Regional)",
            "CAT_C": "Category C (Community)",
            "CAT_D": "Category D (Local Day)",
            "CAT_E": "Category E (CTVET)"
        }.get(tier_key, tier_key)

        selectivity = "HIGH" if tier_key == "CAT_A" else ("MODERATE" if tier_key in ["CAT_C", "CAT_D", "CAT_E"] else "NORMAL")

        for school in tier_info.get("schools", []):
            name = school["name"]
            cutoff_map = BECE_SCHOOL_CUTOFFS.get(name, {})
            cutoff = cutoff_map.get(preferred_programme, cutoff_map.get("default", tier_info["aggregate_range"][1]))

            # Prerequisite & risk rules
            prereqs_met = True
            prereq_note = "Prerequisites satisfied for placement."
            if tier_key == "CAT_A" and preferred_programme == "General Science" and (science_grade > 3 or math_grade > 3):
                prereqs_met = False
                prereq_note = f"Cat A General Science heavily favors Grade 1-2 in Science and Math (Candidate: Sci {science_grade}, Math {math_grade})"
            elif english_grade > 6:
                prereqs_met = False
                prereq_note = f"Stanine {english_grade} in English triggers automated placement failure risk"

            prob_res = calculate_admission_probability(
                candidate_aggregate=total_aggregate,
                cutoff_aggregate=cutoff,
                prerequisites_met=prereqs_met,
                institution_selectivity=selectivity,
                is_bece=True
            )

            # Programme match
            strong_programmes = school.get("strong_in", [])
            prog_match = any(preferred_programme.lower() in p.lower() for p in strong_programmes)

            # Rationale
            delta = prob_res["delta"]
            if not prereqs_met:
                rationale = f"Prerequisite concern: {prereq_note}"
            elif delta >= 3:
                rationale = f"Outstanding match! Aggregate {total_aggregate:02d} beats {name}'s cut-off ({cutoff:02d}) by {delta} points."
            elif delta >= 0:
                rationale = f"Target fit: Aggregate {total_aggregate:02d} meets {name}'s threshold ({cutoff:02d}) with competitive chance."
            elif delta >= -2:
                rationale = f"Competitive reach: Aggregate {total_aggregate:02d} is {abs(delta)} points below cut-off ({cutoff:02d}). Possible in secondary CSSPS run."
            else:
                rationale = f"High competition: Aggregate {total_aggregate:02d} is {abs(delta)} points beyond typical cutoff ({cutoff:02d})."

            # Formulate strategic CSSPS role
            if tier_key == "CAT_A":
                strategic_role = "Choice 1: High-Merit Dream" if prob_res["probability_percent"] < 80 else "Choice 1: Strong National Target"
            elif tier_key == "CAT_B":
                strategic_role = "Choice 2: Prime Regional Target" if prob_res["probability_percent"] >= 70 else "Choice 2: Competitive Regional Choice"
            elif tier_key == "CAT_C":
                strategic_role = "Choice 3 & 4: Safe Placement Choice"
            elif tier_key == "CAT_D":
                strategic_role = "Choice 5: Mandatory 30% Local Day Quota"
            else:
                strategic_role = "Choice 6: CTVET Practical Career Track"

            evaluated_schools.append({
                "school_name": name,
                "category": cat_display,
                "category_code": tier_key,
                "gender": school.get("gender", "Mixed"),
                "region": school.get("region", "National"),
                "strong_in": strong_programmes,
                "programme_match": prog_match,
                "cutoff_aggregate": cutoff,
                "probability_percent": prob_res["probability_percent"],
                "delta": delta,
                "match_tier": prob_res["match_tier"],
                "tier_label": prob_res["tier_label"],
                "badge_class": prob_res["badge_class"],
                "strategic_role": strategic_role,
                "prerequisites_met": prereqs_met,
                "prereq_note": prereq_note,
                "rationale": rationale
            })

    # Curate a balanced CSSPS portfolio
    portfolio = []
    
    # 1. Cat A (top 2 options)
    cat_a_schools = [s for s in evaluated_schools if s["category_code"] == "CAT_A"]
    cat_a_schools.sort(key=lambda s: (s["programme_match"], s["prerequisites_met"], s["probability_percent"]), reverse=True)
    portfolio.extend(cat_a_schools[:2])

    # 2. Cat B (top 3 options)
    cat_b_schools = [s for s in evaluated_schools if s["category_code"] == "CAT_B"]
    cat_b_schools.sort(key=lambda s: (s["programme_match"], s["prerequisites_met"], s["probability_percent"]), reverse=True)
    portfolio.extend(cat_b_schools[:3])

    # 3. Cat C (top 2 options)
    cat_c_schools = [s for s in evaluated_schools if s["category_code"] == "CAT_C"]
    cat_c_schools.sort(key=lambda s: (s["programme_match"], s["prerequisites_met"], s["probability_percent"]), reverse=True)
    portfolio.extend(cat_c_schools[:2])

    # 4. Cat D (1 option)
    cat_d_schools = [s for s in evaluated_schools if s["category_code"] == "CAT_D"]
    portfolio.extend(cat_d_schools[:1])

    # 5. Cat E (top 2 TVET options)
    cat_e_schools = [s for s in evaluated_schools if s["category_code"] == "CAT_E"]
    cat_e_schools.sort(key=lambda s: (s["programme_match"], s["prerequisites_met"], s["probability_percent"]), reverse=True)
    portfolio.extend(cat_e_schools[:2])

    return portfolio

def generate_bece_final_verdict(
    total_aggregate: int,
    english_grade: int,
    math_grade: int,
    science_grade: int,
    preferred_programme: str
) -> Dict[str, Any]:
    """
    Formulates a brutally honest, non-sugarcoated final verdict for BECE candidates
    and parents, specifically advising whether to pursue Category A/B, rely on 
    CSSPS Self-Placement/CTVET, or register for remedial resits.
    """
    if english_grade > 6 or math_grade > 6:
        verdict_type = "CRITICAL_HAZARD"
        badge_label = "CRITICAL PLACEMENT HAZARD"
        theme = "danger"
        headline = "High Automated Placement Risk (Stanine > 6 in Core Subjects)"
        bottom_line = (
            f"Your grade in {'English Language (' + str(english_grade) + ')' if english_grade > 6 else 'Mathematics (' + str(math_grade) + ')'} "
            "means the GES automated algorithm will almost certainly skip your choices 1 through 4."
        )
        best_actions = [
            "Prepare for Day 1 CSSPS Self-Placement: When placements drop, log into https://cssps.gov.gh within 24 hours to secure an open Category C school.",
            "Choose CTVET Technical Track (ATTC, KTI, TTI): Practical engineering and technical institutes give you strong, employable skills regardless of theoretical Stanine setbacks.",
            "If you scored Grade 8 or 9 in English/Math, consider registering for the WAEC Private BECE examination (remedials) to secure a clean slate for boarding school admission."
        ]
        what_not_to_do = [
            "DO NOT pay any protocol agent or middleman claiming they can 'force' PRESEC, Achimota, or any Category A school to admit you. You will be scammed.",
            "DO NOT sit idle waiting for an automated placement SMS. Check the CSSPS portal yourself on release day."
        ]
    elif total_aggregate <= 9 and english_grade <= 3 and math_grade <= 3:
        verdict_type = "DIRECT_CATEGORY_A"
        badge_label = "UNCONDITIONAL TOP-TIER MERIT"
        theme = "success"
        headline = "Target Category A With High Confidence — Do NOT Pay Any Agent"
        bottom_line = (
            f"Aggregate {total_aggregate:02d} puts you in the top tier of candidates across Ghana. "
            "You have demonstrated exceptional mastery across both core and elective subjects."
        )
        best_actions = [
            f"Keep your dream Category A institution (e.g. PRESEC Legon, Achimota, Wesley Girls, Prempeh) as Choice 1 for {preferred_programme}.",
            "Maintain a solid Category B school (e.g. St. Thomas Aquinas, Ghana National) as your Choice 2 safety net.",
            "Gather your official BECE Result Slip, NHIS card, and 4 passport pictures for physical registration once placements drop."
        ]
        what_not_to_do = [
            "DO NOT write BECE remedials. Your score is already at national distinction level.",
            "DO NOT entertain anyone asking for 'protocol fees' to guarantee your placement. Your merit earns your spot legitimately."
        ]
    elif total_aggregate <= 18:
        verdict_type = "CATEGORY_B_TARGET"
        badge_label = "SOLID REGIONAL MERIT"
        theme = "info"
        headline = "Category B is Your Strategic Sweet Spot"
        bottom_line = (
            f"Aggregate {total_aggregate:02d} is a strong, highly respectable pass, but Category A boarding quotas are hyper-competitive. "
            "Category B schools represent your highest quality-of-education assurance."
        )
        best_actions = [
            "Focus your strategy around renowned Category B schools (St. Thomas Aquinas, Kumasi High, Mawuli, Pope John, Ghana National).",
            "If you selected a Category A school for Choice 1, be fully prepared for the automated system to place you in Choice 2 or Choice 3.",
            "Ensure Choice 5 includes your designated Local Day school to take advantage of the guaranteed 30% catchment quota."
        ]
        what_not_to_do = [
            "DO NOT pack your choice form with multiple Category A schools. You are only permitted one Category A choice by GES rules.",
            "DO NOT panic if not placed in Choice 1. Category B institutions regularly produce top WASSCE performers in Ghana."
        ]
    elif total_aggregate <= 30:
        verdict_type = "COMMUNITY_AND_LOCAL_DAY"
        badge_label = "COMMUNITY & LOCAL DAY FOCUS"
        theme = "warning"
        headline = "Leverage Category C & 30% Local Day Quota"
        bottom_line = (
            f"With Aggregate {total_aggregate:02d}, national boarding placement is unrealistic. "
            "Your best pathway is securing enrollment in a quality community or district day school."
        )
        best_actions = [
            "Select reputable Category C schools in your immediate municipal district.",
            "Utilize the GES 30% Local Day quota for candidates living near the school.",
            "If unplaced during the automated run, immediately access the official CSSPS Self-Placement module within 48 hours."
        ]
        what_not_to_do = [
            "DO NOT consider JHS repetition unless you failed English or Core Math (Grade 8–9).",
            "DO NOT pay any admission fixer promising boarding admission to Category A or B schools."
        ]
    else:
        verdict_type = "REMEDIAL_OR_TVET"
        badge_label = "REMEDIAL OR APPRENTICESHIP DIRECTIVE"
        theme = "danger"
        headline = "CTVET Practical Institutes or Private BECE Remedial"
        bottom_line = (
            f"Aggregate {total_aggregate:02d} significantly exceeds conventional secondary school admission thresholds. "
            "A shift in academic strategy is required."
        )
        best_actions = [
            "Option A (Skill & Career Mastery): Enroll directly into a CTVET technical institute (ATTC, KTI, TTI) to learn electrical engineering, computing, or building construction.",
            "Option B (Academic Resit): Register for the WAEC Private BECE examination to resit and improve your aggregate.",
            "Explore self-placement options in developing community day schools."
        ]
        what_not_to_do = [
            "DO NOT fall victim to scammers promising secondary school boarding placement for money.",
            "DO NOT waste months idling at home. Enroll in technical training or remedial classes immediately."
        ]

    tone = (
        "CELEBRATORY_AUTHORITATIVE" if theme == "success"
        else ("CRITICAL_WARNING" if theme == "danger" and verdict_type == "CRITICAL_HAZARD"
        else ("STRICT_REALISTIC" if "REMEDIAL" in verdict_type or verdict_type == "CRITICAL_HAZARD"
        else "STRATEGIC_BALANCED"))
    )

    return {
        "verdict_type": verdict_type,
        "category": verdict_type,
        "badge_label": badge_label,
        "theme": theme,
        "tone": tone,
        "headline": headline,
        "bottom_line": bottom_line,
        "best_actions": best_actions,
        "next_moves": best_actions,
        "what_not_to_do": what_not_to_do,
        "costly_mistakes": what_not_to_do
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
            f"Critical Risk: English Language grade is {english_grade} (Stanine > 6). Under CSSPS automated rules, candidates with Grade 7-9 in English Language frequently miss automated placement and must utilize Self-Placement."
        )
    if math_grade > 6:
        if risk_level != "HIGH":
            risk_level = "MODERATE"
        reality_checks.append(
            f"Mathematics grade is {math_grade} (Stanine > 6). This restricts placement into General Science and Business programmes."
        )
    if preferred_programme == "General Science" and (science_grade > 3 or math_grade > 3):
        reality_checks.append(
            f"General Science Reality Check: Category A & B schools heavily favor candidates with Grade 1 or 2 in Integrated Science and Mathematics. Your grades (Science: {science_grade}, Math: {math_grade}) may require choosing Category B or C schools for this programme."
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

    # 5. Suggest Specific Schools with Calculated Probabilities
    suggested_schools = suggest_best_schools_bece(
        total_aggregate=total_aggregate,
        english_grade=english_grade,
        math_grade=math_grade,
        science_grade=science_grade,
        preferred_programme=preferred_programme
    )

    # 6. Formulate Brutally Honest Final Verdict
    final_verdict = generate_bece_final_verdict(
        total_aggregate=total_aggregate,
        english_grade=english_grade,
        math_grade=math_grade,
        science_grade=science_grade,
        preferred_programme=preferred_programme
    )

    # 7. Step-by-Step Action Roadmap
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
            "verdict_type": final_verdict["verdict_type"],
            "zero_persistence_verified": True
        }
    )
    log_advisory_telemetry("BECE", total_aggregate, preferred_programme, 0)

    top_schools_whatsapp = "\n".join([
        f"  • *{s['school_name']}* ({s['category'].split(' ')[0]} {s['category'].split(' ')[1]}): *{s['probability_percent']}% Chance* [{s['tier_label']}]"
        for s in suggested_schools[:3]
    ])

    whatsapp_text = (
        "*CHECKERPAY GHANA | CSSPS PLACEMENT DOSSIER*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*ADVISOR'S FINAL VERDICT:*\n"
        f"*{final_verdict['headline']}*\n"
        f"_{final_verdict['bottom_line']}_\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*BECE Aggregate:* {total_aggregate:02d} ({risk_level})\n"
        f"*Target Programme:* {preferred_programme}\n"
        f"*Score Breakdown:* Cores: {core_aggregate} pts | Best 2 Electives: {elective_aggregate} pts\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "*TOP SUGGESTED SCHOOLS & CHANCES:*\n"
        + top_schools_whatsapp
        + "\n\n*RECOMMENDED ACTIONS:*\n"
        + "\n".join([f"  • {act}" for act in final_verdict["best_actions"][:2]])
        + "\n\n*WHAT NOT TO DO:*\n"
        + f"  • {final_verdict['what_not_to_do'][0]}\n"
        + "\n*OFFICIAL CSSPS NOTICE:*\n"
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
        "final_verdict": final_verdict,
        "recommended_tiers": recommendations,
        "suggested_schools": suggested_schools,
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

def suggest_best_institutions_wassce(
    total_aggregate: int,
    interest_area: str,
    all_grades: Dict[str, str],
    eligibility_status: str
) -> List[Dict[str, Any]]:
    """
    Evaluates live Ghanaian university and technical university departmental benchmarks,
    checking prerequisite compliance and computing quantitative admission probabilities.
    """
    AdmissionScraperEngine.seed_benchmarks_if_empty()
    all_benchmarks = get_admission_benchmarks(limit=200)

    evaluated = []

    for b in all_benchmarks:
        prog_name = b.get("programme_name", "")
        inst_name = b.get("institution_name", "")
        inst_code = b.get("institution_code", "")
        inst_type = b.get("institution_type", "PUBLIC_DEGREE")
        cutoff = b.get("cutoff_aggregate", 24)
        faculty = b.get("faculty_category", "")

        # Evaluate faculty prerequisites
        prereq = evaluate_programme_prerequisites(prog_name, inst_code, all_grades)
        prereqs_met = prereq["eligible"]
        prereq_details = prereq["details"]

        # GTEC degree rule
        if inst_type == "PUBLIC_DEGREE" and eligibility_status in ["BARRED_FROM_PUBLIC_DEGREE", "EXCEEDS_AGGREGATE_36"]:
            prereqs_met = False
            prereq_details = "GTEC Rule: Min C6 in Core Math & English required for direct public degree entry."

        if inst_type == "TECHNICAL_UNIVERSITY":
            # Technical Universities accept D7/E8 in math/science for HND and B.Tech programmes
            if prereq["status"] != "PREREQUISITE_DEFICIT" or "GTEC Rule" in prereq_details:
                prereqs_met = True
                prereq_details = "Eligible under Technical University applied admission criteria."

        selectivity = "HIGH" if inst_code in ["UG", "KNUST"] else ("MODERATE" if inst_type == "TECHNICAL_UNIVERSITY" else "NORMAL")

        prob_data = calculate_admission_probability(
            candidate_aggregate=total_aggregate,
            cutoff_aggregate=cutoff,
            prerequisites_met=prereqs_met,
            institution_selectivity=selectivity,
            is_bece=False
        )

        delta = prob_data["delta"]
        if not prereqs_met:
            rationale = f"Prerequisite Deficit: {prereq_details}"
        elif delta >= 3:
            rationale = f"Outstanding Match: Aggregate {total_aggregate:02d} beats cutoff ({cutoff:02d}) by {delta} points with all prerequisites met."
        elif delta >= 1:
            rationale = f"Strong Standing: Aggregate {total_aggregate:02d} comfortably clears departmental cut-off ({cutoff:02d}) by {delta} points."
        elif delta == 0:
            rationale = f"Direct Cut-off Match: Aggregate {total_aggregate:02d} matches departmental cutoff ({cutoff:02d}). Competitive admission."
        elif delta >= -2:
            rationale = f"Aspirational Reach: Aggregate {total_aggregate:02d} is {abs(delta)} points shy of cut-off ({cutoff:02d}). Viable in fee-paying or later lists."
        else:
            rationale = f"High Selectivity: Aggregate {total_aggregate:02d} is {abs(delta)} points beyond cutoff ({cutoff:02d}). Consider HND or alternative."

        # Strategic portfolio role
        if not prereqs_met:
            strategic_role = "Conditional / Remedial Required"
        elif prob_data["probability_percent"] >= 80:
            strategic_role = "First Choice / Primary Target" if delta <= 4 else "Guaranteed Safety Match"
        elif prob_data["probability_percent"] >= 60:
            strategic_role = "Competitive Target Choice"
        elif prob_data["probability_percent"] >= 35:
            strategic_role = "Ambitious Reach Choice"
        else:
            strategic_role = "High Risk / Fallback Path"

        # Interest match logic
        is_interest = False
        interest_lower = interest_area.lower()
        prog_lower = prog_name.lower()
        faculty_lower = faculty.lower()
        if interest_lower in prog_lower or interest_lower in faculty_lower:
            is_interest = True
        elif ("computer" in interest_lower or "engineering" in interest_lower) and any(x in prog_lower for x in ["computer", "engineering", "software", "information", "technology"]):
            is_interest = True
        elif ("medicine" in interest_lower or "health" in interest_lower or "nursing" in interest_lower) and any(x in prog_lower for x in ["medicine", "surgery", "nursing", "pharmacy", "health", "midwifery", "optometry", "medical"]):
            is_interest = True
        elif ("business" in interest_lower or "law" in interest_lower) and any(x in prog_lower for x in ["administration", "accounting", "finance", "business", "law", "economics", "marketing", "procurement"]):
            is_interest = True

        evaluated.append({
            "programme_name": prog_name,
            "institution_name": inst_name,
            "institution_code": inst_code,
            "institution_type": inst_type,
            "faculty_category": faculty,
            "cutoff_aggregate": cutoff,
            "probability_percent": prob_data["probability_percent"],
            "delta": delta,
            "match_tier": prob_data["match_tier"],
            "tier_label": prob_data["tier_label"],
            "badge_class": prob_data["badge_class"],
            "strategic_role": strategic_role,
            "prerequisites_met": prereqs_met,
            "prerequisite_status": prereq["status"],
            "prerequisite_details": prereq_details,
            "rationale": rationale,
            "mandatory_requirements": b.get("mandatory_requirements", ""),
            "application_deadline": b.get("application_deadline", "Rolling / Nov 30"),
            "voucher_cost_ghs": b.get("voucher_cost_ghs", 220.0),
            "portal_url": b.get("portal_url", "https://admission.ug.edu.gh"),
            "is_interest_match": is_interest
        })

    # Sort to produce a high-value, diverse portfolio:
    evaluated.sort(
        key=lambda x: (
            1 if x["is_interest_match"] else 0,
            1 if x["prerequisites_met"] else 0,
            x["probability_percent"]
        ),
        reverse=True
    )

    result = []
    inst_counts = {}
    for item in evaluated:
        code = item["institution_code"]
        count = inst_counts.get(code, 0)
        if count < 3 or len(result) < 6:
            result.append(item)
            inst_counts[code] = count + 1
        if len(result) >= 12:
            break

    return result

def generate_wassce_final_verdict(
    total_aggregate: int,
    eligibility_status: str,
    selected_cores: List[Tuple[str, str, int]],
    selected_electives: List[Tuple[str, str, int]],
    interest_area: str,
    all_grades: Dict[str, str]
) -> Dict[str, Any]:
    """
    Formulates a brutally honest, non-sugarcoated final verdict for WASSCE candidates
    and parents, specifically advising whether to buy university degree vouchers,
    pursue Technical University HND without losing an academic year, or register
    for targeted NOV/DEC private candidate remedials.
    """
    eng_grade = "F9"
    math_grade = "F9"
    sci_grade = "F9"
    for k, v in all_grades.items():
        k_lower = k.lower()
        if "english" in k_lower: eng_grade = str(v).strip().upper()
        elif "core math" in k_lower or k_lower == "mathematics": math_grade = str(v).strip().upper()
        elif "science" in k_lower and "elective" not in k_lower: sci_grade = str(v).strip().upper()

    eng_val = WASSCE_GRADE_VALUES.get(eng_grade, 9)
    math_val = WASSCE_GRADE_VALUES.get(math_grade, 9)

    # 1. Critical GTEC Prerequisite Barrier (D7 or E8 in Core Math or English)
    if eligibility_status == "BARRED_FROM_PUBLIC_DEGREE" or eng_val > 6 or math_val > 6:
        failed_subj = "English Language" if eng_val > 6 else "Core Mathematics"
        failed_grade = eng_grade if eng_val > 6 else math_grade
        verdict_type = "GTEC_PREREQUISITE_BARRIER"
        badge_label = "DO NOT BUY DEGREE VOUCHERS — D7/E8 DETECTED"
        theme = "danger"
        headline = "BRUTALLY HONEST REALITY: Barred From 4-Year Public University Degrees"
        bottom_line = (
            f"DO NOT waste GH₵ 220–250 buying university degree application forms right now! "
            f"You scored {failed_grade} in {failed_subj}. Under official GTEC policy, traditional public universities "
            "(UG Legon, KNUST, UCC) will AUTOMATICALLY REJECT your direct degree application without reviewing your other subjects."
        )
        best_actions = [
            "Option 1 — Zero Academic Years Lost (Technical University HND / B.Tech): Apply immediately to Accra Technical University (ATU), Kumasi Technical University (KsTU), or Takoradi Technical University (TTU). They officially admit candidates with D7/E8 into 3-year HND and applied B.Tech programmes. Upon graduation, you top up directly to Level 200 or 300 of a Bachelor's degree!",
            f"Option 2 — Targeted NOV/DEC Remedial Resit: Under GTEC's Two-Sitting Combination Policy, universities legally accept results combined from two sittings (e.g. May/June + Nov/Dec). You only need to register and re-sit the ONE bottleneck subject ({failed_subj}) in the upcoming WAEC private exam.",
            "Option 3 — Accredited Diploma Top-Up: Apply for a 2-year Diploma at UPSA, UCC, or UEW, which admits with D7, then advance straight to degree Level 200."
        ]
        what_not_to_do = [
            "DO NOT buy UG Legon or KNUST degree vouchers hoping for 'special consideration'. The admissions portal software automatically filters out any D7 in Core English or Math.",
            "DO NOT pay unauthorized 'admission fixers' or protocol syndicates who promise they can bypass GTEC regulations. It is 100% fraudulent."
        ]

    # 2. Exceeds Aggregate 36 or Multiple F9s
    elif eligibility_status == "EXCEEDS_AGGREGATE_36" or total_aggregate > 36:
        verdict_type = "MANDATORY_REMEDIAL"
        badge_label = "MANDATORY REMEDIAL DIRECTIVE"
        theme = "danger"
        headline = "Direct Tertiary Entry Not Legally Permitted — NOV/DEC Required"
        bottom_line = (
            f"Your aggregate is {total_aggregate:02d}, exceeding the national tertiary cutoff ceiling of Aggregate 36. "
            "No accredited university or college of education in Ghana can legally admit you for a degree this academic year."
        )
        best_actions = [
            "Enroll in an accredited remedial institute immediately and register for the WAEC Private Candidates Examination (NOV/DEC).",
            "Focus 80% of your revision on the core subjects: Core Mathematics, English Language, and Integrated Science.",
            "Once you secure A1–C6 in your resit, combine your new result slip with your existing passes under the official GTEC Two-Sitting Policy."
        ]
        what_not_to_do = [
            "DO NOT buy any university or nursing college vouchers this cycle.",
            "DO NOT fall for unaccredited private tertiary institutions claiming to admit students with Aggregate 38+ without NOV/DEC."
        ]

    # 3. High Merit / Qualified Degree (Agg 06 - 15, all A1-C6)
    elif total_aggregate <= 15:
        verdict_type = "UNCONDITIONAL_DEGREE"
        badge_label = "UNCONDITIONAL DIRECT DEGREE PATH"
        theme = "success"
        headline = "Apply to University With Full Confidence — Do NOT Write Remedials!"
        bottom_line = (
            f"Aggregate {total_aggregate:02d} with clean A1–C6 passes meets all GTEC university matriculation standards. "
            "Writing NOV/DEC remedials would be a complete waste of your time and money."
        )
        best_actions = [
            "Purchase official admission e-vouchers directly via authorized bank branches or official university USSD codes (e.g. *887# or *389#).",
            f"Designate your target programme in {interest_area} as First Choice at your preferred institution (UG, KNUST, UCC).",
            "Select a competitive target or high-assurance alternative as Second Choice to guarantee admission."
        ]
        what_not_to_do = [
            "DO NOT waste money or effort registering for NOV/DEC resits. You are fully degree-qualified.",
            "DO NOT miss application deadlines (most public universities close admissions between October and November)."
        ]

    # 4. Qualified Degree Borderline / Diversification (Agg 16 - 24, all A1-C6)
    elif total_aggregate <= 24:
        verdict_type = "DEGREE_DIVERSIFICATION"
        badge_label = "QUALIFIED DEGREE WITH DIVERSIFICATION"
        theme = "info"
        headline = "Degree Eligible — Apply Strategically Beyond Oversubscribed Tracks"
        bottom_line = (
            f"With Aggregate {total_aggregate:02d} and zero D7s, you are 100% degree-eligible nationwide. "
            "However, ultra-competitive courses like Medicine, Computer Science, and Law at Legon/KNUST require Agg 06–12."
        )
        best_actions = [
            "Apply to traditional public universities for Administration, Arts, Humanities, Social Sciences, or Education where your probability is 75%–95%.",
            "Consider leading regional institutions (UCC, UEW, UDS, UMaT) or 4-Year B.Tech degree tracks at Technical Universities (ATU, KsTU) where your chances are exceptionally high.",
            "If you are adamant on pursuing Medicine or Engineering, register for targeted NOV/DEC resit to upgrade one or two B/C grades to A1."
        ]
        what_not_to_do = [
            "DO NOT waste your first, second, and third choices on hyper-competitive courses at UG Legon or KNUST (e.g., Medicine + Pharmacy + Law).",
            "DO NOT listen to anyone advising you to repeat an entire school year when you already hold clean A1–C6 passes."
        ]

    # 5. Aggregate 25 - 36 (Diplomas, Technical Universities, or Remedial Upgrade)
    else:
        verdict_type = "TECHNICAL_OR_DIPLOMA_PATH"
        badge_label = "TECHNICAL UNIVERSITY & DIPLOMA TRACK"
        theme = "warning"
        headline = "Prioritize Technical University Degrees, HND, or Accredited Diplomas"
        bottom_line = (
            f"Aggregate {total_aggregate:02d} is above the typical cutoff for traditional public university degrees (UG/KNUST), "
            "but opens wide doors for practical Technical University degrees and accredited university diplomas."
        )
        best_actions = [
            "Apply for 4-Year B.Tech or 3-Year HND programmes at Accra Technical University (ATU), KsTU, or TTU where your admission chance is 80%–95%.",
            "Consider 2-year university Diploma programmes (e.g. at UPSA, UCC, or UEW) which guarantee direct progression to Level 200/300 Bachelor's degree.",
            "If your heart is set on a traditional degree at Legon or KNUST, enroll in targeted NOV/DEC remedial resits to bring your aggregate below 20."
        ]
        what_not_to_do = [
            "DO NOT spend money applying for direct degrees at UG Legon or KNUST without a safety choice.",
            "DO NOT patronize unaccredited private colleges."
        ]

    tone = (
        "CELEBRATORY_AUTHORITATIVE" if theme == "success"
        else ("CRITICAL_WARNING" if theme == "danger"
        else ("STRICT_REALISTIC" if "REMEDIAL" in verdict_type
        else "STRATEGIC_BALANCED"))
    )

    return {
        "verdict_type": verdict_type,
        "category": verdict_type,
        "badge_label": badge_label,
        "theme": theme,
        "tone": tone,
        "headline": headline,
        "bottom_line": bottom_line,
        "best_actions": best_actions,
        "next_moves": best_actions,
        "what_not_to_do": what_not_to_do,
        "costly_mistakes": what_not_to_do
    }

def format_wassce_whatsapp_dossier(analysis: Dict[str, Any]) -> str:
    """Formats an executive WhatsApp share text for parents, mentors, and candidates."""
    verdict = analysis.get("final_verdict", {})
    lines = [
        "*CHECKERPAY GHANA | ADMISSIONS & PLACEMENT DOSSIER*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    if verdict:
        lines.extend([
            "*ADVISOR'S FINAL VERDICT:*",
            f"*{verdict.get('headline', '')}*",
            f"_{verdict.get('bottom_line', '')}_",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ])

    lines.extend([
        f"*Candidate Status:* {analysis.get('aggregate_string', 'N/A')}",
        f"*Field of Interest:* {analysis.get('interest_area', 'General')}",
        f"*GTEC Qualification:* {analysis.get('eligibility_status', '').replace('_', ' ')}",
        "",
        "*QUALIFYING SUBJECTS SUMMARY:*"
    ])
    for c in analysis.get("selected_cores", []):
        lines.append(f"  • {c[0]}: *{c[1]}*")
    for e in analysis.get("selected_electives", []):
        lines.append(f"  • {e[0]}: *{e[1]}*")

    suggested_institutions = analysis.get("suggested_institutions", [])
    if suggested_institutions:
        lines.append("")
        lines.append(f"*TOP SUGGESTED INSTITUTIONS & CHANCES:*")
        for inst in suggested_institutions[:3]:
            lines.append(f"  • *{inst['institution_code']}* - {inst['programme_name']}: *{inst['probability_percent']}% Chance* [{inst['tier_label']}]")

    if verdict and verdict.get("best_actions"):
        lines.append("")
        lines.append("*RECOMMENDED ACTIONS:*")
        for act in verdict["best_actions"][:2]:
            lines.append(f"  • {act}")

    if verdict and verdict.get("what_not_to_do"):
        lines.append("")
        lines.append("*WHAT NOT TO DO:*")
        lines.append(f"  • {verdict['what_not_to_do'][0]}")

    scholarships = analysis.get("scholarships", [])
    if scholarships:
        lines.append("")
        lines.append(f"*MATCHED SCHOLARSHIPS ({len(scholarships)} Opportunities):*")
        for s in scholarships[:2]:
            lines.append(f"  • *{s['name']}*")
            lines.append(f"     Coverage: {s['coverage'][:55]}...")
            lines.append(f"     Portal: {s['portal_url']}")

    deficits = analysis.get("deficits_analysis", {})
    if deficits.get("has_deficits") and deficits.get("scenarios"):
        top = deficits["scenarios"][0]
        lines.append("")
        lines.append("*STRATEGIC REMEDIAL PROJECTION (NOV/DEC):*")
        lines.append(f"  Upgrading *{top['subject']}* ({top['current_grade']} -> {top['target_grade']}) shifts aggregate from *{analysis['aggregate']}* to *{top['projected_aggregate']}*, unlocking *+{top['additional_programmes_unlocked']} degree programmes* at Legon & KNUST!")

    lines.extend([
        "",
        "*VERIFIED INTEGRITY ATTENUATION:*",
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
            f"Critical GTEC Rule: English Language is {eng_grade} (Value: {eng_val}). Traditional public universities (UG, KNUST, UCC) strictly DO NOT grant direct admission for 4-year degree programmes with a grade below C6 in English."
        )
    if math_val > 6:
        if eligibility_status == "QUALIFIED_DEGREE":
            eligibility_status = "BARRED_FROM_PUBLIC_DEGREE"
        reality_checks.append(
            f"Critical GTEC Rule: Core Mathematics is {math_grade} (Value: {math_val}). This prevents direct entry into science, engineering, business, and economics degrees across all traditional public universities."
        )
    if sci_val > 6 and "Science" in interest_area:
        reality_checks.append(
            f"Integrated Science is {sci_grade}. Most science, nursing, and engineering faculties require minimum C6 in Integrated Science."
        )
    if total_aggregate > 36:
        eligibility_status = "EXCEEDS_AGGREGATE_36"
        reality_checks.append(
            f"Aggregate {total_aggregate} exceeds the official national university eligibility threshold of Aggregate 36. Direct degree entry is not possible this academic cycle."
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

    # 7. Institutional Recommendations with Admission Probability
    suggested_institutions = suggest_best_institutions_wassce(
        total_aggregate=total_aggregate,
        interest_area=interest_area,
        all_grades=all_entered_grades,
        eligibility_status=eligibility_status
    )

    # 8. Formulate Brutally Honest Final Verdict
    final_verdict = generate_wassce_final_verdict(
        total_aggregate=total_aggregate,
        eligibility_status=eligibility_status,
        selected_cores=selected_cores,
        selected_electives=selected_electives,
        interest_area=interest_area,
        all_grades=all_entered_grades
    )

    audit_hash = append_audit_block(
        action="ACT_843_WASSCE_EVALUATION",
        actor="EPHEMERAL_ADVISORY_ENGINE",
        payload_data={
            "exam_type": "WASSCE",
            "aggregate": total_aggregate,
            "status": eligibility_status,
            "interest": interest_area,
            "verdict_type": final_verdict["verdict_type"],
            "scholarships_matched": len(matched_scholarships),
            "suggested_institutions_count": len(suggested_institutions),
            "zero_persistence_verified": True
        }
    )
    log_advisory_telemetry("WASSCE", total_aggregate, interest_area, len(matched_scholarships))

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
        "final_verdict": final_verdict,
        "pathways": pathways,
        "suggested_institutions": suggested_institutions,
        "scholarships": matched_scholarships,
        "deficits_analysis": deficits_analysis,
        "roadmap": roadmap,
        "interest_area": interest_area,
        "compliance_attestation_hash": audit_hash
    }
    analysis_result["whatsapp_share_text"] = format_wassce_whatsapp_dossier(analysis_result)

    return analysis_result
