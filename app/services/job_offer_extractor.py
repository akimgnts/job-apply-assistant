"""Extract job offer details from HTML using deterministic methods."""

import re
import json
import logging
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


class JobOfferExtractor:
    """Extract structured job data from HTML."""

    @staticmethod
    def extract(html: str, url: str = "") -> dict:
        """Extract job details from HTML using deterministic methods.

        Returns dict with keys: title, location, description, skills,
        contract_type, external_job_id, posted_date, extraction_confidence.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Try schema.org JobPosting first
        schema = JobOfferExtractor._extract_schema_org(soup)
        if schema:
            return schema

        # Fallback to pattern-based extraction
        return JobOfferExtractor._extract_patterns(soup, html, url)

    @staticmethod
    def _extract_schema_org(soup: BeautifulSoup) -> Optional[dict]:
        """Extract from schema.org/JobPosting structured data."""
        try:
            for script in soup.find_all("script", type="application/ld+json"):
                data = json.loads(script.string)

                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return {
                        "title": data.get("title"),
                        "location": JobOfferExtractor._extract_location_from_schema(data),
                        "description": data.get("description"),
                        "contract_type": data.get("employmentType"),
                        "external_job_id": data.get("identifier"),
                        "posted_date": data.get("datePosted"),
                        "skills": data.get("skills", []),
                        "extraction_method": "schema_org",
                        "extraction_confidence": 0.95,
                    }
        except Exception as e:
            logger.debug(f"Schema.org extraction failed: {e}")

        return None

    @staticmethod
    def _extract_location_from_schema(data: dict) -> Optional[str]:
        """Extract location from schema.org data."""
        job_location = data.get("jobLocation", {})
        if isinstance(job_location, dict):
            address = job_location.get("address", {})
            if isinstance(address, dict):
                return address.get("addressLocality")
        return None

    @staticmethod
    def _extract_patterns(soup: BeautifulSoup, html: str, url: str) -> dict:
        """Fallback pattern-based extraction."""
        result = {
            "title": None,
            "location": None,
            "description": None,
            "contract_type": None,
            "external_job_id": None,
            "posted_date": None,
            "skills": [],
            "extraction_method": "patterns",
            "extraction_confidence": 0.0,
        }

        # Title from <h1> (30 points)
        h1 = soup.find("h1")
        if h1:
            result["title"] = h1.get_text(strip=True)
            result["extraction_confidence"] += 0.30

        # Location from common selectors (20 points)
        for selector in ["location", "place", "city"]:
            loc_elem = soup.find("div", class_=re.compile(selector, re.I))
            if loc_elem:
                result["location"] = loc_elem.get_text(strip=True)[:100]
                result["extraction_confidence"] += 0.20
                break

        # Description from common selectors (30 points)
        for selector in ["description", "details", "job-content", "job-description"]:
            desc_elem = soup.find("div", class_=re.compile(selector, re.I))
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if len(text) > 100:
                    result["description"] = text[:2000]
                    result["extraction_confidence"] += 0.30
                    break

        # Skills from lists (10 points)
        for ul in soup.find_all("ul"):
            parent_text = ul.find_previous(string=re.compile(r"skills", re.I))
            if parent_text:
                skills = [li.get_text(strip=True) for li in ul.find_all("li")]
                if skills:
                    result["skills"] = skills
                    result["extraction_confidence"] += 0.10
                break

        # Contract type from text patterns (10 points)
        if re.search(r"(contract type|employment type).{0,20}(cdi|permanent)", html, re.I):
            result["contract_type"] = "CDI"
            result["extraction_confidence"] += 0.10
        elif re.search(r"(contract type|employment type).{0,20}(cdd|contract|fixed-term)", html, re.I):
            result["contract_type"] = "CDD"
            result["extraction_confidence"] += 0.10

        return result

    @staticmethod
    def estimate_confidence(extracted: dict) -> float:
        """Estimate extraction quality (0-1) based on fields populated."""
        confidence = extracted.get("extraction_confidence", 0.0)

        # Boost if we have title + description
        if extracted.get("title") and extracted.get("description"):
            confidence = min(1.0, confidence + 0.15)

        return confidence
