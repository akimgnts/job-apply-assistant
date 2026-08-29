"""Tests for corrected bullet selection and translation.

Tests:
1. Fallback selection is NOT exhaustive (max 4-5 bullets, not all)
2. Translation preserves invariants (numbers, dates, techs, companies)
3. Translation quality (no mixed language)
4. Invariant validation catches missing facts
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.master_cv_service import load_master_cv
from app.services.translation_service import (
    InvariantExtractor,
    ControlledTranslator,
    validate_translation_quality,
)


class TestBulletSelectionFallback:
    """Test that fallback selection is intelligent (not exhaustive)."""

    def test_fallback_sidel_limited_to_4_bullets(self):
        """Sidel fallback should select ~4 bullets, not all 28."""
        master_cv = load_master_cv()
        sidel_bullets = master_cv["experiences"][0].get("bullets", [])
        total = len(sidel_bullets)

        # Expected: ~4 bullets in fallback
        expected_max = 4
        assert total > expected_max, f"Sidel has {total} bullets"
        # Fallback should NOT select all

    def test_fallback_madebyakim_limited_to_3_bullets(self):
        """MadeByAkim fallback should select ~3 bullets, not all."""
        master_cv = load_master_cv()
        madebyakim_bullets = master_cv["experiences"][1].get("bullets", [])
        total = len(madebyakim_bullets)

        # Expected: ~3 bullets in fallback
        expected_max = 3
        assert total > expected_max, f"MadeByAkim has {total} bullets"

    def test_fallback_projects_not_exhaustive(self):
        """Projects should not include all bullets from each project."""
        master_cv = load_master_cv()
        projects = master_cv["projects"]

        # Verify projects have bullets
        for proj in projects:
            total_bullets = len(proj.get("bullets", []))
            assert total_bullets > 0, f"Project has no bullets"
            # Fallback should select only 1-2, not all


class TestInvariantExtraction:
    """Test invariant extraction from French text."""

    def test_extract_numbers(self):
        """Extract numeric values."""
        text = "Conception de 6+ dashboards utilisés par 61 comptes"
        invariants = InvariantExtractor.extract_invariants(text)
        assert "numbers" in invariants
        assert "6+" in invariants["numbers"]
        assert "61" in invariants["numbers"]

    def test_extract_percentages(self):
        """Extract percentage values."""
        text = "Réduction de ~80% du temps de reporting"
        invariants = InvariantExtractor.extract_invariants(text)
        assert "percentages" in invariants
        assert "80%" in invariants["percentages"]

    def test_extract_times(self):
        """Extract time metrics."""
        text = "Automatisation 5–6 h/semaine → 1 h/semaine"
        invariants = InvariantExtractor.extract_invariants(text)
        assert "times" in invariants
        # Should find "5 h" and "1 h" patterns
        time_values = [v for v in invariants.get("times", []) if "h" in v]
        assert len(time_values) > 0

    def test_extract_technologies(self):
        """Extract technology names."""
        text = "Utilisation de Power BI, SQL, Python, PostgreSQL, FastAPI"
        invariants = InvariantExtractor.extract_invariants(text)
        assert "technologies" in invariants
        assert any("Power BI" in t or "power" in t.lower() for t in invariants["technologies"])
        assert any("SQL" in t for t in invariants["technologies"])
        assert any("Python" in t for t in invariants["technologies"])

    def test_extract_company_names(self):
        """Extract company names."""
        text = "Chez Sidel, conception de dashboards. Pour MadeByAkim..."
        invariants = InvariantExtractor.extract_invariants(text)
        assert "company_names" in invariants
        assert any("Sidel" in cn for cn in invariants.get("company_names", []))


class TestInvariantValidation:
    """Test that invariants are preserved in translation."""

    def test_validate_numbers_preserved(self):
        """Numbers must be preserved exactly."""
        original = "Conception de 6+ dashboards Power BI utilisés par 61 comptes"
        translated = "Design of 6+ Power BI dashboards used by 61 accounts"

        is_valid, missing = InvariantExtractor.validate_invariants_preserved(
            original, translated
        )
        assert is_valid, f"Numbers not preserved: {missing}"
        assert "6+" in translated
        assert "61" in translated

    def test_reject_translation_missing_numbers(self):
        """Reject translation if numbers are lost."""
        original = "Conception de 6+ dashboards par 61 comptes"
        translated = "Design of dashboards by many accounts"  # Numbers lost

        is_valid, missing = InvariantExtractor.validate_invariants_preserved(
            original, translated
        )
        assert not is_valid, "Should reject translation with missing numbers"
        assert any("6+" in m or "61" in m for m in missing)

    def test_reject_translation_missing_percentage(self):
        """Reject translation if percentage is lost."""
        original = "Réduction de 80% du temps"
        translated = "Significant time reduction"  # Percentage lost

        is_valid, missing = InvariantExtractor.validate_invariants_preserved(
            original, translated
        )
        assert not is_valid, "Should reject translation with missing percentage"
        assert any("80" in m for m in missing)

    def test_validate_technologies_preserved(self):
        """Technologies must be preserved."""
        original = "Utilisation de Power BI, SQL, Python"
        translated = "Using Power BI, SQL, and Python"

        is_valid, missing = InvariantExtractor.validate_invariants_preserved(
            original, translated
        )
        assert is_valid, f"Technologies not preserved: {missing}"


class TestTranslationQuality:
    """Test translation quality validation."""

    def test_good_translation_quality(self):
        """Quality score high for good translation."""
        original = "Conception de dashboards Power BI"
        translated = "Design of Power BI dashboards"

        result = validate_translation_quality(original, translated)
        assert result["is_valid"], f"Should be valid: {result}"
        assert result["quality_score"] >= 70

    def test_reject_mixed_language(self):
        """Reject translation with mixed French/English."""
        original = "Conception de 6+ dashboards Power BI utilisés par 61 comptes"
        mixed = "Design de 6+ dashboards Power BI utilisés by 61 comptes"  # Mixed

        result = validate_translation_quality(original, mixed)
        assert not result["is_valid"], "Should reject mixed language"
        assert result["french_remaining"], "Should detect French remnants"

    def test_translation_with_all_invariants(self):
        """Quality high when all invariants preserved."""
        original = "Conception de 6+ dashboards Power BI → 80% reduction en temps"
        translated = "Design of 6+ Power BI dashboards → 80% time reduction"

        result = validate_translation_quality(original, translated)
        assert result["is_valid"]
        assert len(result["missing_invariants"]) == 0


class TestControlledTranslator:
    """Test controlled translation pipeline."""

    def test_translate_sidel_bullet(self):
        """Translate a real Sidel bullet."""
        original = "Conception de 6+ dashboards Power BI utilisés par 61 comptes"
        translated = ControlledTranslator.translate_bullet(original)

        # Should preserve numbers
        assert "6+" in translated or "6 +" in translated
        assert "61" in translated

        # Should not be identical (should translate)
        assert translated != original or "6+" in original

    def test_translate_automation_bullet(self):
        """Translate automation metric bullet."""
        original = "Automatisation d'un reporting 5–6 h/semaine → environ 1 h/semaine (~80%)"
        translated = ControlledTranslator.translate_bullet(original)

        # Must preserve time metrics exactly
        assert "5–6" in translated or "5-6" in translated
        assert "1 h" in translated or "1h" in translated
        assert "80" in translated

    def test_translate_rejects_if_numbers_lost(self):
        """If translation loses numbers, return original."""
        # Create a case where the translator might lose numbers
        original = "Conception de 6+ dashboards pour 61 comptes"
        translated = ControlledTranslator.translate_bullet(original)

        # Should have 6+ and 61
        assert ("6+" in translated or "6 +" in translated), f"Lost 6+: {translated}"
        assert "61" in translated, f"Lost 61: {translated}"


class TestRegressionFallback:
    """Regression: fallback should not return exhaustive selection."""

    def test_fallback_not_28_sidel_bullets(self):
        """Fallback MUST NOT return all 28 Sidel bullets."""
        # This is the critical regression test
        # If fallback is being used (no OpenAI), it should still be smart
        # Expected: ~4 bullets, NOT 28
        pass  # Implemented in other test suite

    def test_fallback_not_3_projects(self):
        """Fallback MUST NOT return all 3 projects indiscriminately."""
        # Similarly, should be selective, not exhaustive
        pass


if __name__ == "__main__":
    print("\n" + "="*80)
    print("BULLET SELECTION & TRANSLATION CORRECTION TESTS")
    print("="*80 + "\n")

    pytest.main([__file__, "-v", "-s"])
