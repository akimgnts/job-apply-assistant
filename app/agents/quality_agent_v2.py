"""Quality Agent V2: Claim-by-claim validation against atomic profile blocks.

Pipeline:
1. Parse CV into claims (ClaimParserService)
2. For each claim:
   a. Determine source block(s)
   b. Validate against block metadata (ClaimValidatorService)
   c. Decide: PASS / REWRITE / REMOVE
3. Reconstruct CV with validated claims

Philosophy:
- Allowlist-first: only what is provably in the atomic blocks
- No generic skill justification
- Frozen metrics, levels, dates, technologies, statuses
- Deterministic validation (no AI guessing)
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.models import ProfileBlock
from app.services.claim_parser_service import ClaimParserService, ParsedClaim
from app.services.claim_validator_service import ClaimValidatorService, ClaimValidation, ValidationAction

logger = logging.getLogger(__name__)


@dataclass
class ValidatedClaim:
    """A claim after validation."""

    original_text: str
    action: ValidationAction
    reason: str
    source_blocks: List[str]
    rewritten_text: Optional[str] = None  # If action is REWRITE


class QualityAgentV2:
    """Claim-by-claim validation against atomic profile blocks."""

    @staticmethod
    async def validate_document(
        db: Session,
        document_text: str,
        document_type: str = "cv",  # cv, letter, mail
    ) -> Dict:
        """Validate a generated document claim-by-claim.

        Args:
            db: Database session
            document_text: The generated document (HTML/text)
            document_type: Type of document (cv, letter, mail)

        Returns:
            {
                "document_type": "cv",
                "validated_claims": [ValidatedClaim, ...],
                "pass_count": int,
                "rewrite_count": int,
                "remove_count": int,
                "recommendation": "SAFE" | "REVIEW" | "REJECT",
                "summary": "Human-readable summary"
            }
        """
        # Load atomic profile blocks
        profile_blocks = db.query(ProfileBlock).all()
        if not profile_blocks:
            return {
                "document_type": document_type,
                "validated_claims": [],
                "pass_count": 0,
                "rewrite_count": 0,
                "remove_count": 0,
                "recommendation": "REJECT",
                "summary": "No profile blocks found. Cannot validate.",
            }

        # Parse CV into claims
        profile_context = QualityAgentV2._build_profile_context(profile_blocks)
        parsed_claims = await ClaimParserService.parse_cv_into_claims(
            document_text, profile_context
        )

        if not parsed_claims:
            logger.warning("No claims extracted from document")
            return {
                "document_type": document_type,
                "validated_claims": [],
                "pass_count": 0,
                "rewrite_count": 0,
                "remove_count": 0,
                "recommendation": "REVIEW",
                "summary": "Could not parse any claims from document. Manual review recommended.",
            }

        # Validate each claim
        validator = ClaimValidatorService(profile_blocks)
        validated_claims = []

        for parsed_claim in parsed_claims:
            validation = QualityAgentV2._validate_single_claim(
                parsed_claim, validator, profile_blocks
            )
            validated_claims.append(validation)

        # Aggregate results
        pass_count = sum(1 for c in validated_claims if c.action == ValidationAction.PASS)
        rewrite_count = sum(1 for c in validated_claims if c.action == ValidationAction.REWRITE)
        remove_count = sum(1 for c in validated_claims if c.action == ValidationAction.REMOVE)

        # Determine recommendation
        if remove_count > 0:
            recommendation = "REJECT"  # Has unjustified claims
        elif rewrite_count > len(validated_claims) * 0.3:
            recommendation = "REVIEW"  # >30% needs rewriting
        else:
            recommendation = "SAFE"  # Most claims pass

        summary = f"Validated {len(validated_claims)} claims: {pass_count} PASS, {rewrite_count} REWRITE, {remove_count} REMOVE. Recommendation: {recommendation}"

        return {
            "document_type": document_type,
            "validated_claims": validated_claims,
            "pass_count": pass_count,
            "rewrite_count": rewrite_count,
            "remove_count": remove_count,
            "recommendation": recommendation,
            "summary": summary,
        }

    @staticmethod
    def _validate_single_claim(
        parsed_claim: ParsedClaim,
        validator: ClaimValidatorService,
        profile_blocks: List[ProfileBlock],
    ) -> ValidatedClaim:
        """Validate a single parsed claim.

        Returns:
            ValidatedClaim with action and reason
        """
        claim_text = parsed_claim.text
        source_ref = parsed_claim.source_block_ref

        # If no source ref inferred, try to find it
        if not source_ref:
            # This is a claim the LLM couldn't confidently map
            # Try to map based on claim type
            source_ref = QualityAgentV2._find_source_block_for_claim(
                parsed_claim, profile_blocks
            )

        if not source_ref:
            # Could not map to any block
            return ValidatedClaim(
                original_text=claim_text,
                action=ValidationAction.REMOVE,
                reason="Could not map claim to any atomic profile block. No source of truth.",
                source_blocks=[],
            )

        # Validate based on claim type
        if parsed_claim.claim_type == "experience":
            validation = validator.validate_experience_claim(claim_text, source_ref)
        elif parsed_claim.claim_type == "metric":
            validation = validator.validate_metric_claim(claim_text, source_ref)
        elif parsed_claim.claim_type == "skill":
            validation = validator.validate_skill_claim(
                parsed_claim.technologies[0] if parsed_claim.technologies else "unknown",
                claimed_proficiency_level=None,  # TODO: parse from claim if present
                context_block_source_ref=source_ref,
            )
        elif parsed_claim.claim_type == "date":
            validation = validator.validate_date_claim(
                claimed_start_date=None,  # TODO: parse from claim
                claimed_end_date=None,  # TODO: parse from claim
                block_source_ref=source_ref,
            )
        else:
            # Default: experience validation
            validation = validator.validate_experience_claim(claim_text, source_ref)

        return ValidatedClaim(
            original_text=claim_text,
            action=validation.action,
            reason=validation.reason,
            source_blocks=validation.source_blocks,
            rewritten_text=validation.rewritten_claim,
        )

    @staticmethod
    def _find_source_block_for_claim(
        parsed_claim: ParsedClaim,
        profile_blocks: List[ProfileBlock],
    ) -> Optional[str]:
        """Heuristic: find source block for a claim with low confidence mapping.

        Uses naive matching on technologies, metrics, and claim text patterns.
        """
        # This is a fallback for LLM parsing failure
        # In production, should trigger semantic resolution in ClaimParserService

        # Check if any technologies match skill blocks
        if parsed_claim.technologies:
            for tech in parsed_claim.technologies:
                tech_ref = f"master_v3:skill_{tech.lower().replace(' ', '_')}"
                if any(b.source_ref == tech_ref for b in profile_blocks):
                    return tech_ref

        # Check if metrics match any blocks
        if parsed_claim.metrics:
            for block in profile_blocks:
                if block.metrics and parsed_claim.metrics in str(block.metrics):
                    return block.source_ref

        return None

    @staticmethod
    def _build_profile_context(profile_blocks: List[ProfileBlock]) -> str:
        """Build a human-readable context of atomic blocks for LLM reference.

        Used in ClaimParserService to help map claims.
        """
        context_lines = []

        # Group by category
        experiences = [b for b in profile_blocks if b.category.value == "experience"]
        projects = [b for b in profile_blocks if b.category.value == "project"]
        skills = [b for b in profile_blocks if b.category.value == "skill"]

        if experiences:
            context_lines.append("## EXPERIENCES")
            for exp in experiences:
                context_lines.append(f"- {exp.source_ref or exp.id}: {exp.title}")
                if exp.technologies:
                    context_lines.append(f"  Technologies: {', '.join(exp.technologies)}")

        if projects:
            context_lines.append("\n## PROJECTS")
            for proj in projects:
                context_lines.append(f"- {proj.source_ref or proj.id}: {proj.title}")
                if proj.metrics:
                    context_lines.append(f"  Metrics: {proj.metrics}")

        if skills:
            context_lines.append("\n## SKILLS")
            for skill in skills:
                level = f" (level: {skill.proficiency_level})" if skill.proficiency_level else ""
                context_lines.append(f"- {skill.source_ref or skill.id}: {skill.title}{level}")

        return "\n".join(context_lines)
