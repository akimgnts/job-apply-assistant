"""Tests for title validation logic."""

import pytest
from app.agents.title_validator import TitleValidator, FALLBACK_TITLE


class TestTitleValidator:
    """Test suite for TitleValidator.validate_title()"""

    def test_safe_generic_title(self):
        """Generic data analyst titles should pass."""
        title = "Data Analyst"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_safe_compound_title_with_pipe(self):
        """Compound titles with safe descriptors should pass."""
        title = "Data Analyst | Business Intelligence"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_safe_compound_title_industrial(self):
        """Data analyst with industrial descriptor should pass."""
        title = "Data Analyst | Industrial Data & Automation"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_safe_business_and_data_analyst(self):
        """Business & Data Analyst should pass."""
        title = "Business & Data Analyst"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_safe_data_and_ai_analyst(self):
        """Data & AI Analyst should pass."""
        title = "Data & AI Analyst"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_unsafe_supply_chain_specialist(self):
        """Supply Chain Specialist should fail (unsupported domain)."""
        title = "Data Analyst — Supply Chain Optimization Specialist"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_senior_data_engineer(self):
        """Senior Data Engineer should fail (unsupported seniority + role)."""
        title = "Senior Data Engineer"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_lead_data_analyst(self):
        """Lead Data Analyst should fail (unsupported seniority)."""
        title = "Lead Data Analyst"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_aps_specialist(self):
        """APS Specialist should fail (unsupported domain)."""
        title = "APS Specialist"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_supply_chain_engineer(self):
        """Supply Chain Engineer should fail (unsupported domain)."""
        title = "Supply Chain Engineer"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_data_architect(self):
        """Data Architect should fail (unsupported role)."""
        title = "Data Architect"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_principal_data_analyst(self):
        """Principal Data Analyst should fail (unsupported seniority)."""
        title = "Principal Data Analyst"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_title_too_long(self):
        """Titles >80 characters should fail."""
        title = "Data Analyst Senior Lead Expert Architect Specialist Engineer Super Professional Very Advanced"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_director_role(self):
        """Director roles should fail."""
        title = "Director of Data Analytics"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_manager_role(self):
        """Manager roles should fail."""
        title = "Data Analytics Manager"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_safe_with_marketing_descriptor(self):
        """Data Analyst with marketing should pass (supported in Master CV)."""
        title = "Data Analyst | Marketing & Analytics"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_safe_with_operations_descriptor(self):
        """Data Analyst with operations should pass."""
        title = "Data Analyst | Operations & Analytics"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_empty_title(self):
        """Empty title should fail gracefully."""
        title = ""
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_none_title(self):
        """None title should fail gracefully."""
        is_valid, rewritten = TitleValidator.validate_title(None)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_case_insensitive_validation(self):
        """Validation should be case-insensitive."""
        title = "SENIOR DATA ANALYST"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False  # "SENIOR" is unsafe
        assert rewritten == FALLBACK_TITLE

    def test_positioning_mapping(self):
        """Test positioning-to-safe-title mapping."""
        # When positioning is provided, should use mapping
        positioning = "Data Analyst BI"
        title = "Invalid Title"
        is_valid, rewritten = TitleValidator.validate_title(title, positioning)
        assert is_valid is False
        # Should rewrite using positioning mapping
        assert rewritten in [FALLBACK_TITLE, "Data Analyst | Business Intelligence"]

    def test_safe_analyst_with_dashes(self):
        """Titles with dashes as separators should work."""
        title = "Data Analyst – Business Intelligence"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_safe_analyst_with_emdash(self):
        """Titles with em-dashes as separators should work."""
        title = "Data Analyst — Business Intelligence"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title

    def test_unsafe_ml_engineer(self):
        """Machine Learning Engineer should fail."""
        title = "Machine Learning Engineer"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_backend_engineer(self):
        """Backend Engineer should fail."""
        title = "Backend Engineer"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_devops_engineer(self):
        """DevOps Engineer should fail."""
        title = "DevOps Engineer"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_safe_junior_data_analyst(self):
        """Junior is OK if explicitly stated (honest about level)."""
        title = "Junior Data Analyst"
        is_valid, rewritten = TitleValidator.validate_title(title)
        # Junior is in SAFE_TITLE_TOKENS
        assert is_valid is True
        assert rewritten == title

    def test_unsafe_data_specialist(self):
        """Data Specialist is too vague."""
        title = "Data Specialist"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_unsafe_data_consultant(self):
        """Data Consultant role should fail."""
        title = "Data Consultant"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is False
        assert rewritten == FALLBACK_TITLE

    def test_safe_data_quality_governance(self):
        """Data Analyst with quality focus should pass."""
        title = "Data Analyst | Data Quality & Governance"
        is_valid, rewritten = TitleValidator.validate_title(title)
        assert is_valid is True
        assert rewritten == title
