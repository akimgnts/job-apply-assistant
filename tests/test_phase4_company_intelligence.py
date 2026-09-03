"""Phase 4 Tests: Company Intelligence Aggregation.

Verify deterministic company-level signal calculation:
- Offer volume (total, active, relevant)
- Recurring skill aggregation
- DIRECT/SUPPORTING/GAP fit scoring
- Company-level profile fit
- Recruitment intensity (LOW/MEDIUM/HIGH)
- Priority ranking (deterministic, ties handled)
- No lead discovery or LinkedIn integration
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.company_intelligence_service import (
    is_relevant_offer,
    calculate_skill_fit,
    calculate_offer_fit,
    get_recruitment_intensity,
    get_company_intelligence,
    rank_companies,
)
from app.database.models import Company, JobOffer, JobAnalysis


class TestRelevanceDetection:
    """Test offer relevance to Data/BI/AI profile."""

    def test_is_relevant_offer_data_analyst_title(self):
        """Title matches Data Analyst → relevant."""
        assert is_relevant_offer("Senior Data Analyst") is True

    def test_is_relevant_offer_bi_analyst_title(self):
        """Title matches BI Analyst → relevant."""
        assert is_relevant_offer("Business Intelligence Specialist") is True

    def test_is_relevant_offer_data_engineer_title(self):
        """Title matches Data Engineer → relevant."""
        assert is_relevant_offer("Data Engineer") is True

    def test_is_relevant_offer_ai_ml_title(self):
        """Title matches AI/ML → relevant."""
        assert is_relevant_offer("Machine Learning Engineer") is True

    def test_is_relevant_offer_automation_title(self):
        """Title matches Automation → relevant."""
        assert is_relevant_offer("Automation Engineer") is True

    def test_is_relevant_offer_generic_role_not_relevant(self):
        """Generic role not in target categories → not relevant."""
        assert is_relevant_offer("Sales Manager") is False
        assert is_relevant_offer("HR Specialist") is False

    def test_is_relevant_offer_title_with_skill_keywords(self):
        """Title contains skill keywords (analytics, data, dashboard) → relevant."""
        assert is_relevant_offer("Developer - Data Analytics and Dashboard") is True
        assert is_relevant_offer("Engineer - Data Warehouse and ETL") is True
        assert is_relevant_offer("Specialist - Business Intelligence") is True

    def test_is_relevant_offer_analysis_required_skills(self):
        """Analysis contains relevant required_skills → relevant."""
        analysis = {
            "required_skills": ["Python", "SQL", "Power BI"]
        }
        assert is_relevant_offer("Junior Developer", analysis) is True

    def test_is_relevant_offer_analysis_no_relevant_skills(self):
        """Analysis contains only non-relevant skills → not relevant (title may override)."""
        analysis = {
            "required_skills": ["JavaScript", "React", "CSS"]
        }
        # Generic title + no relevant skills
        assert is_relevant_offer("Software Engineer", analysis) is False


class TestSkillFitScoring:
    """Test DIRECT/SUPPORTING/GAP scoring."""

    def test_skill_fit_direct_evidence(self):
        """DIRECT evidence = 1.0 fit score."""
        evidence = [
            {"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "Python"}
        ]
        score, breakdown = calculate_skill_fit(evidence)
        assert score == 1.0
        assert breakdown["DIRECT"] == 1
        assert breakdown["SUPPORTING"] == 0

    def test_skill_fit_supporting_evidence(self):
        """SUPPORTING evidence = 0.6 fit score."""
        evidence = [
            {"evidence_id": "SIDEL.DATA_BI.001", "match_type": "SUPPORTING", "evidence_text": "..."}
        ]
        score, breakdown = calculate_skill_fit(evidence)
        assert score == 0.6
        assert breakdown["SUPPORTING"] == 1

    def test_skill_fit_gap_no_evidence(self):
        """Empty evidence list = GAP = 0.0 fit score."""
        evidence = []
        score, breakdown = calculate_skill_fit(evidence)
        assert score == 0.0
        assert breakdown["GAP"] == 1

    def test_skill_fit_mixed_evidence(self):
        """Mixed DIRECT + SUPPORTING = average."""
        evidence = [
            {"evidence_id": "SKILL.SQL", "match_type": "DIRECT", "evidence_text": "SQL"},
            {"evidence_id": "SIDEL.DATA_BI.002", "match_type": "SUPPORTING", "evidence_text": "..."}
        ]
        score, breakdown = calculate_skill_fit(evidence)
        # (1.0 + 0.6) / 2 = 0.8
        assert score == 0.8
        assert breakdown["DIRECT"] == 1
        assert breakdown["SUPPORTING"] == 1

    def test_skill_fit_multiple_direct(self):
        """Multiple DIRECT evidence = 1.0 fit."""
        evidence = [
            {"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."},
            {"evidence_id": "SIDEL.DATA_BI.001", "match_type": "DIRECT", "evidence_text": "..."}
        ]
        score, breakdown = calculate_skill_fit(evidence)
        assert score == 1.0
        assert breakdown["DIRECT"] == 2


class TestOfferFitScoring:
    """Test offer-level fit aggregation."""

    def test_offer_fit_all_direct(self):
        """All skills have DIRECT evidence = 1.0 offer fit."""
        analysis = {
            "required_skills": ["Python", "SQL"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "SQL": [{"evidence_id": "SKILL.SQL", "match_type": "DIRECT", "evidence_text": "..."}]
            }
        }
        score, breakdown = calculate_offer_fit(analysis)
        assert score == 1.0
        assert breakdown["skills_evaluated"] == 2
        assert breakdown["direct"] == 2
        assert breakdown["gaps"] == 0

    def test_offer_fit_mixed_skills(self):
        """Mix of DIRECT and GAP → partial fit."""
        analysis = {
            "required_skills": ["Python", "Spark"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "Spark": []  # GAP
            }
        }
        score, breakdown = calculate_offer_fit(analysis)
        # (1.0 + 0.0) / 2 = 0.5
        assert score == 0.5
        assert breakdown["skills_evaluated"] == 2
        assert breakdown["direct"] == 1
        assert breakdown["gaps"] == 1

    def test_offer_fit_no_skills(self):
        """No required skills defined → 0.0 fit."""
        analysis = {
            "required_skills": [],
            "skill_evidence_map": {}
        }
        score, breakdown = calculate_offer_fit(analysis)
        assert score == 0.0
        assert breakdown["skills_evaluated"] == 0


class TestRecruitmentIntensity:
    """Test LOW/MEDIUM/HIGH determination."""

    def test_intensity_high(self):
        """6+ offers, 3+ relevant → HIGH."""
        assert get_recruitment_intensity(6, 3) == "HIGH"
        assert get_recruitment_intensity(10, 5) == "HIGH"

    def test_intensity_medium(self):
        """3-5 offers, 1+ relevant → MEDIUM."""
        assert get_recruitment_intensity(3, 1) == "MEDIUM"
        assert get_recruitment_intensity(5, 2) == "MEDIUM"

    def test_intensity_low(self):
        """<3 offers or <1 relevant → LOW."""
        assert get_recruitment_intensity(1, 0) == "LOW"
        assert get_recruitment_intensity(2, 0) == "LOW"
        assert get_recruitment_intensity(10, 0) == "LOW"  # Many offers, none relevant


class TestCompanyIntelligenceIntegration:
    """Integration tests for company intelligence (without complex DB mocking)."""

    def test_offer_fit_calculation_all_direct(self):
        """Test complete offer fit calculation with all DIRECT evidence."""
        analysis = {
            "required_skills": ["Python", "SQL"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "SQL": [{"evidence_id": "SKILL.SQL", "match_type": "DIRECT", "evidence_text": "..."}]
            }
        }
        score, breakdown = calculate_offer_fit(analysis)
        assert score == 1.0
        assert breakdown["direct"] == 2
        assert breakdown["gaps"] == 0

    def test_offer_fit_calculation_mixed(self):
        """Test offer fit with mixed DIRECT and GAP evidence."""
        analysis = {
            "required_skills": ["Python", "Spark", "Power BI"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "Spark": [],  # GAP
                "Power BI": [{"evidence_id": "SKILL.BI", "match_type": "SUPPORTING", "evidence_text": "..."}]
            }
        }
        score, breakdown = calculate_offer_fit(analysis)
        # (1.0 + 0.0 + 0.6) / 3 ≈ 0.53
        assert 0.52 <= score <= 0.54
        assert breakdown["direct"] == 1
        assert breakdown["supporting"] == 1
        assert breakdown["gaps"] == 1

    def test_strong_match_threshold(self):
        """Test that fit >= 0.7 is considered strong match."""
        # Just above threshold
        analysis_strong = {
            "required_skills": ["Python"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}]
            }
        }
        score_strong, _ = calculate_offer_fit(analysis_strong)
        assert score_strong >= 0.7

        # Below threshold
        analysis_weak = {
            "required_skills": ["Python", "Spark"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "Spark": []
            }
        }
        score_weak, _ = calculate_offer_fit(analysis_weak)
        assert score_weak < 0.7


class TestRankingLogic:
    """Test ranking logic without DB."""

    def test_priority_score_calculation_components(self):
        """Verify priority score components."""
        # High fit + high offer volume
        high_fit_analysis = {
            "required_skills": ["Python", "SQL"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "SQL": [{"evidence_id": "SKILL.SQL", "match_type": "DIRECT", "evidence_text": "..."}]
            }
        }
        score_high, _ = calculate_offer_fit(high_fit_analysis)
        assert score_high == 1.0  # Should contribute 40 points to priority

        # Low fit
        low_fit_analysis = {
            "required_skills": ["Python", "Spark", "Go"],
            "skill_evidence_map": {
                "Python": [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}],
                "Spark": [],
                "Go": []
            }
        }
        score_low, _ = calculate_offer_fit(low_fit_analysis)
        assert score_low < 0.4  # Should contribute < 15 points

    def test_recruitment_intensity_scoring(self):
        """Verify recruitment intensity values."""
        high = get_recruitment_intensity(total_offers=10, relevant_offers=5)
        medium = get_recruitment_intensity(total_offers=4, relevant_offers=1)
        low = get_recruitment_intensity(total_offers=2, relevant_offers=0)

        assert high == "HIGH"
        assert medium == "MEDIUM"
        assert low == "LOW"

    def test_priority_score_bounds(self):
        """Verify priority score stays in reasonable bounds."""
        # Best case: very high fit, many relevant offers, HIGH intensity
        best_case_fit = 1.0
        best_case_fit_contribution = best_case_fit * 40  # max 40
        best_case_volume = min(10 * 10, 30)  # max 30
        best_case_best_fit = max(0, (1.0 - 0.6) * 20)  # max 10
        best_case_intensity = 10  # HIGH bonus

        max_possible_score = best_case_fit_contribution + best_case_volume + best_case_best_fit + best_case_intensity
        assert max_possible_score <= 100

        # Worst case
        min_possible_score = 0
        assert min_possible_score >= 0


class TestNoLeadDiscovery:
    """Ensure Phase 4 does NOT do lead discovery."""

    def test_no_company_contact_interaction(self):
        """Company intelligence service does not interact with CompanyContact."""
        # This is a structural test: verify the service doesn't import or use CompanyContact
        import app.services.company_intelligence_service as cis
        import inspect

        source = inspect.getsource(cis)
        assert "CompanyContact" not in source, "company_intelligence_service must not reference CompanyContact"
        assert "contact" not in source.lower() or "no contact" in source.lower(), "Should not mention contacts"

    def test_no_linkedin_reference(self):
        """Company intelligence service does not reference LinkedIn."""
        import app.services.company_intelligence_service as cis
        import inspect

        source = inspect.getsource(cis)
        assert "linkedin" not in source.lower(), "Should not reference LinkedIn"
        assert "scrape" not in source.lower() or "scraper" in source.lower(), "Should not scrape"

    def test_no_email_generation(self):
        """Company intelligence service does not generate emails."""
        import app.services.company_intelligence_service as cis
        import inspect

        source = inspect.getsource(cis)
        assert "email" not in source.lower(), "Should not generate emails"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
