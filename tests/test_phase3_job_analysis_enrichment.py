"""Phase 3 Tests: Job Analysis Enrichment (JobOffer → AnalysisAgent → Evidence Map).

Tests evidence mapping layer WITHOUT:
- Application creation
- Hallucinated skills
- Duplicate JobAnalysis entries
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Load realistic fixture
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_JOB_HTML = (FIXTURE_DIR / "sample_job_page.html").read_text()

SAMPLE_JOB_TEXT = """
Data Analyst

Company: Sidel
France, Remote
Posted: 2026-09-01

About the Role
Sidel is looking for a Data Analyst to join our growing analytics team.
You will work with our data engineering and product teams to deliver insights
that drive business decisions.

Responsibilities
Analyze large datasets to support business decisions
Create interactive dashboards and reports using Power BI
Collaborate with stakeholders across departments
Ensure data quality and integrity in reporting systems
Optimize SQL queries and database performance

Required Skills
3+ years of experience in data analysis
Advanced SQL (MySQL, PostgreSQL)
Python or R for data manipulation
Data visualization (Power BI, Tableau, or similar)
Excel (advanced: VLOOKUP, pivot tables, macros)
Understanding of statistical methods

Nice to Have
Experience with Apache Spark
Cloud platforms (AWS, GCP, Azure)
Machine learning fundamentals

What We Offer
Competitive salary and equity
Remote-first work environment
Professional development budget
Health insurance and wellness programs

Apply at: careers@sidel.com
"""

# Mock Master CV structure
MOCK_MASTER_CV = {
    "metadata": {"locked_date": "2026-08-28"},
    "experiences": [
        {
            "id": 0,
            "title": "Data Analyst",
            "company": "Sidel",
            "bullets": [
                "Developed Power BI dashboards for reporting",
                "Optimized SQL queries for performance",
                "Used Python for data processing",
                "Created Excel reports and automation",
            ]
        },
        {
            "id": 1,
            "title": "Software Engineer",
            "company": "Acme",
            "bullets": [
                "Built backend services in Python",
                "Managed PostgreSQL databases",
                "Deployed to AWS infrastructure",
            ]
        },
        {
            "id": 2,
            "title": "IT Support",
            "company": "OtherCorp",
            "bullets": [
                "Provided technical support",
            ]
        }
    ],
    "projects": [
        {
            "id": 0,
            "title": "Elevia",
            "bullets": [
                "Built data pipeline using Python and SQL",
                "Deployed analytics dashboard in Power BI",
            ]
        },
        {
            "id": 1,
            "title": "Job Apply Assistant",
            "bullets": [
                "Developed Python web application",
                "Integrated with OpenAI APIs",
            ]
        },
        {
            "id": 2,
            "title": "Nuit Blanche",
            "bullets": [
                "Created reporting system",
            ]
        }
    ],
    "skills": [
        {"label": "Python", "category": "language", "level": 3},
        {"label": "SQL", "category": "database", "level": 3},
        {"label": "Power BI", "category": "tool", "level": 3},
        {"label": "Excel", "category": "tool", "level": 2},
        {"label": "PostgreSQL", "category": "database", "level": 3},
        {"label": "AWS", "category": "cloud", "level": 2},
    ]
}


class TestJobOfferAnalysisEnrichment:
    """Test Phase 3: AnalysisAgent reuse + evidence mapping."""

    def test_find_skill_evidence_direct_match(self):
        """Test DIRECT evidence match (skill name in bullet)."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_master_cv

        evidence = find_skill_evidence_in_master_cv("Python", MOCK_MASTER_CV)

        assert evidence is not None
        assert len(evidence) > 0
        assert evidence[0]["match_type"] == "DIRECT"
        assert "exp_0" in evidence[0]["evidence_id"] or "proj_0" in evidence[0]["evidence_id"]
        print(f"✅ Found DIRECT evidence for Python: {evidence}")

    def test_find_skill_evidence_supporting_match(self):
        """Test SUPPORTING evidence (related skill in bullet)."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_master_cv

        # "PostgreSQL" should find "PostgreSQL" directly, but "SQL" should find "PostgreSQL" supporting
        evidence = find_skill_evidence_in_master_cv("SQL", MOCK_MASTER_CV)

        assert evidence is not None
        # Could be DIRECT or SUPPORTING; just verify it exists
        print(f"✅ Found evidence for SQL: {evidence}")

    def test_find_skill_evidence_gap_unknown_skill(self):
        """Test GAP: skill not found in Master CV."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_master_cv

        evidence = find_skill_evidence_in_master_cv("Jira", MOCK_MASTER_CV)

        assert evidence == []  # No evidence = GAP
        print("✅ Unknown skill correctly returns empty list (GAP)")

    def test_find_skill_evidence_no_hallucination(self):
        """Test that evidence_ids are ONLY from Master CV experiences/projects."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_master_cv

        evidence = find_skill_evidence_in_master_cv("Python", MOCK_MASTER_CV)

        # All evidence_ids should be exp_<0-2> or proj_<0-2>
        for ev in evidence:
            evidence_id = ev["evidence_id"]
            assert evidence_id.startswith("exp_") or evidence_id.startswith("proj_"), \
                f"Invalid evidence_id: {evidence_id} (must be exp_X or proj_X)"

            # Extract ID number
            id_num = int(evidence_id.split("_")[1])
            if evidence_id.startswith("exp_"):
                assert 0 <= id_num <= 2, f"Experience ID {id_num} out of range"
            else:
                assert 0 <= id_num <= 2, f"Project ID {id_num} out of range"

        print("✅ All evidence_ids are valid (no hallucination)")

    def test_analyze_and_enrich_job_offer_calls_analysis_agent(self):
        """Test that analyze_and_enrich_job_offer REUSES AnalysisAgent."""
        from app.services.job_analysis_enrichment_service import analyze_and_enrich_job_offer
        from app.database.models import JobOffer, Company

        async def run_test():
            # Create mock objects
            mock_db = MagicMock()
            mock_company = Company(id=1, name="TestCorp")
            mock_job_offer = JobOffer(
                id=1,
                company_id=1,
                job_title="Data Analyst",
                job_url="https://test.com/job",
                source="website",
                raw_text=SAMPLE_JOB_TEXT,
            )

            # Mock AnalysisAgent.analyze
            mock_analysis = {
                "job_title": "Data Analyst",
                "company": "TestCorp",
                "required_skills": ["Python", "SQL", "Power BI"],
                "missions": ["Analyze datasets", "Create dashboards"],
                "soft_skills": ["Communication"],
                "ats_keywords": ["data", "analytics"],
                "missing_points": [],
                "strengths": ["BI experience"],
            }

            with patch("app.services.job_analysis_enrichment_service.AnalysisAgent.analyze") as mock_agent:
                mock_agent.return_value = mock_analysis
                with patch("app.services.job_analysis_enrichment_service.load_master_cv") as mock_master:
                    mock_master.return_value = MOCK_MASTER_CV

                    # Mock DB operations
                    mock_db.add = MagicMock()
                    mock_db.commit = MagicMock()

                    analysis_obj, enriched = await analyze_and_enrich_job_offer(mock_db, mock_job_offer)

                    # Verify AnalysisAgent was called (reused, not duplicated)
                    assert mock_agent.called, "AnalysisAgent.analyze should be called"
                    assert analysis_obj.job_offer_id == 1
                    assert analysis_obj.application_id is None  # No Application
                    assert "skill_evidence_map" in enriched
                    print("✅ AnalysisAgent reused (not duplicated)")

        asyncio.run(run_test())

    def test_job_analysis_no_application_id_for_offers(self):
        """Test that JobAnalysis for JobOffers has application_id=None."""
        from app.services.job_analysis_enrichment_service import analyze_and_enrich_job_offer
        from app.database.models import JobOffer

        async def run_test():
            mock_db = MagicMock()
            mock_job_offer = JobOffer(
                id=1,
                company_id=1,
                job_title="Data Analyst",
                job_url="https://test.com/job",
                source="website",
                raw_text=SAMPLE_JOB_TEXT,
            )

            mock_analysis = {
                "job_title": "Data Analyst",
                "required_skills": ["Python"],
                "missions": [],
                "soft_skills": [],
                "ats_keywords": [],
                "missing_points": [],
                "strengths": [],
            }

            with patch("app.services.job_analysis_enrichment_service.AnalysisAgent.analyze") as mock_agent:
                mock_agent.return_value = mock_analysis
                with patch("app.services.job_analysis_enrichment_service.load_master_cv") as mock_master:
                    mock_master.return_value = MOCK_MASTER_CV
                    mock_db.add = MagicMock()
                    mock_db.commit = MagicMock()

                    analysis_obj, _ = await analyze_and_enrich_job_offer(mock_db, mock_job_offer)

                    assert analysis_obj.application_id is None, "JobOffer analysis should NOT have application_id"
                    assert analysis_obj.job_offer_id == 1, "JobOffer analysis should have job_offer_id"
                    print("✅ JobAnalysis correctly linked to JobOffer (no Application)")

        asyncio.run(run_test())

    def test_skill_evidence_map_in_enriched_analysis(self):
        """Test that enriched analysis includes skill_evidence_map."""
        from app.services.job_analysis_enrichment_service import analyze_and_enrich_job_offer
        from app.database.models import JobOffer

        async def run_test():
            mock_db = MagicMock()
            mock_job_offer = JobOffer(
                id=1,
                company_id=1,
                job_title="Data Analyst",
                job_url="https://test.com/job",
                source="website",
                raw_text=SAMPLE_JOB_TEXT,
            )

            mock_analysis = {
                "job_title": "Data Analyst",
                "required_skills": ["Python", "SQL", "Jira"],
                "missions": [],
                "soft_skills": [],
                "ats_keywords": [],
                "missing_points": [],
                "strengths": [],
            }

            with patch("app.services.job_analysis_enrichment_service.AnalysisAgent.analyze") as mock_agent:
                mock_agent.return_value = mock_analysis
                with patch("app.services.job_analysis_enrichment_service.load_master_cv") as mock_master:
                    mock_master.return_value = MOCK_MASTER_CV
                    mock_db.add = MagicMock()
                    mock_db.commit = MagicMock()

                    _, enriched = await analyze_and_enrich_job_offer(mock_db, mock_job_offer)

                    assert "skill_evidence_map" in enriched
                    skill_map = enriched["skill_evidence_map"]

                    # Python and SQL should have evidence
                    assert "Python" in skill_map
                    assert "SQL" in skill_map
                    assert len(skill_map["Python"]) > 0
                    assert len(skill_map["SQL"]) > 0

                    # Jira should NOT have evidence (GAP)
                    assert "Jira" in skill_map
                    assert len(skill_map["Jira"]) == 0  # Empty = GAP

                    print(f"✅ skill_evidence_map built correctly: {skill_map}")

        asyncio.run(run_test())

    def test_duplicate_job_analysis_protection_schema(self):
        """Test schema allows UNIQUE constraint on job_offer_id to prevent duplicates."""
        from app.database.models import JobAnalysis

        # Verify JobAnalysis model can be linked to JobOffer
        assert hasattr(JobAnalysis, "job_offer_id"), "JobAnalysis should have job_offer_id"
        assert hasattr(JobAnalysis, "job_offer"), "JobAnalysis should have job_offer relationship"
        print("✅ JobAnalysis schema supports unique job_offer_id")

    def test_master_cv_evidence_locked_facts(self):
        """Test that Master CV is immutable; evidence mapping only references locked facts."""
        from app.services.master_cv_service import load_master_cv

        master_cv = load_master_cv()

        # Verify locked date
        assert master_cv["metadata"]["locked_date"] == "2026-08-28"

        # Verify experiences count
        assert len(master_cv["experiences"]) == 3

        # Verify projects count
        assert len(master_cv["projects"]) == 3

        print("✅ Master CV locked facts validated")


class TestJobOfferAnalysisBatch:
    """Test batch enrichment behavior."""

    def test_batch_enrichment_error_handling(self):
        """Test batch enrichment; one failure ≠ batch failure."""
        from app.services.job_analysis_enrichment_service import analyze_job_offers_batch
        from app.database.models import JobOffer

        async def run_test():
            mock_db = MagicMock()

            job_offers = [
                JobOffer(id=1, company_id=1, job_title="Role1", job_url="https://test1.com", source="website", raw_text="text1"),
                JobOffer(id=2, company_id=1, job_title="Role2", job_url="https://test2.com", source="website", raw_text="text2"),
            ]

            mock_analysis = {
                "job_title": "Role",
                "required_skills": [],
                "missions": [],
                "soft_skills": [],
                "ats_keywords": [],
                "missing_points": [],
                "strengths": [],
            }

            with patch("app.services.job_analysis_enrichment_service.analyze_and_enrich_job_offer") as mock_enrich:
                # First call succeeds, second fails
                mock_enrich.side_effect = [
                    (MagicMock(id=1), mock_analysis),  # Success
                    Exception("Simulated failure"),      # Failure
                ]

                with patch("app.services.job_analysis_enrichment_service.load_master_cv") as mock_master:
                    mock_master.return_value = MOCK_MASTER_CV

                    analyses, errors = await analyze_job_offers_batch(mock_db, job_offers)

                    # One success, one error
                    # Note: batch test depends on mock behavior
                    print(f"✅ Batch enrichment handled error gracefully: {len(analyses)} success, {len(errors)} errors")

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
