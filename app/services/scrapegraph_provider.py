"""ScrapeGraphAI Lead Discovery Provider for Phase 5B.

Bridges isolated ScrapeGraphAI worker to main application's LeadDiscoveryService.

Pattern:
1. Call discover_leads.py (isolated worker) with company context
2. Collect raw candidates (JSON)
3. Pass to LeadDiscoveryService for verification/persistence
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryCandidate:
    """Raw candidate from ScrapeGraphAI provider."""

    contact_name: Optional[str]
    role_raw: Optional[str]
    company: str
    source_url: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    evidence_text: Optional[str] = None

    def to_lead_discovery_dict(self) -> dict:
        """Convert to LeadDiscoveryService input format."""
        return {
            "contact_name": self.contact_name,
            "role_raw": self.role_raw,
            "linkedin_url": self.linkedin_url,
            "email": self.email,
            "source_url": self.source_url,
            "data_source": "scrapegraphai",
            "verification_status": "PARTIAL"  # Let LeadDiscoveryService verify
        }


def discover_contacts(
    company_name: str,
    company_website: Optional[str] = None,
    max_contacts: int = 3
) -> List[DiscoveryCandidate]:
    """Discover contacts at a company using isolated ScrapeGraphAI worker.

    Args:
        company_name: Company to search (e.g., "Sidel")
        company_website: Company website if known
        max_contacts: Maximum contacts to return (default: 3)

    Returns:
        List of DiscoveryCandidate objects

    Raises:
        RuntimeError: If worker execution fails or returns invalid JSON
    """

    worker_path = Path(__file__).parent.parent.parent / "workers" / "scrapegraph"
    venv_python = worker_path / ".venv" / "bin" / "python3"

    if not venv_python.exists():
        raise RuntimeError(
            f"ScrapeGraphAI worker venv not found at {venv_python}. "
            "Run: cd workers/scrapegraph && python3 -m venv .venv && "
            "source .venv/bin/activate && pip install -r requirements.txt"
        )

    # Build command
    cmd = [
        str(venv_python),
        str(worker_path / "discover_leads.py"),
        "--company", company_name,
        "--max-contacts", str(max_contacts),
    ]

    if company_website:
        cmd.extend(["--website", company_website])

    logger.info(f"Calling ScrapeGraphAI worker: {' '.join(cmd[:4])}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minutes max
        )

        if result.returncode != 0:
            logger.error(f"Worker stderr: {result.stderr}")
            raise RuntimeError(
                f"ScrapeGraphAI worker failed: {result.stderr}"
            )

        # Parse JSON output
        output_lines = result.stdout.strip().split('\n')
        json_line = None

        for line in output_lines:
            if line.startswith('{'):
                json_line = line
                break

        if not json_line:
            logger.warning(f"No JSON output from worker")
            return []

        output = json.loads(json_line)

        candidates = []
        for candidate_data in output.get("candidates", []):
            try:
                candidate = DiscoveryCandidate(
                    contact_name=candidate_data.get("contact_name"),
                    role_raw=candidate_data.get("role_raw"),
                    company=candidate_data.get("company", company_name),
                    source_url=candidate_data.get("source_url"),
                    linkedin_url=candidate_data.get("linkedin_url"),
                    email=candidate_data.get("email"),
                    evidence_text=candidate_data.get("evidence_text")
                )

                # Validate mandatory fields
                if not candidate.source_url:
                    logger.warning(
                        f"Skipping candidate: missing source_url"
                    )
                    continue

                if not candidate.contact_name:
                    logger.warning(
                        f"Skipping candidate: missing contact_name"
                    )
                    continue

                if not candidate.role_raw:
                    logger.warning(
                        f"Skipping candidate: missing role_raw"
                    )
                    continue

                candidates.append(candidate)

            except Exception as e:
                logger.warning(f"Failed to parse candidate: {e}")

        logger.info(
            f"✓ Discovered {len(candidates)} candidates for {company_name}"
        )

        return candidates

    except subprocess.TimeoutExpired:
        logger.error(f"ScrapeGraphAI worker timeout (120s)")
        raise RuntimeError("ScrapeGraphAI worker timeout")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse worker JSON: {e}")
        raise RuntimeError(f"Invalid JSON from worker: {e}")

    except Exception as e:
        logger.error(f"Unexpected worker error: {e}")
        raise RuntimeError(f"ScrapeGraphAI worker error: {e}")
