"""Test skill profile selection and emphasis rules.

Usage:
    python -m app.debug.test_skill_profiles
"""

from app.config.skill_profiles import SKILL_PROFILES, get_skill_profile, validate_skill_profile

def test_skill_profiles():
    """Verify skill profile structure and rules."""
    print("\n=== Skill Profile V1.1 Test ===\n")

    # Test profile existence
    profiles = list(SKILL_PROFILES.keys())
    print(f"✓ Available profiles: {profiles}")
    assert len(profiles) == 7, "Should have 7 profiles"

    # Test marketing_crm profile
    print("\n### marketing_crm profile ###")
    marketing = get_skill_profile("marketing_crm")
    print(f"Description: {marketing['description']}")
    print(f"Prioritize: {marketing['prioritize']}")
    print(f"Reduce: {marketing['reduce']}")
    print(f"Skill section order: {marketing['skill_section_order']}")
    assert "Business Systems" in marketing["prioritize"], "Business Systems should be prioritized"
    assert "Backend & Data Systems" in marketing["reduce"], "Backend should be reduced"
    print("✓ marketing_crm rules correct")

    # Test data_ai profile
    print("\n### data_ai profile ###")
    data_ai = get_skill_profile("data_ai")
    print(f"Description: {data_ai['description']}")
    print(f"Prioritize: {data_ai['prioritize'][:3]}")
    assert "AI & LLM Workflows" in data_ai["prioritize"], "AI/LLM should be prioritized"
    assert "Creative & Delivery" in data_ai["reduce"], "Creative should be reduced"
    print("✓ data_ai rules correct")

    # Test all profiles have required fields
    print("\n### Checking all profiles structure ###")
    required_fields = ["description", "prioritize", "reduce", "skill_section_order", "skill_section_emphasis"]
    for profile_key in profiles:
        profile = SKILL_PROFILES[profile_key]
        for field in required_fields:
            assert field in profile, f"{profile_key} missing {field}"
        # Verify skill_section_order has 6 sections
        assert len(profile["skill_section_order"]) == 6, f"{profile_key} order should have 6 sections"
        # Verify skill_section_emphasis has 6 sections
        assert len(profile["skill_section_emphasis"]) == 6, f"{profile_key} emphasis should have 6 sections"
    print(f"✓ All {len(profiles)} profiles have correct structure")

    # Test validation
    print("\n### Testing validation ###")
    assert validate_skill_profile("marketing_crm") == True
    assert validate_skill_profile("data_ai") == True
    assert validate_skill_profile("invalid_profile") == False
    print("✓ Validation works correctly")

    # Test fallback to general_business_data
    print("\n### Testing fallback ###")
    fallback = get_skill_profile("nonexistent")
    assert fallback == SKILL_PROFILES["general_business_data"]
    print("✓ Fallback to general_business_data works")

    # Summary
    print("\n=== Summary ===")
    print(f"✓ {len(profiles)} skill profiles defined")
    print(f"✓ All profiles have prioritize/reduce/order/emphasis")
    print(f"✓ Validation and fallback working")
    print("\n✅ Skill Profile V1.1 test passed!\n")


if __name__ == "__main__":
    test_skill_profiles()
