"""Test suite for QualityAgent V2 and claim validation.

Tests verify:
1. Metric fabrication detection
2. Technology invention detection
3. Level exaggeration detection
4. Status misrepresentation detection
5. Date fabrication detection
6. Accurate claim acceptance
"""

import pytest
from unittest.mock import MagicMock

from app.database.models import (
    ProfileBlock, CategoryEnum, TruthLevelEnum,
    ProficiencyLevelEnum, BlockStatusEnum
)
from app.services.claim_validator_service import (
    ClaimValidatorService, ValidationAction
)


class TestClaimValidatorService:
    """Test deterministic claim validation."""

    @pytest.fixture
    def sample_blocks(self):
        """Create sample atomic profile blocks for testing."""
        blocks = [
            # Sidel dashboards block
            ProfileBlock(
                id=1,
                category=CategoryEnum.achievement,
                title="Sidel — Dashboard Portfolio",
                content="Built dashboards",
                tags=[],
                truth_level=TruthLevelEnum.verified,
                status=BlockStatusEnum.deployed,
                company="Sidel",
                start_date="2023",
                end_date="2025",
                technologies=["Power BI", "Power Query", "Excel"],
                job_families=["Data Analyst", "BI Analyst"],
                metrics={"dashboards": "~10", "stakeholders": "~30–40"},
                forbidden_claims=[
                    "Do not change ~30–40 to an exact number",
                    "Do not claim automated beyond Power BI capabilities"
                ],
                source_ref="master_v3:sidel_dashboard_portfolio",
                priority=10,
            ),
            # Sidel automation block
            ProfileBlock(
                id=2,
                category=CategoryEnum.achievement,
                title="Sidel — Data Automation",
                content="Automated reporting",
                tags=[],
                truth_level=TruthLevelEnum.verified,
                status=BlockStatusEnum.deployed,
                company="Sidel",
                start_date="2023",
                end_date="2025",
                technologies=["Python", "SQL", "Power BI"],
                job_families=["Data Analyst", "Data Engineer"],
                metrics={
                    "before": "Half a day to several days of manual work",
                    "after": "Automated"
                },
                forbidden_claims=[
                    "Do not claim full automation without caveats",
                    "Do not invent reduction percentages"
                ],
                source_ref="master_v3:sidel_reporting_automation",
                priority=10,
            ),
            # Skill: Power BI (expert)
            ProfileBlock(
                id=3,
                category=CategoryEnum.skill,
                title="Power BI",
                content="Business intelligence tool",
                tags=["powerbi", "dataviz"],
                truth_level=TruthLevelEnum.verified,
                proficiency_level=ProficiencyLevelEnum.expert,
                technologies=["Power BI"],
                job_families=["BI Analyst", "Data Analyst"],
                source_ref="master_v3:skill_power_bi",
                priority=9,
            ),
            # Skill: Pandas (intermediate)
            ProfileBlock(
                id=4,
                category=CategoryEnum.skill,
                title="Pandas",
                content="Python data library",
                tags=["pandas", "python"],
                truth_level=TruthLevelEnum.verified,
                proficiency_level=ProficiencyLevelEnum.intermediate,
                technologies=["Pandas", "Python"],
                source_ref="master_v3:skill_pandas",
                priority=8,
            ),
            # Elevia project (exploratory status)
            ProfileBlock(
                id=5,
                category=CategoryEnum.project,
                title="Elevia — Platform",
                content="Matching platform",
                tags=["ai", "matching"],
                truth_level=TruthLevelEnum.declared,
                status=BlockStatusEnum.in_progress,
                company="Personal Project",
                start_date="2024",
                metrics={
                    "versions": "10+",
                    "profiles": "30",
                    "opportunities": "1000+"
                },
                forbidden_claims=[
                    "Do not claim 1000+ matches without data",
                    "Do not claim production scale without user base",
                ],
                source_ref="master_v3:elevia_platform",
                priority=10,
            ),
        ]
        return {b.source_ref: b for b in blocks}

    @pytest.fixture
    def validator(self, sample_blocks):
        """Create validator with sample blocks."""
        blocks = list(sample_blocks.values())
        return ClaimValidatorService(blocks)

    # =========================================================================
    # METRIC FABRICATION TESTS
    # =========================================================================

    def test_metric_exact_match_pass(self, validator):
        """Claimed metric matches frozen block metric → PASS."""
        result = validator.validate_metric_claim(
            "~30–40 stakeholders",
            "master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.PASS

    def test_metric_invented_number_remove(self, validator):
        """Claimed metric differs from frozen value → REMOVE."""
        result = validator.validate_metric_claim(
            "100+ stakeholders",  # Block says "~30–40"
            "master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.REMOVE
        assert "not found in block's frozen metrics" in result.reason

    def test_metric_without_block_remove(self, validator):
        """Metric claim with no block reference → REMOVE."""
        result = validator.validate_metric_claim(
            "50 dashboards",
            "master_v3:nonexistent_block"
        )
        assert result.action == ValidationAction.REMOVE

    # =========================================================================
    # TECHNOLOGY INVENTION TESTS
    # =========================================================================

    def test_technology_authorized_pass(self, validator):
        """Claimed technology in block's authorized list → PASS."""
        result = validator.validate_experience_claim(
            "Built dashboards using Power BI and Excel",
            "master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.PASS

    def test_technology_unauthorized_remove(self, validator):
        """Claimed technology NOT in block's authorized list → REMOVE."""
        result = validator.validate_experience_claim(
            "Built dashboards using Tableau and Looker",  # Not in Sidel's techs
            "master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.REMOVE
        assert "not authorized" in result.reason

    def test_technology_mixed_authorized_unauthorized_remove(self, validator):
        """Mix of authorized + unauthorized → REMOVE."""
        result = validator.validate_experience_claim(
            "Built dashboards using Power BI and Tableau",  # PBI yes, Tableau no
            "master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.REMOVE

    def test_snowflake_at_sidel_removed(self, validator):
        """Snowflake claim at Sidel → REMOVE (user correction)."""
        result = validator.validate_experience_claim(
            "Built Snowflake pipeline at Sidel",
            "master_v3:sidel_reporting_automation"
        )
        # Snowflake is NOT in sidel_reporting_automation.technologies
        assert result.action == ValidationAction.REMOVE

    # =========================================================================
    # PROFICIENCY EXAGGERATION TESTS
    # =========================================================================

    def test_skill_proficiency_at_block_level_pass(self, validator):
        """Claim proficiency level = block level → PASS."""
        result = validator.validate_skill_claim(
            "Power BI",
            claimed_proficiency_level=3,  # expert
            context_block_source_ref=None
        )
        assert result.action == ValidationAction.PASS

    def test_skill_proficiency_below_block_level_pass(self, validator):
        """Claim proficiency level < block level → PASS."""
        result = validator.validate_skill_claim(
            "Power BI",
            claimed_proficiency_level=2,  # intermediate (block is expert)
            context_block_source_ref=None
        )
        assert result.action == ValidationAction.PASS

    def test_skill_proficiency_above_block_level_remove(self, validator):
        """Claim proficiency level > block level → REMOVE."""
        result = validator.validate_skill_claim(
            "Pandas",
            claimed_proficiency_level=3,  # expert (block is intermediate)
            context_block_source_ref=None
        )
        assert result.action == ValidationAction.REMOVE
        assert "exceeds block's" in result.reason

    # =========================================================================
    # STATUS MISREPRESENTATION TESTS
    # =========================================================================

    def test_exploratory_status_cannot_claim_deployed(self, validator):
        """Status exploratory + claim 'deployed' → REMOVE."""
        result = validator.validate_experience_claim(
            "Deployed the Elevia platform in production",
            "master_v3:elevia_platform"
        )
        assert result.action == ValidationAction.REMOVE
        assert "exploratory" in result.reason

    def test_in_progress_status_can_claim_building(self, validator):
        """Status in_progress + claim 'building' → PASS."""
        result = validator.validate_experience_claim(
            "Currently building the matching engine",
            "master_v3:elevia_platform"
        )
        assert result.action == ValidationAction.PASS

    # =========================================================================
    # DATE FABRICATION TESTS
    # =========================================================================

    def test_date_within_block_range_pass(self, validator):
        """Claimed date within block's range → PASS."""
        result = validator.validate_date_claim(
            "2024",
            "2025",
            "master_v3:elevia_platform"
        )
        # Block says start_date="2024", no end_date specified
        assert result.action == ValidationAction.PASS

    def test_date_before_block_start_remove(self, validator):
        """Claimed start date before block's → REMOVE."""
        result = validator.validate_date_claim(
            "2022",  # Elevia started 2024
            None,
            "master_v3:elevia_platform"
        )
        assert result.action == ValidationAction.REMOVE

    # =========================================================================
    # FORBIDDEN CLAIMS TESTS
    # =========================================================================

    def test_forbidden_claim_violation_remove(self, validator):
        """Claim violates block's forbidden_claims → REMOVE."""
        result = validator.validate_experience_claim(
            "Designed over 100+ dashboards for 1000+ users",
            "master_v3:sidel_dashboard_portfolio"
        )
        # Block forbids: "Do not change ~30–40 to an exact number"
        assert result.action == ValidationAction.REMOVE
        assert "forbidden" in result.reason.lower()

    # =========================================================================
    # NO GENERIC SKILL JUSTIFICATION TESTS
    # =========================================================================

    def test_skill_without_context_block_pass(self, validator):
        """Skill exists globally → PASS (but cannot be used in specific experience without block)."""
        result = validator.validate_skill_claim(
            "Power BI",
            claimed_proficiency_level=None,
            context_block_source_ref=None
        )
        assert result.action == ValidationAction.PASS

    def test_skill_in_unauthorized_context_remove(self, validator):
        """Skill exists globally but NOT in specific experience block → REMOVE."""
        # Pandas is not in sidel_dashboard_portfolio
        result = validator.validate_skill_claim(
            "Pandas",
            claimed_proficiency_level=None,
            context_block_source_ref="master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.REMOVE
        assert "not authorized" in result.reason

    def test_skill_in_authorized_context_pass(self, validator):
        """Skill in block's authorized technologies → PASS."""
        # Python is in sidel_reporting_automation
        result = validator.validate_skill_claim(
            "Python",
            claimed_proficiency_level=None,
            context_block_source_ref="master_v3:sidel_reporting_automation"
        )
        assert result.action == ValidationAction.PASS

    # =========================================================================
    # ACCURATE CLAIM ACCEPTANCE TESTS
    # =========================================================================

    def test_accurate_experience_claim_pass(self, validator):
        """Factually accurate claim with authorized techs → PASS."""
        result = validator.validate_experience_claim(
            "Built and maintained around 10 dashboards using Power BI and Excel for 30–40 stakeholders",
            "master_v3:sidel_dashboard_portfolio"
        )
        assert result.action == ValidationAction.PASS

    def test_accurate_automation_claim_pass(self, validator):
        """Accurate claim about automation → PASS."""
        result = validator.validate_experience_claim(
            "Automated extraction and visualization tasks using Python and SQL",
            "master_v3:sidel_reporting_automation"
        )
        assert result.action == ValidationAction.PASS

    def test_accurate_metric_claim_pass(self, validator):
        """Accurate metric claim → PASS."""
        result = validator.validate_metric_claim(
            "Processed 1000+ job opportunities",
            "master_v3:elevia_platform"
        )
        assert result.action == ValidationAction.PASS
