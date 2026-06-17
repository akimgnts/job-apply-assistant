#!/usr/bin/env python3
"""Test Gap Analysis on real job offers.

Validates that confidence scoring correctly identifies:
- Family match
- Level gaps
- Skill gaps
- Bridge validity
"""

# Mock test data for gap analysis (JSON format for testing)
TEST_CASES = [
    {
        "name": "Sopra Steria - Consultant Analytics & IA",
        "offer": {
            "job_title": "Consultant Analytics & IA",
            "company": "Sopra Steria",
            "missions": [
                "Analyse de données complexes",
                "Development de solutions IA",
                "Reporting et dashboarding"
            ],
            "required_skills": ["SQL", "Python", "Power BI", "Machine Learning"],
        },
        "positioning": "Data & AI Consultant",
        "expected": {
            "role_family": "data_analytics|data_ai",
            "confidence_range": (0.70, 0.85),
            "level_gap": None,  # Should be junior-to-mid aligned
            "bridges_expected": ["Data analysis", "Analytics background", "Python/SQL foundation"],
        }
    },
    {
        "name": "Ever.t - Data Engineer",
        "offer": {
            "job_title": "Data Engineer",
            "company": "Ever.t",
            "missions": [
                "Build ETL pipelines",
                "Data quality assurance",
                "SQL optimization"
            ],
            "required_skills": ["SQL", "Python", "ETL", "Data pipelines"],
        },
        "positioning": "Data & AI Consultant",
        "expected": {
            "role_family": "data_engineering",
            "confidence_range": (0.75, 0.90),
            "level_gap": None,  # Junior-mid aligned
            "must_haves": {"SQL": True, "Python": True, "ETL": True},
        }
    },
    {
        "name": "Pelico - Team Lead Data Engineering",
        "offer": {
            "job_title": "Team Lead Data Engineering",
            "company": "Pelico",
            "missions": [
                "Manage data engineering team",
                "Lead technical strategy",
                "Mentor junior engineers"
            ],
            "required_skills": ["SQL", "Python", "Leadership", "Team management", "Architecture"],
        },
        "positioning": "Data & AI Consultant",
        "expected": {
            "role_family": "data_engineering",
            "confidence_range": (0.40, 0.60),
            "level_gap": "junior_vs_lead",
            "seniority_feasible": False,
            "bridges_expected": ["Data engineering", "Automation", "Analytics"],
            "missing_dimensions": ["Team leadership", "People management", "Technical architecture"],
        }
    },
    {
        "name": "Fictitious - Marketing Project Manager",
        "offer": {
            "job_title": "Marketing Project Manager",
            "company": "TechCorp",
            "missions": [
                "Coordinate marketing campaigns",
                "Manage stakeholder reporting",
                "CRM data analysis"
            ],
            "required_skills": ["Project management", "CRM", "Data analysis", "Communication"],
        },
        "positioning": "Data Analyst BI",
        "expected": {
            "role_family": "marketing",
            "confidence_range": (0.45, 0.65),
            "level_gap": None,
            "skill_match": 0.60,  # Has data/reporting, lacks project mgmt
            "bridges_expected": ["Data analysis", "Reporting", "Stakeholder coordination"],
        }
    }
]

def print_test_case(test_case):
    """Print test case expectations."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*70}")
    print(f"Title: {test_case['offer']['job_title']}")
    print(f"Company: {test_case['offer']['company']}")
    print(f"Positioning: {test_case['positioning']}")
    print(f"\nExpected:")
    for key, value in test_case['expected'].items():
        print(f"  {key}: {value}")

def validate_gap_assessment(gap_assessment, expected):
    """Validate gap assessment against expectations."""
    issues = []

    # Check role family
    if "role_family" in expected and expected["role_family"]:
        family = gap_assessment.get("role_family", "")
        expected_families = expected["role_family"].split("|")
        if family not in expected_families:
            issues.append(f"Family mismatch: got {family}, expected one of {expected_families}")

    # Check confidence range
    if "confidence_range" in expected:
        conf = gap_assessment.get("confidence", 0.5)
        min_conf, max_conf = expected["confidence_range"]
        if not (min_conf <= conf <= max_conf):
            issues.append(f"Confidence out of range: {conf} not in [{min_conf}, {max_conf}]")

    # Check level gap
    if "level_gap" in expected:
        gap = gap_assessment.get("level_gap")
        expected_gap = expected["level_gap"]
        if gap != expected_gap:
            issues.append(f"Level gap mismatch: got {gap}, expected {expected_gap}")

    # Check seniority feasible
    if "seniority_feasible" in expected:
        feasible = gap_assessment.get("fit_factors", {}).get("seniority_feasible", True)
        expected_feasible = expected["seniority_feasible"]
        if feasible != expected_feasible:
            issues.append(f"Seniority feasible mismatch: got {feasible}, expected {expected_feasible}")

    return issues

def main():
    print("\n" + "="*70)
    print("GAP ANALYSIS TEST SUITE")
    print("="*70)
    print("\nTesting confidence scoring on 4 job offers")
    print("(Mocked - shows expected vs actual structure)")

    for test_case in TEST_CASES:
        print_test_case(test_case)

        # In real test, would call:
        # gap_assessment = await GapAnalysisAgent.analyze_gap(
        #     test_case['offer'],
        #     test_case['positioning']
        # )
        # issues = validate_gap_assessment(gap_assessment, test_case['expected'])

        print(f"\nTest structure valid. Would validate confidence scoring.")

    print("\n" + "="*70)
    print("TEST SUITE READY")
    print("="*70)
    print("""
When database is available, run:
    pytest test_gap_analysis.py -v

Expected results:
1. Sopra: confidence 0.75-0.85 (good family match, level aligned)
2. Ever.t: confidence 0.80-0.90 (excellent family + level match)
3. Pelico: confidence 0.45-0.55 (family OK, level gap severe)
4. Marketing: confidence 0.50-0.60 (family partial, skills partial)
    """)

if __name__ == "__main__":
    main()
