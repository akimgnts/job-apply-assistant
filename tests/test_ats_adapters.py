"""Unit tests for ATS adapters.

Validates adapter logic without requiring live API access.
Uses fixture data matching real API responses.
"""

import pytest
import asyncio
from app.models.job_source_adapter import DiscoveredJobUrl, NormalizedJobOffer
from app.services.greenhouse_adapter import GreenhouseAdapter
from app.services.lever_adapter import LeverAdapter
from app.services.ashby_adapter import AshbyAdapter


class TestGreenhouseAdapter:
    """Greenhouse adapter tests."""

    @pytest.mark.asyncio
    async def test_adapter_initializes(self):
        """Adapter can be instantiated."""
        adapter = GreenhouseAdapter()
        assert adapter.source_name == "greenhouse"
        assert adapter.collection_strategy == "api"
        await adapter.close()

    @pytest.mark.asyncio
    async def test_normalize_job_with_fixture_data(self):
        """Normalize method produces correct NormalizedJobOffer."""
        adapter = GreenhouseAdapter()

        extracted = {
            "title": "Software Engineer",
            "company_name": "Stripe",
            "source_url": "https://stripe.greenhouse.io/jobs/123",
            "job_id": "123",
            "company_slug": "stripe",
            "location": "Remote",
        }

        normalized = await adapter.normalize_job(extracted)

        assert isinstance(normalized, NormalizedJobOffer)
        assert normalized.job_title == "Software Engineer"
        assert normalized.company_name == "Stripe"
        assert normalized.source == "greenhouse"
        assert normalized.job_url == "https://stripe.greenhouse.io/jobs/123"
        assert normalized.external_job_id == "123"

        await adapter.close()

    @pytest.mark.asyncio
    async def test_extract_job_handles_error_gracefully(self):
        """Extract method returns fallback dict on error."""
        adapter = GreenhouseAdapter()

        discovered = DiscoveredJobUrl(
            url="https://invalid.example.com/404",
            metadata={"title": "Test Job", "company_name": "Test"}
        )

        extracted = await adapter.extract_job(discovered)

        assert "title" in extracted
        assert extracted["extraction_method"] == "greenhouse_error"
        assert extracted["extraction_confidence"] == 0.0

        await adapter.close()


class TestLeverAdapter:
    """Lever adapter tests."""

    @pytest.mark.asyncio
    async def test_adapter_initializes(self):
        """Adapter can be instantiated."""
        adapter = LeverAdapter()
        assert adapter.source_name == "lever"
        assert adapter.collection_strategy == "api"
        await adapter.close()

    @pytest.mark.asyncio
    async def test_normalize_job_with_fixture_data(self):
        """Normalize method produces correct NormalizedJobOffer."""
        adapter = LeverAdapter()

        extracted = {
            "title": "Data Scientist",
            "company_name": "Deel",
            "source_url": "https://jobs.lever.co/deel/abc123",
            "posting_id": "abc123",
            "company_handle": "deel",
        }

        normalized = await adapter.normalize_job(extracted)

        assert isinstance(normalized, NormalizedJobOffer)
        assert normalized.job_title == "Data Scientist"
        assert normalized.company_name == "Deel"
        assert normalized.source == "lever"
        assert normalized.job_url == "https://jobs.lever.co/deel/abc123"
        assert normalized.external_job_id == "abc123"

        await adapter.close()


class TestAshbyAdapter:
    """Ashby adapter tests."""

    @pytest.mark.asyncio
    async def test_adapter_initializes(self):
        """Adapter can be instantiated."""
        adapter = AshbyAdapter()
        assert adapter.source_name == "ashby"
        assert adapter.collection_strategy == "api"
        await adapter.close()

    @pytest.mark.asyncio
    async def test_normalize_job_with_fixture_data(self):
        """Normalize method produces correct NormalizedJobOffer."""
        adapter = AshbyAdapter()

        extracted = {
            "title": "Backend Engineer",
            "source_url": "https://jobs.ashby.com/anthropic/xyz789",
            "job_id": "xyz789",
            "company_slug": "anthropic",
            "location": "San Francisco",
        }

        normalized = await adapter.normalize_job(extracted)

        assert isinstance(normalized, NormalizedJobOffer)
        assert normalized.job_title == "Backend Engineer"
        assert normalized.company_name == "Anthropic"
        assert normalized.source == "ashby"
        assert normalized.location == "San Francisco"
        assert normalized.external_job_id == "xyz789"

        await adapter.close()


class TestAdapterContract:
    """Validate adapter interface contracts."""

    def test_all_adapters_implement_required_methods(self):
        """All adapters implement JobSourceAdapter interface."""
        adapters = [
            GreenhouseAdapter(),
            LeverAdapter(),
            AshbyAdapter(),
        ]

        required_methods = ["discover_jobs", "extract_job", "normalize_job"]

        for adapter in adapters:
            for method in required_methods:
                assert hasattr(adapter, method), f"{adapter.__class__.__name__} missing {method}"
                assert callable(getattr(adapter, method))

    def test_normalized_offer_has_required_fields(self):
        """NormalizedJobOffer contains all required fields."""
        offer = NormalizedJobOffer(
            job_title="Test",
            company_name="Test Co",
            job_url="https://example.com",
            source="test",
        )

        assert offer.job_title == "Test"
        assert offer.company_name == "Test Co"
        assert offer.job_url == "https://example.com"
        assert offer.source == "test"
        assert offer.location is None  # Optional
        assert offer.external_job_id is None  # Optional
