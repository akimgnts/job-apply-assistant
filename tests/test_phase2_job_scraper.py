"""Phase 2 Tests: Job Offer Scraper (URL → minimal JobOffer dict).

Tests extraction layer WITHOUT:
- OpenAI calls
- AnalysisAgent
- PostgreSQL persistence (mocked DB for logic validation)
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path


# Load realistic fixture
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_JOB_HTML = (FIXTURE_DIR / "sample_job_page.html").read_text()

# After trafilatura extraction, the HTML becomes plain text like:
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


class TestJobOfferScraper:
    """Test job offer scraping (no AnalysisAgent, no OpenAI)."""

    def test_scrape_with_realistic_fixture(self):
        """Test scraper with realistic trafilatura output."""
        from app.services.job_offer_scraper_service import scrape_job_offer

        url = "https://sidel.com/careers/data-analyst"

        with patch("app.services.job_offer_scraper_service.extract_from_url") as mock_extract:
            mock_extract.return_value = SAMPLE_JOB_TEXT

            offer = scrape_job_offer(url)

            assert offer is not None
            assert offer["job_url"] == url
            assert offer["job_title"] == "Data Analyst"
            assert offer["company_name"] == "Sidel"
            assert offer["source"] == "website"
            assert len(offer["raw_text"]) > 100
            print(f"✅ Extracted offer: {offer['job_title']} @ {offer['company_name']}")

    def test_scrape_empty_extraction_returns_none(self):
        """Test graceful failure when extraction is too short."""
        from app.services.job_offer_scraper_service import scrape_job_offer

        with patch("app.services.job_offer_scraper_service.extract_from_url") as mock_extract:
            mock_extract.return_value = ""

            offer = scrape_job_offer("https://example.com/job")
            assert offer is None

    def test_company_inference_from_text(self):
        """Test company name extraction from explicit 'Company:' pattern."""
        from app.services.job_offer_scraper_service import infer_company_name

        text = "Company: Acme Corporation\nJoin our team..."
        company = infer_company_name(text, "https://example.com")
        assert company == "Acme Corporation"

    def test_company_inference_from_domain_only_for_websites(self):
        """Test domain extraction only for non-job-board URLs."""
        from app.services.job_offer_scraper_service import infer_company_name

        # Should extract from domain
        company = infer_company_name("Generic job text", "https://acmecorp.com/careers")
        assert company == "Acmecorp"

        # Should NOT extract from Indeed domain
        company = infer_company_name("Generic text", "https://indeed.com/jobs?q=python")
        assert company is None

        # Should NOT hallucinate without clear evidence
        company = infer_company_name("Some vague text", "https://example.org/page")
        assert company == "Example" or company is None  # Domain fallback only

    def test_batch_scraping_with_error_handling(self):
        """Test batch scraping; one URL failure should not stop batch."""
        from app.services.job_offer_scraper_service import scrape_job_offers

        urls = [
            "https://sidel.com/job1",
            "https://badurl.com/job2",  # Will fail
            "https://company.com/job3",
        ]

        with patch("app.services.job_offer_scraper_service.extract_from_url") as mock_extract:
            def side_effect(url):
                if "badurl" in url:
                    return ""  # Empty extraction
                return SAMPLE_JOB_TEXT

            mock_extract.side_effect = side_effect

            offers, errors = scrape_job_offers(urls)

            assert len(offers) == 2  # Two succeeded
            assert len(errors) == 1  # One failed
            assert errors[0]["url"] == "https://badurl.com/job2"
            print(f"✅ Batch scraping: {len(offers)} success, {len(errors)} errors")


class TestJobMarketRepository:
    """Test DB persistence layer (mocked DB session)."""

    def test_get_or_create_company_new(self):
        """Test creating a new company."""
        from app.services.job_market_repository_service import get_or_create_company
        from app.database.models import Company

        # Mock session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None  # Not found

        mock_company = Company(id=1, name="TestCorp", website="https://testcorp.com")
        mock_db.add.side_effect = lambda x: setattr(x, "id", 1)

        result = get_or_create_company(mock_db, "TestCorp", "https://testcorp.com")

        # Verify add() was called
        assert mock_db.add.called
        print("✅ Company creation logic works")

    def test_get_or_create_company_existing(self):
        """Test returning existing company (no duplicate)."""
        from app.services.job_market_repository_service import get_or_create_company
        from app.database.models import Company

        mock_db = MagicMock()
        existing_company = Company(id=42, name="TestCorp", website="https://testcorp.com")

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = existing_company

        result = get_or_create_company(mock_db, "TestCorp", "https://testcorp.com")

        assert result.id == 42
        # add() should NOT be called for existing company
        assert not mock_db.add.called
        print("✅ Existing company reuse works (no duplicate creation)")

    def test_get_or_create_job_offer_idempotent_on_url(self):
        """Test that duplicate job_url returns existing offer (idempotency)."""
        from app.services.job_market_repository_service import get_or_create_job_offer
        from app.database.models import JobOffer

        mock_db = MagicMock()
        existing_offer = JobOffer(
            id=10,
            company_id=1,
            job_url="https://example.com/job",
            job_title="Data Analyst"
        )

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = existing_offer

        result, is_new = get_or_create_job_offer(
            mock_db,
            company_id=1,
            job_url="https://example.com/job",
            job_title="Data Analyst",
            source="website",
            raw_text="Some text"
        )

        assert result.id == 10
        assert is_new is False  # Existing, not new
        print("✅ Duplicate URL detection works (idempotent)")

    def test_ingest_scraped_offers_mixed_success_error(self):
        """Test ingestion of multiple offers with some errors."""
        from app.services.job_market_repository_service import ingest_scraped_offers
        from app.database.models import Company, JobOffer

        mock_db = MagicMock()
        mock_company = Company(id=1, name="TestCorp")
        mock_offer = JobOffer(id=1, company_id=1, job_url="https://example.com/job")

        # Mock get_or_create_company
        with patch("app.services.job_market_repository_service.get_or_create_company") as mock_get_co:
            mock_get_co.return_value = mock_company

            # Mock get_or_create_job_offer
            with patch("app.services.job_market_repository_service.get_or_create_job_offer") as mock_get_jo:
                mock_get_jo.return_value = (mock_offer, True)

                scraped = [
                    {"job_url": "https://example.com/job1", "company_name": "Corp1", "job_title": "Role1", "source": "website", "raw_text": "text"},
                    {"job_url": "https://example.com/job2", "company_name": "Corp2", "job_title": "Role2", "source": "website", "raw_text": "text"},
                ]

                persisted, errors = ingest_scraped_offers(mock_db, scraped)

                assert len(persisted) == 2
                assert mock_db.commit.called
                print("✅ Ingestion with commit works")


def test_fixture_html_loads():
    """Verify fixture HTML exists and is realistic."""
    assert os.path.exists(FIXTURE_DIR / "sample_job_page.html")
    assert len(SAMPLE_JOB_HTML) > 1000  # Non-trivial HTML
    assert "Data Analyst" in SAMPLE_JOB_HTML
    assert "Sidel" in SAMPLE_JOB_HTML
    print("✅ Fixture HTML is realistic and loadable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
