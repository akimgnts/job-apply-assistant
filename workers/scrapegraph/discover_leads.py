#!/usr/bin/env python3
"""ScrapeGraphAI-based lead discovery provider for Job Market Radar Phase 5B.

This worker runs in isolation from the main application.

Input: company name, context
Output: JSON candidates

The main application's LeadDiscoveryService handles verification, normalization, and persistence.
"""

import json
import logging
import os
import sys
from typing import Optional
from pathlib import Path

# Add parent directory to path for config access
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workers.scrapegraph.schemas import DiscoveredContact, DiscoveryResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def discover_contacts_for_company(
    company_name: str,
    company_website: Optional[str] = None,
    context: Optional[dict] = None,
    max_contacts: int = 3
) -> DiscoveryResult:
    """Discover contacts at a company using ScrapeGraphAI.

    Args:
        company_name: Company to search
        company_website: Company website URL if known
        context: Additional context (job offers, skills, etc.)
        max_contacts: Maximum contacts to return

    Returns:
        DiscoveryResult with candidates ready for LeadDiscoveryService

    This function:
    1. Uses ScrapeGraphAI to search public sources
    2. Extracts structured contact candidates
    3. Returns minimal candidates (name, role, source_url only)
    4. Leaves verification to Phase 5 LeadDiscoveryService
    """

    try:
        from scrapegraphai.graphs import SearchGraph, SmartScraperGraph
    except ImportError as e:
        logger.error(f"ScrapeGraphAI not installed: {e}")
        raise ImportError(
            "Run: pip install -r workers/scrapegraph/requirements.txt"
        ) from e

    result = DiscoveryResult(
        company=company_name,
        candidates=[],
        search_queries_used=[],
        sources_checked=[],
        errors=[]
    )

    try:
        # Get LLM config from main app (reuse existing OPENAI_API_KEY)
        try:
            from app.config import config
            api_key = config.OPENAI_API_KEY
            model = config.OPENAI_MODEL or "gpt-4o-mini"
        except ImportError:
            # Fallback: read from environment
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        logger.info(f"Discovering contacts at {company_name}")

        # Strategy 1: Search company careers page
        if company_website:
            search_url = company_website
            logger.info(f"  Searching careers page: {search_url}")

            try:
                graph_config = {
                    "llm": {
                        "api_key": api_key,
                        "model": model
                    },
                    "verbose": False,
                    "headless": True
                }

                # Use SmartScraperGraph for structured extraction from known page
                scraper = SmartScraperGraph(
                    prompt=f"""
                    Extract publicly listed contact information for hiring at {company_name}.

                    Look for:
                    - Talent Acquisition / Recruiting roles
                    - Technical Recruiters
                    - Data/Analytics hiring managers
                    - AI/ML hiring leaders

                    For each contact found, return:
                    - Name (exact as shown publicly)
                    - Current role title (exact)
                    - Source URL (where found)
                    - LinkedIn URL if publicly linked
                    - Email if publicly listed

                    Return as JSON array.
                    Do NOT invent names or roles.
                    If unclear or unverifiable, omit the field.
                    Email and LinkedIn are optional.
                    """,
                    source=search_url,
                    config=graph_config
                )

                output = scraper.run()
                logger.info(f"  Scraper output: {output}")

                if output:
                    contacts = json.loads(output) if isinstance(output, str) else output
                    if isinstance(contacts, list):
                        for contact_data in contacts[:max_contacts]:
                            try:
                                candidate = _parse_contact_candidate(
                                    company_name,
                                    contact_data,
                                    source_url=search_url
                                )
                                if candidate:
                                    result.candidates.append(candidate)
                            except Exception as e:
                                logger.warning(f"  Failed to parse contact: {e}")
                                result.errors.append(str(e))

                result.sources_checked.append(search_url)

            except Exception as e:
                logger.warning(f"  Careers page search failed: {e}")
                result.errors.append(f"Careers page search: {str(e)}")

        # Strategy 2: Web search for company recruiters
        logger.info(f"  Searching web for {company_name} recruiters")

        try:
            graph_config = {
                "llm": {
                    "api_key": api_key,
                    "model": model
                },
                "verbose": False
            }

            # Use SearchGraph for web search
            search_graph = SearchGraph(
                prompt=f"""
                Find public information about hiring/recruitment contacts at {company_name}.

                Search for:
                - Talent Acquisition managers
                - Recruiters
                - Technical recruiters for Data/AI roles
                - Hiring managers visible in public sources

                For each result, include:
                - Name
                - Role
                - Source URL
                - LinkedIn URL if accessible
                - Email if publicly listed

                Return JSON array.
                Do NOT fabricate contacts.
                Only include verifiable public information.
                """,
                config=graph_config
            )

            output = search_graph.run()
            logger.info(f"  Search results: {output}")

            if output:
                contacts = json.loads(output) if isinstance(output, str) else output
                if isinstance(contacts, list):
                    for contact_data in contacts[:max_contacts]:
                        try:
                            candidate = _parse_contact_candidate(
                                company_name,
                                contact_data,
                                source_url=None
                            )
                            if candidate and not _is_duplicate(
                                candidate, result.candidates
                            ):
                                result.candidates.append(candidate)
                        except Exception as e:
                            logger.warning(f"  Failed to parse search result: {e}")
                            result.errors.append(str(e))

            result.sources_checked.append("web_search")

        except Exception as e:
            logger.warning(f"  Web search failed: {e}")
            result.errors.append(f"Web search: {str(e)}")

        # Limit to max_contacts
        result.candidates = result.candidates[:max_contacts]

        logger.info(
            f"✅ Discovery complete: {len(result.candidates)} candidates found"
        )

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise

    return result


def _parse_contact_candidate(
    company_name: str,
    data: dict,
    source_url: Optional[str]
) -> Optional[DiscoveredContact]:
    """Parse raw contact data from ScrapeGraphAI into DiscoveredContact.

    Validates:
    - source_url is present (mandatory)
    - contact_name and role are not obviously fabricated
    - email is not a guess
    - linkedin_url looks like a real profile URL
    """

    # Mandatory: source_url
    if not source_url and not data.get("source_url"):
        logger.debug("Skipping contact: no source_url")
        return None

    final_source_url = source_url or data.get("source_url")

    # Extract fields
    name = (data.get("name") or data.get("contact_name") or "").strip()
    role = (data.get("role") or data.get("role_raw") or "").strip()
    linkedin = (data.get("linkedin_url") or "").strip()
    email = (data.get("email") or "").strip()
    evidence = (data.get("evidence_text") or "").strip()

    # Validation: name and role should exist
    if not name or not role:
        logger.debug(f"Skipping contact: missing name or role")
        return None

    # Validation: name should be reasonable length (not a sentence)
    if len(name) > 100 or "\n" in name:
        logger.debug(f"Skipping contact: name looks invalid: {name}")
        return None

    # Validation: role should be reasonable length
    if len(role) > 200:
        logger.debug(f"Skipping contact: role too long: {role}")
        return None

    # Validation: email should look like email if present
    if email and ("@" not in email or len(email) > 254):
        logger.debug(f"Skipping contact: email looks invalid: {email}")
        email = None  # Don't guess

    # Validation: LinkedIn should look like LinkedIn URL
    if linkedin:
        if not ("linkedin.com" in linkedin.lower() and "/in/" in linkedin.lower()):
            logger.debug(f"Skipping contact: linkedin_url doesn't look like LinkedIn: {linkedin}")
            linkedin = None

    return DiscoveredContact(
        contact_name=name if name else None,
        role_raw=role if role else None,
        company=company_name,
        source_url=final_source_url,
        linkedin_url=linkedin if linkedin else None,
        email=email if email else None,
        evidence_text=evidence if evidence else None
    )


def _is_duplicate(
    candidate: DiscoveredContact,
    existing: list[DiscoveredContact]
) -> bool:
    """Check if candidate is already in list (by name + source)."""
    for existing_candidate in existing:
        if (
            existing_candidate.contact_name == candidate.contact_name
            and existing_candidate.source_url == candidate.source_url
        ):
            return True
    return False


def main():
    """CLI entry point for manual discovery testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ScrapeGraphAI lead discovery for Job Market Radar"
    )
    parser.add_argument(
        "--company",
        required=True,
        help="Company name (e.g., 'Sidel')"
    )
    parser.add_argument(
        "--website",
        help="Company website URL"
    )
    parser.add_argument(
        "--max-contacts",
        type=int,
        default=3,
        help="Maximum contacts to discover (default: 3)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file (default: stdout)"
    )

    args = parser.parse_args()

    try:
        result = discover_contacts_for_company(
            company_name=args.company,
            company_website=args.website,
            max_contacts=args.max_contacts
        )

        output_dict = {
            "company": result.company,
            "candidates": [c.model_dump() for c in result.candidates],
            "search_queries_used": result.search_queries_used,
            "sources_checked": result.sources_checked,
            "errors": result.errors
        }

        output_json = json.dumps(output_dict, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
            print(f"Results saved to {args.output}")
        else:
            print(output_json)

        # Summary
        print(f"\n{'='*60}")
        print(f"Discovered {len(result.candidates)} contacts at {args.company}")
        print(f"Sources: {', '.join(result.sources_checked)}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
        print(f"{'='*60}")

    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
