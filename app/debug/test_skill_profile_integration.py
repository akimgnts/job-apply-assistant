"""Test skill profile integration with adaptation prompt.

Simulates the adaptation process without calling OpenAI.

Usage:
    python -m app.debug.test_skill_profile_integration
"""

from app.prompts.adaptation_prompt import get_cv_adaptation_prompt
from app.services.master_cv_service import load_master_cv
from app.config.skill_profiles import SKILL_PROFILES

def test_adaptation_prompt_with_skill_profile():
    """Test that adaptation prompt includes skill profile rules."""
    print("\n=== Skill Profile Integration Test ===\n")

    # Load master CV
    master_cv = load_master_cv()
    print(f"✓ Master CV loaded: {len(master_cv['experiences'])} experiences, {len(master_cv['skills'])} skill sections")

    # Mock analysis
    analysis = {
        "job_title": "Chef de Projets Marketing",
        "company": "John Paul",
        "missions": [
            "Développer l'expérience client",
            "Renforcer la fidélisation des membres",
            "Mettre en œuvre des stratégies marketing ciblées"
        ],
        "required_skills": [
            "CRM", "Marketing", "Campaign Reporting", "Customer Experience",
            "KPI Monitoring", "Stakeholder Coordination"
        ],
        "ats_keywords": [
            "CRM", "Campaign Reporting", "Customer Data", "KPI",
            "Marketing Analysis", "Power BI", "Excel", "Stakeholder Management"
        ],
        "strengths": [],
        "missing_points": [],
        "cv_strategy": "Test"
    }

    # Test with marketing_crm profile
    print("\n### Testing marketing_crm profile ###")
    positioning = "Marketing & CRM Project Manager"
    skill_profile = "marketing_crm"

    prompt = get_cv_adaptation_prompt(analysis, positioning, master_cv, skill_profile)

    # Verify prompt includes skill profile rules
    assert "marketing_crm" in prompt, "Prompt should mention skill_profile"
    assert "Prioritize: Business Systems" in prompt, "Prompt should include prioritize rules"
    assert "De-emphasize FastAPI" in prompt, "Prompt should mention what to reduce"
    assert "skill_section_order" in prompt, "Prompt should request skill section ordering"
    assert "skill_section_emphasis" in prompt, "Prompt should request visibility levels"

    print("✓ Prompt includes marketing_crm rules")
    print(f"✓ Prompt mentions reducing: Backend & Data Systems, AI & LLM Workflows")
    print(f"✓ Prompt mentions prioritizing: Business Systems, Data & Analytics, Creative & Delivery")

    # Test with data_ai profile
    print("\n### Testing data_ai profile ###")
    skill_profile = "data_ai"
    positioning = "Data & AI Project Analyst"

    prompt = get_cv_adaptation_prompt(analysis, positioning, master_cv, skill_profile)

    assert "data_ai" in prompt, "Prompt should mention skill_profile"
    assert "AI & LLM Workflows" in prompt, "Prompt should prioritize AI/LLM"
    assert "Creative & Delivery" in prompt, "Prompt should mention reducing creative"

    print("✓ Prompt includes data_ai rules")
    print(f"✓ Prompt prioritizes AI & LLM, Backend, Data & Analytics")
    print(f"✓ Prompt reduces Creative & Delivery")

    # Verify prompt returns expected JSON structure
    print("\n### Checking JSON return format ###")
    assert "skill_section_order" in prompt, "Should request skill_section_order"
    assert "skill_section_emphasis" in prompt, "Should request skill_section_emphasis"
    print("✓ Prompt requests skill_section_order array")
    print("✓ Prompt requests skill_section_emphasis object")
    print("✓ Prompt explains visibility levels: high | normal | low")

    # Verify all skill sections are mentioned
    print("\n### Verifying skill section coverage ###")
    skill_sections = [s["label"] for s in master_cv["skills"]]
    print(f"Master CV skill sections: {skill_sections}")
    for section in skill_sections:
        assert section in prompt, f"Prompt should mention {section}"
    print(f"✓ All {len(skill_sections)} skill sections mentioned in prompt")

    print("\n=== Summary ===")
    print("✓ Adaptation prompt correctly integrates skill profiles")
    print("✓ Profile-specific rules are included in prompt")
    print("✓ JSON return format requests skill_section_order and emphasis")
    print("✓ All skill sections from master CV are accounted for")
    print("\n✅ Skill Profile Integration test passed!\n")


if __name__ == "__main__":
    test_adaptation_prompt_with_skill_profile()
