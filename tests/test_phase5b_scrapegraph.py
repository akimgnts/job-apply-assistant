"""Phase 5B Tests: ScrapeGraphAI Provider Integration.

Unit tests for ScrapeGraphAI lead discovery provider.
All tests are mocked - no internet access required.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.scrapegraph_provider import (
    discover_contacts,
    DiscoveryCandidate,
)


class TestScrapegraphProvider:
    """Test ScrapeGraphAI provider integration."""

    def test_discovery_candidate_model(self):
        """Test DiscoveryCandidate data model."""
        candidate = DiscoveryCandidate(
            contact_name="Jane Doe",
            role_raw="Talent Acquisition Manager",
            company="Sidel",
            source_url="https://sidel.com/careers",
            linkedin_url="https://linkedin.com/in/jane-doe",
            email=None,
            evidence_text="Jane leads recruiting"
        )

        assert candidate.contact_name == "Jane Doe"
        assert candidate.role_raw == "Talent Acquisition Manager"
        assert candidate.source_url == "https://sidel.com/careers"
        assert candidate.email is None

    def test_candidate_to_lead_discovery_dict(self):
        """Test conversion to LeadDiscoveryService format."""
        candidate = DiscoveryCandidate(
            contact_name="Jane Doe",
            role_raw="Talent Acquisition Manager",
            company="Sidel",
            source_url="https://sidel.com/careers",
            linkedin_url=None,
            email=None
        )

        lead_dict = candidate.to_lead_discovery_dict()

        assert lead_dict["contact_name"] == "Jane Doe"
        assert lead_dict["role_raw"] == "Talent Acquisition Manager"
        assert lead_dict["source_url"] == "https://sidel.com/careers"
        assert lead_dict["data_source"] == "scrapegraphai"
        assert lead_dict["verification_status"] == "PARTIAL"
        assert lead_dict["email"] is None

    @patch('subprocess.run')
    def test_discover_contacts_success(self, mock_run):
        """Test successful discovery."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": [
                {
                    "contact_name": "Alice Johnson",
                    "role_raw": "Talent Acquisition Partner",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/careers",
                    "linkedin_url": None,
                    "email": None,
                    "evidence_text": "Alice leads TA at Sidel"
                }
            ]
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        candidates = discover_contacts("Sidel", max_contacts=3)

        assert len(candidates) == 1
        assert candidates[0].contact_name == "Alice Johnson"
        assert candidates[0].source_url == "https://sidel.com/careers"

    @patch('subprocess.run')
    def test_discover_contacts_missing_source_url_rejected(self, mock_run):
        """Test that candidates without source_url are rejected."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": [
                {
                    "contact_name": "Bob Smith",
                    "role_raw": "Recruiter",
                    "company": "Sidel",
                    "source_url": None,  # MISSING - should be rejected
                    "linkedin_url": None,
                    "email": None
                }
            ]
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        candidates = discover_contacts("Sidel")

        assert len(candidates) == 0  # Rejected due to missing source_url

    @patch('subprocess.run')
    def test_discover_contacts_null_optional_fields(self, mock_run):
        """Test that optional fields (email, linkedin) remain null."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": [
                {
                    "contact_name": "Charlie Brown",
                    "role_raw": "Data Manager",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/team",
                    "linkedin_url": None,
                    "email": None,
                    "evidence_text": None
                }
            ]
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        candidates = discover_contacts("Sidel")

        assert len(candidates) == 1
        assert candidates[0].email is None
        assert candidates[0].linkedin_url is None
        assert candidates[0].evidence_text is None

    @patch('subprocess.run')
    def test_discover_contacts_multiple_candidates(self, mock_run):
        """Test discovering multiple candidates."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": [
                {
                    "contact_name": "Alice",
                    "role_raw": "Talent Acquisition",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/careers",
                    "linkedin_url": None,
                    "email": None
                },
                {
                    "contact_name": "Bob",
                    "role_raw": "Data Lead",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/team",
                    "linkedin_url": None,
                    "email": None
                },
                {
                    "contact_name": "Charlie",
                    "role_raw": "AI Manager",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/leadership",
                    "linkedin_url": None,
                    "email": None
                }
            ]
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        candidates = discover_contacts("Sidel", max_contacts=3)

        assert len(candidates) == 3
        assert candidates[0].contact_name == "Alice"
        assert candidates[1].contact_name == "Bob"
        assert candidates[2].contact_name == "Charlie"

    @patch('subprocess.run')
    def test_discover_contacts_no_json_in_output(self, mock_run):
        """Test handling when no JSON found in worker output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Some text output without JSON"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Provider returns empty list when no JSON output found (defensive)
        candidates = discover_contacts("Sidel")
        assert len(candidates) == 0

    @patch('subprocess.run')
    def test_discover_contacts_worker_error(self, mock_run):
        """Test handling of worker execution error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ScrapeGraphAI failed to initialize"
        mock_run.return_value = mock_result

        with pytest.raises(RuntimeError, match="ScrapeGraphAI worker failed"):
            discover_contacts("Sidel")

    @patch('subprocess.run')
    def test_discover_contacts_with_website_param(self, mock_run):
        """Test that website parameter is passed to worker."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": []
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        discover_contacts(
            "Sidel",
            company_website="https://www.sidel.com",
            max_contacts=3
        )

        # Verify subprocess was called with website argument
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--website" in cmd
        assert "https://www.sidel.com" in cmd

    @patch('subprocess.run')
    def test_discover_contacts_respects_max_contacts_param(self, mock_run):
        """Test that max_contacts parameter is passed to worker."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": []
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        discover_contacts("Sidel", max_contacts=5)

        # Verify subprocess was called with max_contacts argument
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--max-contacts" in cmd
        assert "5" in cmd

    @patch('subprocess.run')
    def test_discover_contacts_no_results(self, mock_run):
        """Test handling of zero discovery results."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "UnknownCompany",
            "candidates": []
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        candidates = discover_contacts("UnknownCompany")

        assert len(candidates) == 0

    @patch('subprocess.run')
    def test_discover_contacts_partial_candidates(self, mock_run):
        """Test discovery with mix of valid and invalid candidates."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "company": "Sidel",
            "candidates": [
                {
                    "contact_name": "Valid Contact",
                    "role_raw": "Recruiter",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/careers",
                    "linkedin_url": None,
                    "email": None
                },
                {
                    "contact_name": None,  # INVALID - no name
                    "role_raw": "Manager",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/team",
                    "linkedin_url": None,
                    "email": None
                },
                {
                    "contact_name": "Another Valid",
                    "role_raw": "Data Lead",
                    "company": "Sidel",
                    "source_url": "https://sidel.com/leadership",
                    "linkedin_url": None,
                    "email": None
                }
            ]
        })
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        candidates = discover_contacts("Sidel")

        # Should skip the candidate with no name
        assert len(candidates) == 2
        assert candidates[0].contact_name == "Valid Contact"
        assert candidates[1].contact_name == "Another Valid"


class TestPhase5BIntegration:
    """Test integration with LeadDiscoveryService."""

    def test_scrapegraph_candidate_integrates_with_lead_service(self):
        """Verify DiscoveryCandidate output works with LeadDiscoveryService."""
        from app.services.lead_discovery_service import normalize_role_category

        candidate = DiscoveryCandidate(
            contact_name="Jane Doe",
            role_raw="Talent Acquisition Manager",
            company="Sidel",
            source_url="https://sidel.com/careers"
        )

        # Convert to LeadDiscoveryService format
        lead_dict = candidate.to_lead_discovery_dict()

        # Normalize role using Phase 5 service
        role_category = normalize_role_category(lead_dict["role_raw"])

        # Should normalize to a valid category
        assert role_category is not None
        assert role_category.value in [
            "TALENT_ACQUISITION",
            "DATA_LEADERSHIP",
            "DATA_MANAGER",
            "AI_LEADERSHIP",
            "AI_MANAGER",
            "ENGINEERING_MANAGER",
            "RECRUITER"
        ]

    def test_scrapegraph_output_format_matches_lead_discovery_expectation(self):
        """Verify output format matches LeadDiscoveryService input."""
        candidate = DiscoveryCandidate(
            contact_name="Test Contact",
            role_raw="Test Role",
            company="Test Company",
            source_url="https://example.com",
            linkedin_url="https://linkedin.com/in/test",
            email="test@example.com"
        )

        lead_dict = candidate.to_lead_discovery_dict()

        # Required fields for LeadDiscoveryService
        required_keys = {
            "contact_name",
            "role_raw",
            "source_url",
            "data_source",
            "verification_status"
        }

        assert required_keys.issubset(set(lead_dict.keys()))
        assert lead_dict["source_url"]  # Must have source_url
