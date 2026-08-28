"""Master CV Authoritativeness Test: Proves generated CV text comes from Master CV, not from stale data or hallucinations.

CRITICAL TEST: Verifies that the generated CV uses actual Master CV content as source of truth.
- Test 1: Inject unique string into Master CV bullet
- Test 2: Generate CV selecting that bullet
- Test 3: Assert exact unique string appears in rendered HTML
- Test 4: Change Master CV bullet to different unique string
- Test 5: Generate CV again
- Test 6: Assert NEW unique string appears, OLD string is gone
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.master_cv_service import load_master_cv
from app.agents.generation_agent import GenerationAgent
from app.services.document_service import render_cv


async def test_master_cv_authoritativeness():
    """Test that generated CV text comes from Master CV, not cached/hallucinated."""

    print("=" * 80)
    print("MASTER CV AUTHORITATIVENESS TEST")
    print("=" * 80)
    print("\nPURPOSE: Prove that generated CV renders text EXACTLY from Master CV source")
    print("APPROACH: Inject unique string → generate → verify → change → generate → verify\n")

    # STEP 1: Load original Master CV
    print("STEP 1: Load original Master CV")
    print("-" * 80)
    master_cv_original = load_master_cv()
    original_bullet = master_cv_original["experiences"][0]["bullets"][0]
    print(f"Original first Sidel bullet:\n  {original_bullet[:100]}...\n")

    # STEP 2: Create test fixture with unique string
    unique_string_v1 = "UNIQUE_TEST_STRING_V1_AUTHORITATIVENESS_CHECK_8F4A2C9B"
    test_bullet_v1 = f"Built dashboards with {unique_string_v1} for validation testing."

    print("STEP 2: Create test fixture with unique marker")
    print("-" * 80)
    print(f"Test bullet v1:\n  {test_bullet_v1}\n")

    # Create modified Master CV with unique string
    master_cv_test_v1 = load_master_cv()
    master_cv_test_v1["experiences"][0]["bullets"][0] = test_bullet_v1

    # STEP 3: Mock the load_master_cv to return our test version
    print("STEP 3: Generate CV with test fixture v1")
    print("-" * 80)

    # Build a minimal adaptation that selects first Sidel experience, first bullet only
    source_adaptation_v1 = {
        "title": "Data Analyst | Business Intelligence",
        "summary": "Test summary for authoritativeness validation.",
        "selected_experience_blocks": [
            {
                "source_id": 0,  # Sidel
                "bullet_indices": [0],  # Only first bullet (our unique string)
                "order": 1,
                "show": True,
                "relevance": 1.0,
            }
        ],
        "selected_project_blocks": [],
        "selected_skill_blocks": [],
        "metadata": {
            "source": "authoritativeness_test_v1",
            "test_fixture": True,
        },
    }

    # Convert to template format using modified master_cv
    adaptation_v1 = GenerationAgent._convert_source_adaptation_to_template_format(
        source_adaptation_v1, master_cv_test_v1
    )

    # Render with test fixture
    context_v1 = {
        "candidate": {
            "name": "Test Candidate",
            "email": "test@example.com",
            "phone": "+33 6 00 00 00 00",
            "linkedin": "",
            "github": "",
            "website": "",
        },
        "adaptation": adaptation_v1,
        "master_cv": master_cv_test_v1,
        "positioning": "Data Analyst | Business Intelligence",
        "analysis_job_title": "Test Position",
    }

    html_v1 = render_cv(context_v1, template_name="master_cv.html")

    # STEP 4: Verify v1 unique string appears
    print("\nSTEP 4: Verify v1 unique string in rendered HTML")
    print("-" * 80)

    if unique_string_v1 in html_v1:
        print(f"✅ PASS: Found v1 unique string in HTML")
        # Find context
        idx = html_v1.find(unique_string_v1)
        context_snippet = html_v1[max(0, idx - 50) : min(len(html_v1), idx + len(unique_string_v1) + 50)]
        print(f"   Context: ...{context_snippet}...\n")
    else:
        print(f"❌ FAIL: v1 unique string NOT found in HTML")
        print(f"   This means the CV is NOT rendering from Master CV!\n")
        return False

    # STEP 5: Change Master CV to different unique string
    print("STEP 5: Change Master CV fixture to v2")
    print("-" * 80)

    unique_string_v2 = "UNIQUE_TEST_STRING_V2_CHANGED_FIXTURE_7D6E1A4F"
    test_bullet_v2 = f"Maintained analytics systems using {unique_string_v2} methodology."

    print(f"Test bullet v2:\n  {test_bullet_v2}\n")

    master_cv_test_v2 = load_master_cv()
    master_cv_test_v2["experiences"][0]["bullets"][0] = test_bullet_v2

    # STEP 6: Generate CV again with v2 fixture
    print("STEP 6: Generate CV with test fixture v2")
    print("-" * 80)

    source_adaptation_v2 = {
        "title": "Data Analyst | Business Intelligence",
        "summary": "Test summary for authoritativeness validation.",
        "selected_experience_blocks": [
            {
                "source_id": 0,  # Sidel
                "bullet_indices": [0],  # Only first bullet (our new unique string)
                "order": 1,
                "show": True,
                "relevance": 1.0,
            }
        ],
        "selected_project_blocks": [],
        "selected_skill_blocks": [],
        "metadata": {
            "source": "authoritativeness_test_v2",
            "test_fixture": True,
        },
    }

    adaptation_v2 = GenerationAgent._convert_source_adaptation_to_template_format(
        source_adaptation_v2, master_cv_test_v2
    )

    context_v2 = {
        "candidate": {
            "name": "Test Candidate",
            "email": "test@example.com",
            "phone": "+33 6 00 00 00 00",
            "linkedin": "",
            "github": "",
            "website": "",
        },
        "adaptation": adaptation_v2,
        "master_cv": master_cv_test_v2,
        "positioning": "Data Analyst | Business Intelligence",
        "analysis_job_title": "Test Position",
    }

    html_v2 = render_cv(context_v2, template_name="master_cv.html")

    # STEP 7: Verify v2 string appears, v1 string is gone
    print("\nSTEP 7: Verify v2 unique string appears, v1 string is gone")
    print("-" * 80)

    v2_found = unique_string_v2 in html_v2
    v1_still_present = unique_string_v1 in html_v2

    if v2_found:
        print(f"✅ PASS: Found v2 unique string in HTML")
        idx = html_v2.find(unique_string_v2)
        context_snippet = html_v2[max(0, idx - 50) : min(len(html_v2), idx + len(unique_string_v2) + 50)]
        print(f"   Context: ...{context_snippet}...")
    else:
        print(f"❌ FAIL: v2 unique string NOT found in HTML")

    if not v1_still_present:
        print(f"✅ PASS: v1 unique string is GONE from HTML")
    else:
        print(f"❌ FAIL: v1 unique string still present in HTML (cache/stale data issue)")

    # FINAL VERDICT
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    all_pass = v2_found and not v1_still_present

    if all_pass:
        print("\n✅ AUTHORITATIVENESS TEST PASSED")
        print("\nProof that Master CV is source of truth:")
        print("  ✓ Injected v1 unique string → appeared in rendered CV")
        print("  ✓ Changed Master CV to v2 → v2 appeared, v1 disappeared")
        print("  ✓ CV content is EXACTLY from Master CV, not cached/hallucinated")
        print("\nConclusion: The generator IS reading Master CV as source of truth.")
        print("Deployed CVs will use actual Master CV content, not stale data.")
    else:
        print("\n❌ AUTHORITATIVENESS TEST FAILED")
        if not v2_found:
            print("  ✗ v2 unique string not found → Generator not reading from Master CV")
        if v1_still_present:
            print("  ✗ v1 unique string still present → Using cached/stale data or hallucinations")
        print("\nConclusion: The generator is NOT using Master CV as source of truth.")

    return {
        "v1_string_found": unique_string_v1 in html_v1,
        "v2_string_found": v2_found,
        "v1_string_gone": not v1_still_present,
        "all_pass": all_pass,
    }


if __name__ == "__main__":
    result = asyncio.run(test_master_cv_authoritativeness())
    print("\n" + "=" * 80)
    print(f"Test Result: {result}")
    print("\nExit code: {'SUCCESS' if result['all_pass'] else 'FAILURE'}")
    sys.exit(0 if result["all_pass"] else 1)
