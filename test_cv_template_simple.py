#!/usr/bin/env python3
"""Simple CV template rendering test (no OpenAI/database required).

Tests template robustness with edge cases.
"""
from jinja2 import Template

def test_cv_template_robustness():
    """Test that CV template safely renders with missing/empty values."""

    # Minimal template to test key fixes
    template_str = """
<div class="top-subtitle">
{{ adaptation.title or positioning or analysis_job_title or "Data & AI Analyst" }}
</div>

<div class="contact-line">
{% set contact_items = [] %}
{% if contact.location %}{% set _ = contact_items.append(contact.location) %}{% endif %}
{% if contact.email %}{% set _ = contact_items.append(contact.email) %}{% endif %}
{% if contact.phone %}{% set _ = contact_items.append(contact.phone) %}{% endif %}
{% if contact.linkedin %}{% set _ = contact_items.append(contact.linkedin) %}{% endif %}
{% if contact.github %}{% set _ = contact_items.append(contact.github) %}{% endif %}
{{ contact_items|join(" · ") }}
</div>

{% if adaptation.summary and adaptation.summary.strip() %}
<div class="intro">
{{ adaptation.summary }}
</div>
{% endif %}
"""

    template = Template(template_str)

    test_cases = [
        {
            "name": "Empty title, phone, email",
            "context": {
                "adaptation": {
                    "title": "",
                    "summary": "Professional summary here",
                },
                "positioning": "Marketing Manager",
                "analysis_job_title": "Senior Analyst",
                "contact": {
                    "location": "Paris",
                    "email": "",
                    "phone": "",
                    "linkedin": "linkedin.com/in/user",
                    "github": "github.com/user",
                },
            },
            "should_contain": [
                "Marketing Manager",
                "Professional summary here",
                "Paris · linkedin.com/in/user · github.com/user",
            ],
            "should_not_contain": [
                "None",
                " ·  · ",  # duplicate separator
                "<div class=\"intro\"></div>",  # empty intro
            ],
        },
        {
            "name": "All fields empty - use all defaults",
            "context": {
                "adaptation": {
                    "title": None,
                    "summary": "",
                },
                "positioning": "",
                "analysis_job_title": "",
                "contact": {
                    "location": "",
                    "email": "",
                    "phone": "",
                    "linkedin": "",
                    "github": "",
                },
            },
            "should_contain": [
                "Data & AI Analyst",  # fallback
            ],
            "should_not_contain": [
                "None",
                " ·  · ",
                "<div class=\"intro\"></div>",
            ],
        },
        {
            "name": "Full data - all present",
            "context": {
                "adaptation": {
                    "title": "Data Scientist",
                    "summary": "Experienced data professional",
                },
                "positioning": "Marketing Manager",
                "analysis_job_title": "Senior Analyst",
                "contact": {
                    "location": "Paris",
                    "email": "user@example.com",
                    "phone": "+33 6 00 00 00 00",
                    "linkedin": "linkedin.com/in/user",
                    "github": "github.com/user",
                },
            },
            "should_contain": [
                "Data Scientist",
                "Experienced data professional",
                "Paris · user@example.com · +33 6 00 00 00 00 · linkedin.com/in/user · github.com/user",
            ],
            "should_not_contain": [
                "None",
                " ·  · ",
            ],
        },
    ]

    print("=" * 80)
    print("CV TEMPLATE ROBUSTNESS TEST")
    print("=" * 80)

    all_passed = True
    for test_case in test_cases:
        print(f"\n[{test_case['name']}]")

        rendered = template.render(test_case["context"])

        passed = True
        for should_text in test_case.get("should_contain", []):
            if should_text in rendered:
                print(f"  ✅ Contains: {should_text[:60]}")
            else:
                print(f"  ❌ Missing: {should_text[:60]}")
                passed = False

        for should_not_text in test_case.get("should_not_contain", []):
            if should_not_text not in rendered:
                print(f"  ✅ No: {should_not_text[:60]}")
            else:
                print(f"  ❌ Found: {should_not_text[:60]}")
                passed = False

        if passed:
            print("  Result: ✅ PASS")
        else:
            print("  Result: ❌ FAIL")
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)

    return all_passed

if __name__ == "__main__":
    success = test_cv_template_robustness()
    exit(0 if success else 1)
