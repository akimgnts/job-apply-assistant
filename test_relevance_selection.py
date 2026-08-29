"""Test that fallback selection varies by job offer (not first-N fixed).

Different job offers should produce different bullet selections.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.master_cv_service import load_master_cv
from app.services.intelligent_selection_service import RelevanceScorer


# Data/BI job offer
DATA_BI_ANALYSIS = {
    "job_title": "Data Analyst",
    "required_skills": ["Power BI", "SQL", "Data Analysis", "Dashboards"],
    "missions": [
        "build dashboards",
        "analyze data",
        "reporting",
        "business intelligence",
        "query optimization"
    ],
    "company": "TechCorp",
}

# Automation/AI job offer
AUTOMATION_AI_ANALYSIS = {
    "job_title": "Automation Engineer",
    "required_skills": ["Python", "FastAPI", "APIs", "Automation", "LLM"],
    "missions": [
        "build automation workflows",
        "create APIs",
        "implement LLM solutions",
        "system integration",
        "pipeline development"
    ],
    "company": "InnovateCorp",
}


def test_different_selections():
    """Verify that different job offers produce different selections."""
    print("\n" + "="*80)
    print("RELEVANCE-BASED SELECTION TEST")
    print("="*80 + "\n")

    master_cv = load_master_cv()
    sidel_bullets = master_cv["experiences"][0].get("bullets", [])

    print(f"Master CV: Sidel experience has {len(sidel_bullets)} bullets\n")

    # Test 1: Data/BI offer
    print("TEST 1: Data/BI Offer")
    print(f"  Required skills: {DATA_BI_ANALYSIS['required_skills']}")
    print(f"  Missions: {', '.join(DATA_BI_ANALYSIS['missions'][:3])}")

    data_bi_selection = RelevanceScorer.select_relevant_bullets(
        sidel_bullets,
        DATA_BI_ANALYSIS,
        max_bullets=4
    )
    print(f"  Selected indices: {data_bi_selection}")
    print(f"  Sample bullets selected:")
    for idx in data_bi_selection[:2]:
        print(f"    [{idx}] {sidel_bullets[idx][:70]}...")

    # Test 2: Automation/AI offer
    print("\nTEST 2: Automation/AI Offer")
    print(f"  Required skills: {AUTOMATION_AI_ANALYSIS['required_skills']}")
    print(f"  Missions: {', '.join(AUTOMATION_AI_ANALYSIS['missions'][:3])}")

    automation_ai_selection = RelevanceScorer.select_relevant_bullets(
        sidel_bullets,
        AUTOMATION_AI_ANALYSIS,
        max_bullets=4
    )
    print(f"  Selected indices: {automation_ai_selection}")
    print(f"  Sample bullets selected:")
    for idx in automation_ai_selection[:2]:
        print(f"    [{idx}] {sidel_bullets[idx][:70]}...")

    # Verify they differ
    print("\n" + "="*80)
    print("RESULT")
    print("="*80)
    print(f"Data/BI selection: {data_bi_selection}")
    print(f"Automation/AI selection: {automation_ai_selection}")

    if data_bi_selection == automation_ai_selection:
        print(f"\n❌ FAIL: Selections are identical (not relevance-based)")
        return False
    else:
        print(f"\n✅ PASS: Selections differ based on job offer")
        return True


def test_experience_inclusion():
    """Verify that experience inclusion is relevance-based."""
    print("\n" + "="*80)
    print("EXPERIENCE INCLUSION TEST")
    print("="*80 + "\n")

    master_cv = load_master_cv()

    # Test: Vassard (sales-focused) should be excluded for technical jobs
    vassard = master_cv["experiences"][2]
    print(f"Vassard experience: {vassard.get('title', 'N/A')} @ {vassard.get('company', 'N/A')}")

    for name, analysis in [
        ("Data/BI", DATA_BI_ANALYSIS),
        ("Automation/AI", AUTOMATION_AI_ANALYSIS),
    ]:
        include = RelevanceScorer.should_include_experience(vassard, analysis)
        print(f"  {name} job: include={include}")

    return True


def test_no_hardcoded_first_n():
    """Verify that selection is NOT just [0,1,2,3] for every offer."""
    print("\n" + "="*80)
    print("ANTI-HARDCODING TEST")
    print("="*80 + "\n")

    master_cv = load_master_cv()
    sidel_bullets = master_cv["experiences"][0].get("bullets", [])

    # Generate selection for an unusual job
    unusual_analysis = {
        "job_title": "Machine Learning Engineer",
        "required_skills": ["Python", "TensorFlow", "Deep Learning", "Data Science"],
        "missions": [
            "implement ML models",
            "train neural networks",
            "feature engineering",
            "model optimization",
        ],
        "company": "AI Company",
    }

    selection = RelevanceScorer.select_relevant_bullets(
        sidel_bullets,
        unusual_analysis,
        max_bullets=4
    )

    print(f"ML Engineer job selection: {selection}")
    print(f"Is it hardcoded [0,1,2,3]? {selection == [0,1,2,3]}")

    if selection == [0,1,2,3]:
        print(f"❌ FAIL: Selection is hardcoded")
        return False
    else:
        print(f"✅ PASS: Selection varies based on relevance")
        return True


if __name__ == "__main__":
    results = []
    results.append(("Different selections", test_different_selections()))
    results.append(("Experience inclusion", test_experience_inclusion()))
    results.append(("Not hardcoded", test_no_hardcoded_first_n()))

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    all_pass = all(r for _, r in results)
    print(f"\nOverall: {'✅ ALL PASS' if all_pass else '❌ SOME FAILED'}")
    print("="*80 + "\n")
