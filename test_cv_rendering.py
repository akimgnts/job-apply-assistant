#!/usr/bin/env python3
"""Test CV rendering with edge cases.

Verifies that missing values don't render as None/null/empty blocks.
"""
import asyncio
from app.database.db import SessionLocal
from app.services.master_cv_service import load_master_cv
from app.agents.generation_agent import GenerationAgent
from app.services.document_service import render_cv

def test_rendering_with_empty_summary():
    """Test CV renders correctly when adaptation.summary is empty."""
    master_cv = load_master_cv()
    positioning = "Consultant Analytics & IA"

    adaptation = {
        "title": "",  # Empty - should fallback
        "summary": "",  # Empty - should use default
        "experience_order": [0, 1, 2],
        "experience_bullets": {
            "0": master_cv["experiences"][0].get("bullets", []),
            "1": master_cv["experiences"][1].get("bullets", []),
            "2": master_cv["experiences"][2].get("bullets", []),
        },
        "project_order": [0, 1, 2],
        "project_bullets": {
            "0": master_cv["projects"][0].get("bullets", []),
            "1": master_cv["projects"][1].get("bullets", []),
            "2": master_cv["projects"][2].get("bullets", []),
        },
        "ats_keywords": [],
    }

    # Apply defaults
    adaptation = GenerationAgent._ensure_adaptation_defaults(adaptation)

    candidate = {
        "name": "Akim Guentas",
        "email": "",
        "phone": "",
        "linkedin": "linkedin.com/in/akimguentas",
        "github": "github.com/akimgnts",
        "website": "madebyakim.com",
    }

    context = {
        "candidate": candidate,
        "adaptation": adaptation,
        "master_cv": master_cv,
        "positioning": positioning,
        "analysis_job_title": "Data Analyst BI",
    }

    html = render_cv(context, template_name="master_cv.html")

    # Validate
    validation = GenerationAgent._validate_rendered_html(html)

    print("=" * 80)
    print("TEST: CV Rendering with Empty Summary")
    print("=" * 80)
    print(f"\nValidation: {'✅ PASS' if validation['is_valid'] else '❌ FAIL'}")
    if validation["issues"]:
        print(f"Issues: {validation['issues']}")
    else:
        print("No issues found")

    # Check specific content
    print("\n--- Content Checks ---")
    checks = {
        "Title rendered": "Consultant Analytics & IA" in html,
        "Summary present": "Business-oriented" in html,
        "No 'None' text": "None" not in html,
        "Contact line built": "linkedin.com/in/akimguentas · github.com/akimgnts · madebyakim.com" in html,
        "No duplicate separators": " ·  · " not in html,
        "No empty subtitle": '<div class="top-subtitle"></div>' not in html,
        "Experience section": "Experience" in html,
        "Projects section": "Projects" in html,
    }

    for check_name, result in checks.items():
        print(f"  {check_name}: {'✅' if result else '❌'}")

    # Save HTML for inspection
    with open("test_cv_output.html", "w") as f:
        f.write(html)
    print(f"\nFull HTML saved to: test_cv_output.html")

    return validation["is_valid"]

if __name__ == "__main__":
    success = test_rendering_with_empty_summary()
    exit(0 if success else 1)
