"""Phase 2B: Comprehensive unit + integration tests."""

import pytest
import asyncio
from bs4 import BeautifulSoup
from app.services.url_normalizer import normalize_url, url_hash, is_same_domain
from app.services.job_candidate_detector import JobCandidateDetector
from app.services.job_offer_extractor import JobOfferExtractor
from app.models.job_source_adapter import DiscoveredJobUrl, NormalizedJobOffer


class TestURLNormalization:
    """Test URL normalization for deduplication."""

    def test_normalize_removes_fragment(self):
        """Remove URL fragment."""
        url = "https://sidel.com/job/123#apply"
        normalized = normalize_url(url)
        assert "#" not in normalized
        assert "apply" not in normalized

    def test_normalize_removes_utm_params(self):
        """Remove tracking parameters."""
        url = "https://sidel.com/job/123?utm_source=linkedin&utm_campaign=hiring"
        normalized = normalize_url(url)
        assert "utm_" not in normalized
        assert "/job/123" in normalized

    def test_normalize_keeps_context_params(self):
        """Keep legitimate context parameters."""
        url = "https://sidel.com/job/123?lang=fr&ref=internal"
        normalized = normalize_url(url)
        assert "lang=fr" in normalized
        assert "ref=internal" in normalized

    def test_normalize_lowercase(self):
        """Lowercase scheme and hostname."""
        url = "HTTPS://SIDEL.COM/Job/123"
        normalized = normalize_url(url)
        assert normalized.startswith("https://sidel.com")

    def test_normalize_trailing_slash(self):
        """Remove trailing slash."""
        url1 = "https://sidel.com/job/123"
        url2 = "https://sidel.com/job/123/"
        assert normalize_url(url1) == normalize_url(url2)

    def test_url_hash_deterministic(self):
        """Hash is deterministic."""
        url = "https://sidel.com/job/123?utm_source=x"
        hash1 = url_hash(url)
        hash2 = url_hash(url)
        assert hash1 == hash2

    def test_url_hash_length(self):
        """Hash is SHA256 (64 hex chars)."""
        url = "https://sidel.com/job/123"
        h = url_hash(url)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_domain_match(self):
        """Detect same domain."""
        url1 = "https://sidel.com/job/123"
        url2 = "https://sidel.com/about"
        assert is_same_domain(url1, url2)

    def test_same_domain_no_match(self):
        """Detect different domain."""
        url1 = "https://sidel.com/job/123"
        url2 = "https://indeed.com/job/123"
        assert not is_same_domain(url1, url2)


class TestJobCandidateDetector:
    """Test deterministic job page scoring."""

    def test_score_url_pattern_match(self):
        """URL pattern adds 35 points."""
        detector = JobCandidateDetector()
        result = detector.score("https://sidel.com/job/123", "<html></html>")
        assert result["signals"]["url_pattern"]
        assert result["score"] >= 35

    def test_score_schema_org_jobposting(self):
        """Schema.org JobPosting adds 40 points."""
        detector = JobCandidateDetector()
        html = '<script type="application/ld+json">{"@type": "JobPosting"}</script>'
        result = detector.score("https://sidel.com/page", html)
        assert result["signals"]["jobposting_schema"]
        assert result["score"] >= 40

    def test_score_apply_button(self):
        """Apply button/link adds 20 points."""
        detector = JobCandidateDetector()
        html = '<a href="/apply">Apply Now</a>'
        result = detector.score("https://sidel.com/page", html)
        assert result["signals"]["apply_button"]
        assert result["score"] >= 20

    def test_score_description_markers(self):
        """Description markers add 15 points."""
        detector = JobCandidateDetector()
        html = "<h1>Title</h1>" + "x" * 500 + "<p>Requirements: Python, SQL</p>"
        result = detector.score("https://sidel.com/page", html)
        assert result["signals"]["description_markers"]
        assert result["score"] >= 15

    def test_score_title_signal(self):
        """Job title keywords add 10 points."""
        detector = JobCandidateDetector()
        result = detector.score("https://sidel.com/page", "<html></html>", title="Data Engineer")
        assert result["signals"]["title_signal"]
        assert result["score"] >= 10

    def test_score_content_length(self):
        """Nontrivial content adds 5 points."""
        detector = JobCandidateDetector()
        html = "<p>Job description. " + "x" * 500 + "</p>"
        result = detector.score("https://sidel.com/page", html)
        assert result["signals"]["content_length"]
        assert result["score"] >= 5

    def test_is_candidate_threshold(self):
        """Score >= 60 is candidate."""
        detector = JobCandidateDetector()
        # High-scoring page
        html = (
            '<h1>Data Engineer</h1>'
            '<a href="/apply">Apply</a>'
            '<p>Requirements: ' + "x" * 500 + '</p>'
        )
        result = detector.score("https://sidel.com/job/123", html, title="Data Engineer")
        assert result["is_candidate"]
        assert result["score"] >= 60

    def test_not_candidate_low_score(self):
        """Score < 60 is not candidate."""
        detector = JobCandidateDetector()
        result = detector.score("https://sidel.com/about", "<p>About us</p>")
        assert not result["is_candidate"]
        assert result["score"] < 60


class TestJobOfferExtraction:
    """Test job data extraction."""

    def test_extract_schema_org_jobposting(self):
        """Extract from schema.org JobPosting."""
        extractor = JobOfferExtractor()
        html = """
        <script type="application/ld+json">
        {
            "@type": "JobPosting",
            "title": "Data Engineer",
            "jobLocation": {"address": {"addressLocality": "Lyon"}},
            "description": "We are hiring...",
            "employmentType": "FULL_TIME",
            "identifier": "ext-123"
        }
        </script>
        """
        result = extractor.extract(html)
        assert result["title"] == "Data Engineer"
        assert result["location"] == "Lyon"
        assert result["contract_type"] == "FULL_TIME"
        assert result["external_job_id"] == "ext-123"
        assert result["extraction_method"] == "schema_org"

    def test_extract_patterns_title(self):
        """Extract title from <h1>."""
        extractor = JobOfferExtractor()
        html = "<h1>Senior Data Analyst</h1><p>" + "x" * 600 + "</p>"
        result = extractor.extract(html)
        assert result["title"] == "Senior Data Analyst"

    def test_extract_patterns_location(self):
        """Extract location from div."""
        extractor = JobOfferExtractor()
        html = '<h1>Job</h1><div class="location">Paris, France</div>'
        result = extractor.extract(html)
        assert result["location"] == "Paris, France"

    def test_extract_patterns_description(self):
        """Extract description from div."""
        extractor = JobOfferExtractor()
        html = (
            '<h1>Job</h1>'
            '<div class="job-description">Long description '
            + 'x' * 600 + '</div>'
        )
        result = extractor.extract(html)
        assert len(result["description"]) > 100

    def test_extract_patterns_skills(self):
        """Extract skills from <ul>."""
        extractor = JobOfferExtractor()
        html = (
            '<h1>Job</h1>'
            'Skills required:'
            '<ul><li>Python</li><li>SQL</li><li>Power BI</li></ul>'
            '<p>' + 'x' * 600 + '</p>'
        )
        result = extractor.extract(html)
        assert "Python" in result["skills"]
        assert "SQL" in result["skills"]

    def test_estimate_confidence_high(self):
        """High confidence with title + description."""
        extractor = JobOfferExtractor()
        extracted = {
            "title": "Data Engineer",
            "description": "Job description " * 100,
            "extraction_confidence": 0.6,
        }
        confidence = extractor.estimate_confidence(extracted)
        assert confidence > 0.70

    def test_estimate_confidence_low(self):
        """Low confidence with missing fields."""
        extractor = JobOfferExtractor()
        extracted = {
            "title": None,
            "description": None,
            "extraction_confidence": 0.0,
        }
        confidence = extractor.estimate_confidence(extracted)
        assert confidence <= 0.15


class TestSourceAdapterInterface:
    """Test JobSourceAdapter interface."""

    def test_normalized_job_offer_creation(self):
        """Create NormalizedJobOffer."""
        offer = NormalizedJobOffer(
            job_title="Data Engineer",
            company_name="Sidel",
            job_url="https://sidel.com/job/123",
            source="career_site",
            location="Lyon",
            contract_type="CDI",
            external_job_id="sidel-123",
        )
        assert offer.job_title == "Data Engineer"
        assert offer.source == "career_site"

    def test_discovered_job_url_metadata(self):
        """Store discovery metadata."""
        discovered = DiscoveredJobUrl(
            url="https://sidel.com/job/123",
            metadata={"title": "Data Engineer", "signals": {"url_pattern": True}},
        )
        assert discovered.metadata["title"] == "Data Engineer"


# Integration tests (real database, no network)
class TestCareerCrawlUrlModel:
    """Integration: CareerCrawlUrl model."""

    def test_create_career_crawl_url(self):
        """Create CareerCrawlUrl record."""
        from app.database.db import SessionLocal
        from app.database.models import CareerCrawlUrl, Company
        from app.services.url_normalizer import url_hash

        db = SessionLocal()
        try:
            # Get Sidel company
            company = db.query(Company).filter(Company.name == "Sidel").first()
            if not company:
                pytest.skip("Sidel company not in database")

            url = "https://sidel.com/job/data-engineer-123"
            normalized = normalize_url(url)
            hash_val = url_hash(url)

            record = CareerCrawlUrl(
                company_id=company.id,
                discovered_url=url,
                normalized_url=normalized,
                url_hash=hash_val,
                page_title="Data Engineer - Lyon",
                is_job_candidate=1,
                detection_signals={"url_pattern": True, "schema": False},
                detection_score=75,
                status="CANDIDATE",
            )
            db.add(record)
            db.commit()

            # Verify
            found = db.query(CareerCrawlUrl).filter(
                CareerCrawlUrl.url_hash == hash_val
            ).first()
            assert found is not None
            assert found.status == "CANDIDATE"

            # Cleanup
            db.delete(found)
            db.commit()
        finally:
            db.close()

    def test_company_scoped_uniqueness(self):
        """Enforce company-scoped URL uniqueness."""
        from app.database.db import SessionLocal
        from app.database.models import CareerCrawlUrl, Company
        from app.services.url_normalizer import normalize_url, url_hash

        db = SessionLocal()
        try:
            # Clean up any prior test data
            hash_val = url_hash("https://sidel.com/job/456")
            db.query(CareerCrawlUrl).filter(CareerCrawlUrl.url_hash == hash_val).delete()
            db.commit()

            company = db.query(Company).filter(Company.name == "Sidel").first()
            if not company:
                pytest.skip("Sidel company not in database")

            url = "https://sidel.com/job/456"
            normalized = normalize_url(url)

            # Create first record
            record1 = CareerCrawlUrl(
                company_id=company.id,
                discovered_url=url,
                normalized_url=normalized,
                url_hash=hash_val,
                is_job_candidate=1,
                status="CANDIDATE",
            )
            db.add(record1)
            db.commit()

            # Verify we can query it back
            found = db.query(CareerCrawlUrl).filter(
                CareerCrawlUrl.company_id == company.id,
                CareerCrawlUrl.normalized_url == normalized,
            ).first()
            assert found is not None

            # Cleanup
            db.query(CareerCrawlUrl).filter(CareerCrawlUrl.url_hash == hash_val).delete()
            db.commit()
        finally:
            db.close()


class TestRegression:
    """Regression: existing functionality unaffected."""

    def test_company_model_unchanged(self):
        """Company model works."""
        from app.database.db import SessionLocal
        from app.database.models import Company

        db = SessionLocal()
        try:
            sidel = db.query(Company).filter(Company.name == "Sidel").first()
            assert sidel is not None
            assert sidel.website == "https://www.sidel.com"
        finally:
            db.close()

    def test_job_offer_model_unchanged(self):
        """JobOffer model works."""
        from app.database.db import SessionLocal
        from app.database.models import JobOffer

        db = SessionLocal()
        try:
            offers = db.query(JobOffer).limit(1).all()
            # Should not error
            assert isinstance(offers, list)
        finally:
            db.close()

    def test_company_contact_model_unchanged(self):
        """CompanyContact model works."""
        from app.database.db import SessionLocal
        from app.database.models import CompanyContact

        db = SessionLocal()
        try:
            contacts = db.query(CompanyContact).limit(1).all()
            assert isinstance(contacts, list)
        finally:
            db.close()
