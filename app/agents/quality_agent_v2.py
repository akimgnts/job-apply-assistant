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
from app.agents.title_validator import TitleValidator

logger = logging.getLogger(__name__)


@dataclass
class ValidatedClaim:
    """A claim after validation."""

    original_text: str
    action: ValidationAction
    reason: str
    source_blocks: List[str]
    rewritten_text: Optional[str] = None  # If action is REWRITE


@dataclass
class AdaptationValidationResult:
    """Result of validating an adaptation JSON before rendering."""

    cleaned_adaptation: Dict  # Modified adaptation with removed/rewritten claims
    pass_count: int
    rewrite_count: int
    remove_count: int
    total_count: int
    removal_rate: float  # Percentage of claims removed
    recommendation: str  # "ACCEPT" | "REVIEW" | "REJECT"
    details: List[Dict]  # Per-claim validation results


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

    @staticmethod
    def _find_experience_blocks(experience_index: int, all_blocks: List[ProfileBlock]) -> List[str]:
        """Find all experience blocks for a given index.

        Returns list of source_refs for all experience blocks matching the index:
        0 → Sidel blocks (dashboard, automation, analytics, consolidation, etc)
        1 → MadeByAkim blocks
        2 → Vassard block
        """
        company_prefixes = {
            0: "master_v3:sidel_",
            1: "master_v3:madebyakim_",
            2: "master_v3:vassard_",
        }

        prefix = company_prefixes.get(experience_index)
        if not prefix:
            return []

        matching = [
            b.source_ref for b in all_blocks
            if b.source_ref and b.source_ref.startswith(prefix) and b.category.value == "experience"
        ]
        return matching

    @staticmethod
    def _find_best_source_block_for_bullet(
        bullet: str, candidate_blocks: List[str], all_blocks: List[ProfileBlock]
    ) -> Optional[str]:
        """Find best matching source block for a bullet claim.

        Strategy:
        1. Check which blocks contain technologies mentioned in bullet
        2. Check which blocks contain metrics mentioned in bullet
        3. Return first match, or fall back to first candidate

        Args:
            bullet: Claim text
            candidate_blocks: List of source_refs to check against
            all_blocks: All ProfileBlock objects for lookup

        Returns:
            Best matching source_ref, or first candidate, or None
        """
        if not candidate_blocks:
            return None

        blocks_by_ref = {b.source_ref: b for b in all_blocks if b.source_ref}

        bullet_lower = bullet.lower()

        # First pass: check for technology matches
        for source_ref in candidate_blocks:
            block = blocks_by_ref.get(source_ref)
            if block and block.technologies:
                for tech in block.technologies:
                    if tech.lower() in bullet_lower:
                        return source_ref

        # Second pass: check for metric matches
        for source_ref in candidate_blocks:
            block = blocks_by_ref.get(source_ref)
            if block and block.metrics:
                metrics_str = str(block.metrics).lower()
                if any(m.lower() in bullet_lower for m in metrics_str.split()):
                    return source_ref

        # Fallback: return first candidate
        return candidate_blocks[0] if candidate_blocks else None

    @staticmethod
    def validate_adaptation_claims(
        adaptation: Dict,
        db: Session,
        removal_threshold: float = 0.30,  # 30% threshold
    ) -> AdaptationValidationResult:
        """Validate adaptation JSON before rendering to HTML.

        Checks all claims (summary, experience bullets, project bullets) against
        atomic profile blocks. Applies PASS/REWRITE/REMOVE logic.

        If removal rate exceeds threshold, recommends REVIEW instead of ACCEPT.

        Args:
            adaptation: JSON from CVAdaptationAgent with title, summary, bullets
            db: Database session
            removal_threshold: Max removal rate (default 30%) before REVIEW recommendation

        Returns:
            AdaptationValidationResult with cleaned adaptation + stats
        """
        # Load ALL atomic blocks (not just selected ones)
        all_blocks = db.query(ProfileBlock).all()
        if not all_blocks:
            logger.warning("No profile blocks found for adaptation validation")
            return AdaptationValidationResult(
                cleaned_adaptation=adaptation,
                pass_count=0,
                rewrite_count=0,
                remove_count=0,
                total_count=0,
                removal_rate=0.0,
                recommendation="REJECT",
                details=[],
            )

        validator = ClaimValidatorService(all_blocks)
        details = []
        total_claims = 0
        pass_count = 0
        rewrite_count = 0
        remove_count = 0

        cleaned_adaptation = {
            "title": adaptation.get("title", ""),
            "summary": adaptation.get("summary", ""),
            "experience_order": adaptation.get("experience_order", []),
            "experience_bullets": {},
            "project_order": adaptation.get("project_order", []),
            "project_bullets": {},
            "ats_keywords": adaptation.get("ats_keywords", []),
        }

        # Validate title (factual consistency check)
        if adaptation.get("title"):
            total_claims += 1
            original_title = adaptation["title"]
            is_valid, rewritten_title = TitleValidator.validate_title(
                original_title,
                positioning=None  # positioning not passed to this method, but OK for generic validation
            )
            if is_valid:
                action = ValidationAction.PASS
                reason = "Title is factually supported"
                pass_count += 1
                cleaned_title = original_title
            else:
                action = ValidationAction.REWRITE
                reason = f"Title contains unsupported domain/seniority. Rewritten to factually supported title."
                rewrite_count += 1
                cleaned_title = rewritten_title

            details.append({
                "type": "title",
                "original": original_title,
                "action": action.value,
                "reason": reason,
            })
            cleaned_adaptation["title"] = cleaned_title

        # Validate summary (as experience claim)
        if adaptation.get("summary"):
            total_claims += 1
            summary_claim = adaptation["summary"]
            # Validate as a general claim (no specific block context)
            # This is simplified—summary usually passes unless obviously false
            validation = validator.validate_experience_claim(
                summary_claim,
                "master_v3:sidel_experience"  # Use primary block context
            )
            details.append({
                "type": "summary",
                "original": summary_claim,
                "action": validation.action.value,
                "reason": validation.reason,
            })
            if validation.action == ValidationAction.PASS:
                pass_count += 1
            elif validation.action == ValidationAction.REWRITE:
                rewrite_count += 1
                cleaned_adaptation["summary"] = validation.rewritten_claim or summary_claim
            elif validation.action == ValidationAction.REMOVE:
                remove_count += 1
                cleaned_adaptation["summary"] = ""

        # Validate experience bullets
        for exp_str, bullets in adaptation.get("experience_bullets", {}).items():
            try:
                exp_index = int(exp_str)
            except ValueError:
                continue

            # Find all candidate blocks for this experience index
            candidate_blocks = QualityAgentV2._find_experience_blocks(exp_index, all_blocks)
            if not candidate_blocks:
                logger.warning(f"No candidate blocks for experience index {exp_index}")
                cleaned_adaptation["experience_bullets"][exp_str] = bullets
                continue

            cleaned_bullets = []
            for bullet in bullets:
                total_claims += 1

                # Find best source block for this specific bullet
                source_ref = QualityAgentV2._find_best_source_block_for_bullet(
                    bullet, candidate_blocks, all_blocks
                )

                validation = validator.validate_experience_claim(bullet, source_ref)

                details.append({
                    "type": "experience",
                    "index": exp_index,
                    "original": bullet,
                    "action": validation.action.value,
                    "reason": validation.reason,
                    "source_block": source_ref,
                })

                if validation.action == ValidationAction.PASS:
                    pass_count += 1
                    cleaned_bullets.append(bullet)
                elif validation.action == ValidationAction.REWRITE:
                    rewrite_count += 1
                    cleaned_bullets.append(validation.rewritten_claim or bullet)
                elif validation.action == ValidationAction.REMOVE:
                    remove_count += 1
                    # Don't add to cleaned_bullets (removes the claim)

            cleaned_adaptation["experience_bullets"][exp_str] = cleaned_bullets

        # Validate project bullets (fixed project mapping)
        project_mapping = {
            0: ["master_v3:elevia_platform", "master_v3:elevia_matching_engine", "master_v3:elevia_document_generation", "master_v3:elevia_architecture"],
            1: ["master_v3:job_apply_assistant"],
            2: ["master_v3:vie_matcher"],
        }

        for proj_str, bullets in adaptation.get("project_bullets", {}).items():
            try:
                proj_index = int(proj_str)
            except ValueError:
                continue

            candidate_blocks = project_mapping.get(proj_index, [])
            if not candidate_blocks:
                logger.warning(f"No candidate blocks for project index {proj_index}")
                cleaned_adaptation["project_bullets"][proj_str] = bullets
                continue

            cleaned_bullets = []
            for bullet in bullets:
                total_claims += 1

                # Find best source block for this specific bullet
                source_ref = QualityAgentV2._find_best_source_block_for_bullet(
                    bullet, candidate_blocks, all_blocks
                )

                validation = validator.validate_experience_claim(bullet, source_ref)

                details.append({
                    "type": "project",
                    "index": proj_index,
                    "original": bullet,
                    "action": validation.action.value,
                    "reason": validation.reason,
                    "source_block": source_ref,
                })

                if validation.action == ValidationAction.PASS:
                    pass_count += 1
                    cleaned_bullets.append(bullet)
                elif validation.action == ValidationAction.REWRITE:
                    rewrite_count += 1
                    cleaned_bullets.append(validation.rewritten_claim or bullet)
                elif validation.action == ValidationAction.REMOVE:
                    remove_count += 1
                    # Don't add to cleaned_bullets (removes the claim)

            cleaned_adaptation["project_bullets"][proj_str] = cleaned_bullets

        # Determine recommendation
        removal_rate = remove_count / total_claims if total_claims > 0 else 0.0
        if remove_count > 0:
            recommendation = "REVIEW"  # Has removals = needs review
        elif removal_rate > removal_threshold:
            recommendation = "REVIEW"  # Too many removals
        else:
            recommendation = "ACCEPT"  # Safe to render

        logger.info(
            f"Adaptation validation complete: pass={pass_count}, rewrite={rewrite_count}, "
            f"remove={remove_count}, total={total_claims}, removal_rate={removal_rate:.1%}, "
            f"recommendation={recommendation}"
        )

        return AdaptationValidationResult(
            cleaned_adaptation=cleaned_adaptation,
            pass_count=pass_count,
            rewrite_count=rewrite_count,
            remove_count=remove_count,
            total_count=total_claims,
            removal_rate=removal_rate,
            recommendation=recommendation,
            details=details,
        )
