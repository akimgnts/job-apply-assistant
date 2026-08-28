"""Semantic parsing of CV text into claims with source block mapping.

This is the ONLY place where LLM is used in the validation pipeline.

Purpose:
- Extract atomic claims from CV text (e.g., "Built 10 dashboards")
- Map each claim to its source block (e.g., "sidel_dashboard_portfolio")
- Classify claim type (experience, metric, skill, date, etc.)

The deterministic ClaimValidatorService then validates each parsed claim.
"""

import json
import logging
from typing import List, Optional
from dataclasses import dataclass

from app.services.openai_service import generate_text

logger = logging.getLogger(__name__)


@dataclass
class ParsedClaim:
    """A single extracted claim with metadata."""

    text: str  # The claim text (e.g., "Built 10 dashboards and reporting tools")
    claim_type: str  # "experience", "metric", "skill", "date", "achievement"
    source_block_ref: Optional[str]  # Inferred source block (e.g., "master_v3:sidel_dashboard_portfolio")
    confidence: float  # 0.0–1.0 confidence in source mapping
    technologies: List[str] = None  # Extracted technologies
    metrics: Optional[str] = None  # Extracted metrics (e.g., "~10", "30–40")
    proficiency_hint: Optional[str] = None  # Heuristic proficiency ("expert", "intermediate", "beginner")


class ClaimParserService:
    """Parse CV text into semantic claims using LLM."""

    @staticmethod
    async def parse_cv_into_claims(cv_text: str, master_profile_context: str) -> List[ParsedClaim]:
        """Parse CV text into claims with source block mapping.

        Args:
            cv_text: Generated CV HTML/text content
            master_profile_context: Context about the atomic blocks (for LLM reference)

        Returns:
            List of ParsedClaim objects
        """
        prompt = f"""You are a claim extraction system for a job application CV.

Your task: Extract every factual claim from the CV and map it to its source block from the candidate's atomic profile.

ATOMIC BLOCKS (Reference):
{master_profile_context}

INSTRUCTIONS:
1. Extract each claim as a separate, atomic assertion (one fact per claim)
2. For each claim, infer which atomic profile block it likely comes from
3. Classify the claim type: "experience", "metric", "skill", "date", "achievement"
4. Extract technologies mentioned (e.g., ["Power BI", "Python"])
5. Extract any metrics (e.g., "~10", "30–40", "45 minutes")
6. Rate confidence in source block mapping (0.0–1.0)

EXAMPLE OUTPUT:
{{
  "claims": [
    {{
      "text": "Built and maintained around 10 dashboards and reporting tools",
      "claim_type": "achievement",
      "source_block_ref": "master_v3:sidel_dashboard_portfolio",
      "confidence": 0.95,
      "technologies": ["Power BI", "Power Query", "Excel"],
      "metrics": "~10",
      "proficiency_hint": "expert"
    }},
    {{
      "text": "Used weekly and monthly by approximately 30–40 stakeholders",
      "claim_type": "metric",
      "source_block_ref": "master_v3:sidel_dashboard_portfolio",
      "confidence": 0.90,
      "metrics": "~30–40"
    }}
  ]
}}

CV TEXT TO PARSE:
{cv_text}

RESPONSE (JSON only):
"""

        response = await generate_text(prompt, json_mode=True)

        try:
            data = json.loads(response)
            claims = []
            for claim_data in data.get("claims", []):
                claim = ParsedClaim(
                    text=claim_data.get("text", ""),
                    claim_type=claim_data.get("claim_type", "unknown"),
                    source_block_ref=claim_data.get("source_block_ref"),
                    confidence=float(claim_data.get("confidence", 0.5)),
                    technologies=claim_data.get("technologies"),
                    metrics=claim_data.get("metrics"),
                    proficiency_hint=claim_data.get("proficiency_hint"),
                )
                claims.append(claim)
            return claims
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []

    @staticmethod
    async def resolve_ambiguous_mapping(
        claim: str,
        possible_blocks: List[str],
        profile_context: str,
    ) -> str:
        """Resolve ambiguous source block mapping using LLM.

        When ClaimValidatorService finds multiple possible source blocks,
        use LLM to determine which one is most likely.

        Args:
            claim: The claim text
            possible_blocks: List of possible source_refs
            profile_context: Description of candidate's profile

        Returns:
            Most likely source_ref
        """
        if len(possible_blocks) == 1:
            return possible_blocks[0]

        prompt = f"""Given this claim from a CV, which atomic profile block is it most likely sourced from?

CLAIM: "{claim}"

POSSIBLE BLOCKS:
{chr(10).join(f"- {block}" for block in possible_blocks)}

PROFILE CONTEXT:
{profile_context}

REASON: Briefly explain why, then respond with ONLY the block reference (e.g., master_v3:sidel_reporting_automation)
"""

        response = await generate_text(prompt, json_mode=False)

        # Extract block ref from response (last line or first line with "master_v3:")
        for line in response.strip().split("\n"):
            if "master_v3:" in line:
                # Extract the reference
                import re
                match = re.search(r"master_v3:\S+", line)
                if match:
                    return match.group(0)

        # Fallback to first option
        return possible_blocks[0]

    @staticmethod
    def batch_parse_claims(
        claims_text: str,
        atomic_blocks_json: str,
    ) -> List[ParsedClaim]:
        """Synchronous batch parsing (wraps async for use in non-async contexts).

        This is a helper for testing. In production, use parse_cv_into_claims() with await.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            ClaimParserService.parse_cv_into_claims(claims_text, atomic_blocks_json)
        )
