"""End-to-end CV generation and validation testing.

Tests the complete pipeline:
1. Job offer analysis
2. Positioning selection
3. CV adaptation
4. Quality validation
5. HTML rendering

Collects metrics on retention rate, block matching, false negatives.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.database.models import ProfileBlock
from app.agents.analysis_agent import AnalysisAgent
from app.agents.positioning_agent import PositioningAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.quality_agent_v2 import QualityAgentV2


@dataclass
class CVMetrics:
    """Metrics for a single generated CV."""

    test_case: str
    job_title: str
    company: str
    positioning_chosen: str
    timestamp: str

    # Validation metrics
    pass_count: int = 0
    rewrite_count: int = 0
    remove_count: int = 0
    total_claims: int = 0
    removal_rate: float = 0.0  # remove_count / total_claims
    qc_recommendation: str = "UNKNOWN"  # ACCEPT / REVIEW / REJECT

    # Content metrics
    bullets_before: int = 0
    bullets_after: int = 0
    retention_rate: float = 0.0  # bullets_after / bullets_before
    avg_bullet_length: float = 0.0

    # Block matching metrics
    blocks_searched: int = 0
    top_matched_blocks: Dict[str, int] = None  # block_ref → match count

    # HTML quality
    html_validation_issues: int = 0
    ats_keywords_count: int = 0
    summary_present: bool = False

    # Manual review (filled in later)
    false_negatives: List[str] = None  # Claims that should have passed but were removed
    manual_notes: str = ""
    manual_status: str = ""  # PASS / REVIEW / FAIL


@dataclass
class CVTestResult:
    """Result of one E2E test case."""

    test_name: str
    job_family: str
    metrics: CVMetrics
    cv_html: Optional[str] = None
    adaptation_json: Optional[dict] = None
    quality_result_json: Optional[dict] = None
    error: Optional[str] = None


class CVE2ETestSuite:
    """End-to-end CV generation test suite."""

    @staticmethod
    async def run_test_case(
        db: Session,
        job_offer: str,
        test_name: str,
        job_family: str,
    ) -> CVTestResult:
        """Run one complete E2E test: analyze → position → adapt → validate → render.

        Args:
            db: Database session with profile blocks
            job_offer: Raw job offer text
            test_name: Test case name
            job_family: Job family for categorization

        Returns:
            CVTestResult with metrics and generated content
        """
        try:
            # 1. ANALYZE: Parse job offer
            analysis = await AnalysisAgent.analyze(db, job_offer)
            assert analysis, "Analysis failed"

            # 2. POSITION: Choose positioning angle
            positioning = await PositioningAgent.choose_angle(
                db, analysis, job_family
            )
            assert positioning, "Positioning failed"

            # 3. GENERATE: Produce CV
            cv_html = await GenerationAgent.generate_cv(
                db,
                application_id=0,  # Dummy ID for testing
                analysis=analysis,
                positioning=positioning,
                skill_profile="general_business_data",
            )
            assert cv_html, "CV generation failed"

            # 4. EXTRACT METRICS from generated CV
            # Note: In actual test, we'd need to intercept quality_result
            # For now, this is a placeholder
            metrics = CVMetrics(
                test_case=test_name,
                job_title=analysis.get("job_title", "Unknown"),
                company=analysis.get("company", "Unknown"),
                positioning_chosen=positioning,
                timestamp=datetime.utcnow().isoformat(),
                summary_present="summary" in cv_html.lower(),
            )

            return CVTestResult(
                test_name=test_name,
                job_family=job_family,
                metrics=metrics,
                cv_html=cv_html,
                error=None,
            )

        except Exception as e:
            return CVTestResult(
                test_name=test_name,
                job_family=job_family,
                metrics=CVMetrics(
                    test_case=test_name,
                    job_title="",
                    company="",
                    positioning_chosen="",
                    timestamp=datetime.utcnow().isoformat(),
                ),
                error=str(e),
            )

    @staticmethod
    def collect_metrics_from_adaptation(
        adaptation: dict,
        quality_result,
        master_cv: dict,
    ) -> CVMetrics:
        """Extract metrics from adaptation JSON and quality result.

        Args:
            adaptation: Adaptation JSON from CVAdaptationAgent
            quality_result: AdaptationValidationResult from QualityAgent v2
            master_cv: Master CV for reference

        Returns:
            CVMetrics dataclass with populated fields
        """
        # Count bullets
        bullets_before = sum(
            len(bullets) for bullets in adaptation.get("experience_bullets", {}).values()
        ) + sum(
            len(bullets) for bullets in adaptation.get("project_bullets", {}).values()
        )

        bullets_after = sum(
            len(bullets) for bullets in quality_result.cleaned_adaptation.get("experience_bullets", {}).values()
        ) + sum(
            len(bullets) for bullets in quality_result.cleaned_adaptation.get("project_bullets", {}).values()
        )

        retention_rate = (
            bullets_after / bullets_before if bullets_before > 0 else 0.0
        )

        # Extract top matched blocks from quality_result.details
        block_counts: Dict[str, int] = {}
        for detail in quality_result.details:
            block = detail.get("source_block")
            if block:
                block_counts[block] = block_counts.get(block, 0) + 1

        return CVMetrics(
            test_case="",
            job_title="",
            company="",
            positioning_chosen="",
            timestamp=datetime.utcnow().isoformat(),
            pass_count=quality_result.pass_count,
            rewrite_count=quality_result.rewrite_count,
            remove_count=quality_result.remove_count,
            total_claims=quality_result.total_count,
            removal_rate=quality_result.removal_rate,
            qc_recommendation=quality_result.recommendation,
            bullets_before=bullets_before,
            bullets_after=bullets_after,
            retention_rate=retention_rate,
            top_matched_blocks=block_counts,
        )

    @staticmethod
    def generate_report(results: List[CVTestResult]) -> Dict:
        """Generate summary report from test results.

        Args:
            results: List of CVTestResult from all test cases

        Returns:
            Report dict with aggregated metrics and diagnostics
        """
        passed = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]

        # Aggregate metrics
        all_metrics = [r.metrics for r in passed]
        avg_removal_rate = (
            sum(m.removal_rate for m in all_metrics) / len(all_metrics)
            if all_metrics
            else 0.0
        )
        avg_retention_rate = (
            sum(m.retention_rate for m in all_metrics) / len(all_metrics)
            if all_metrics
            else 0.0
        )

        accept_count = sum(
            1 for m in all_metrics if m.qc_recommendation == "ACCEPT"
        )
        review_count = sum(
            1 for m in all_metrics if m.qc_recommendation == "REVIEW"
        )
        reject_count = sum(
            1 for m in all_metrics if m.qc_recommendation == "REJECT"
        )

        # Diagnostics
        diagnostics = {}
        if avg_removal_rate > 0.30:
            diagnostics["HIGH_REMOVAL_RATE"] = (
                f"Avg removal {avg_removal_rate:.1%} > threshold 30%"
            )
        if avg_retention_rate < 0.80:
            diagnostics["LOW_RETENTION_RATE"] = (
                f"Avg retention {avg_retention_rate:.1%} < threshold 80%"
            )
        if reject_count > 1:
            diagnostics["MULTIPLE_REJECTS"] = f"{reject_count} test cases rejected"

        # Overall status
        if not failed and avg_removal_rate < 0.25 and avg_retention_rate >= 0.80:
            status = "PASS"
        elif not failed and avg_removal_rate < 0.40:
            status = "REVIEW"
        else:
            status = "FAIL"

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "test_count": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "aggregate_metrics": {
                "avg_removal_rate": avg_removal_rate,
                "avg_retention_rate": avg_retention_rate,
                "accept_count": accept_count,
                "review_count": review_count,
                "reject_count": reject_count,
            },
            "diagnostics": diagnostics,
            "overall_status": status,
            "individual_results": [
                {
                    "test_case": r.test_name,
                    "job_family": r.job_family,
                    "metrics": asdict(r.metrics),
                    "error": r.error,
                } for r in results
            ],
        }


# ============================================================================
# PLACEHOLDER TESTS (Ready for Phase 5 data)
# ============================================================================


class TestCVE2EPlaceholder:
    """Placeholder tests for Phase 5 E2E suite.

    Real tests will require:
    - Actual job offers (5 test cases)
    - Database with atomic blocks seeded
    - Full pipeline integration
    """

    def test_placeholder_awaiting_phase_5_data(self):
        """Placeholder: Phase 5 will provide real test data."""
        pytest.skip("Phase 5 E2E tests await real job offers and data")

    def test_metrics_dataclass_structure(self):
        """Verify CVMetrics structure is correct."""
        metrics = CVMetrics(
            test_case="Data Analyst",
            job_title="Senior Data Analyst",
            company="TechCorp",
            positioning_chosen="Data Analyst BI",
            timestamp="2025-01-01T00:00:00",
        )
        assert metrics.removal_rate == 0.0
        assert metrics.qc_recommendation == "UNKNOWN"
        assert isinstance(asdict(metrics), dict)

    def test_report_structure(self):
        """Verify report generation structure."""
        results = []
        report = CVE2ETestSuite.generate_report(results)
        assert "timestamp" in report
        assert "test_count" in report
        assert "overall_status" in report
        assert report["overall_status"] in ["PASS", "REVIEW", "FAIL"]
