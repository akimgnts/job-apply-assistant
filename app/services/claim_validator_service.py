"""Deterministic claim validation against atomic profile blocks.

Rules:
1. Block-scoped technology: Can only use tech if source block authorizes it
2. Metric freezing: Cannot change frozen metrics from block
3. Proficiency claim: Cannot claim level > block.proficiency_level
4. Status claim: Cannot claim status incompatible with block.status
5. No generic skill justification: "Skill X exists globally" ≠ "Used X in experience Y"

Actions:
- PASS: Claim is valid and justified
- REWRITE: Claim is recoverable with corrected metrics/wording
- REMOVE: Claim is unjustifiable or false
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from app.database.models import ProfileBlock, BlockStatusEnum, ProficiencyLevelEnum


class ValidationAction(str, Enum):
    PASS = "pass"
    REWRITE = "rewrite"
    REMOVE = "remove"


@dataclass
class ClaimValidation:
    action: ValidationAction
    reason: str
    source_blocks: List[str]  # Block IDs/source_refs that justify this
    rewritten_claim: Optional[str] = None  # If action is REWRITE


class ClaimValidatorService:
    """Deterministic validation of CV claims against atomic profile blocks."""

    def __init__(self, profile_blocks: List[ProfileBlock]):
        """Initialize with loaded profile blocks.

        Args:
            profile_blocks: List of atomic ProfileBlock objects
        """
        self.blocks = {b.id: b for b in profile_blocks}
        self.blocks_by_source_ref = {}
        for block in profile_blocks:
            if block.source_ref:
                self.blocks_by_source_ref[block.source_ref] = block

    def validate_experience_claim(
        self,
        claim: str,
        experience_block_source_ref: str,
    ) -> ClaimValidation:
        """Validate a claim made within a specific experience block.

        Core rule: Cannot use technology/skill unless the experience block authorizes it.

        Args:
            claim: The CV claim text (e.g., "Built dashboards using Power BI")
            experience_block_source_ref: source_ref of the experience block (e.g., "master_v3:sidel_reporting_automation")

        Returns:
            ClaimValidation with action and reason
        """
        # Find source experience block
        exp_block = self.blocks_by_source_ref.get(experience_block_source_ref)
        if not exp_block:
            return ClaimValidation(
                action=ValidationAction.REMOVE,
                reason=f"Experience block {experience_block_source_ref} not found in profile",
                source_blocks=[],
            )

        # Extract technologies from claim (naive extraction — will be enhanced by semantic parser)
        claim_technologies = self._extract_technologies_from_claim(claim)

        # Check: all claimed technologies must be in experience block's technologies
        if claim_technologies:
            unauthorized_techs = [
                tech
                for tech in claim_technologies
                if tech not in (exp_block.technologies or [])
            ]
            if unauthorized_techs:
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Technologies {unauthorized_techs} not authorized in {experience_block_source_ref}. "
                    f"Authorized: {exp_block.technologies}",
                    source_blocks=[experience_block_source_ref],
                )

        # Check: forbidden claims
        if exp_block.forbidden_claims:
            violation = self._check_forbidden_claims(claim, exp_block.forbidden_claims)
            if violation:
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Claim violates block's forbidden claim: {violation}",
                    source_blocks=[experience_block_source_ref],
                )

        # Check: status-incompatible claims
        status_issue = self._check_status_claim_compatibility(claim, exp_block.status)
        if status_issue:
            return ClaimValidation(
                action=ValidationAction.REMOVE,
                reason=status_issue,
                source_blocks=[experience_block_source_ref],
            )

        # Passed all checks
        return ClaimValidation(
            action=ValidationAction.PASS,
            reason="Claim is authorized by experience block and does not violate constraints",
            source_blocks=[experience_block_source_ref],
        )

    def validate_metric_claim(
        self,
        claimed_metric: str,
        block_source_ref: str,
    ) -> ClaimValidation:
        """Validate a specific metric claim against block's frozen metrics.

        Args:
            claimed_metric: The metric as stated in CV (e.g., "30–40 stakeholders")
            block_source_ref: source_ref of the ProfileBlock

        Returns:
            ClaimValidation
        """
        block = self.blocks_by_source_ref.get(block_source_ref)
        if not block:
            return ClaimValidation(
                action=ValidationAction.REMOVE,
                reason=f"Block {block_source_ref} not found",
                source_blocks=[],
            )

        if not block.metrics:
            return ClaimValidation(
                action=ValidationAction.PASS,
                reason="Block has no frozen metrics",
                source_blocks=[block_source_ref],
            )

        # Extract metric values from claim (naive — enhanced by semantic parser)
        claimed_value = self._extract_metric_value(claimed_metric)
        if not claimed_value:
            return ClaimValidation(
                action=ValidationAction.PASS,
                reason="Could not extract metric value from claim — passing for semantic review",
                source_blocks=[block_source_ref],
            )

        # Check: claimed metric matches frozen block metric
        block_metric_str = str(block.metrics)
        if claimed_value not in block_metric_str:
            return ClaimValidation(
                action=ValidationAction.REMOVE,
                reason=f"Claimed metric '{claimed_value}' not found in block's frozen metrics: {block.metrics}",
                source_blocks=[block_source_ref],
            )

        return ClaimValidation(
            action=ValidationAction.PASS,
            reason="Metric matches frozen block value",
            source_blocks=[block_source_ref],
        )

    def validate_skill_claim(
        self,
        skill_name: str,
        claimed_proficiency_level: Optional[int] = None,
        context_block_source_ref: Optional[str] = None,
    ) -> ClaimValidation:
        """Validate a skill claim (with optional context block).

        Rules:
        - If context_block_source_ref given: skill must be in that block's technologies
        - If proficiency claimed: cannot exceed block's proficiency_level

        Args:
            skill_name: Name of the skill (e.g., "Power BI", "Python")
            claimed_proficiency_level: Optional proficiency level claim (0-3)
            context_block_source_ref: Optional source_ref of experience block using this skill

        Returns:
            ClaimValidation
        """
        # Find skill block
        skill_block_ref = f"master_v3:skill_{skill_name.lower().replace(' ', '_')}"
        skill_block = self.blocks_by_source_ref.get(skill_block_ref)

        if not skill_block:
            return ClaimValidation(
                action=ValidationAction.REMOVE,
                reason=f"Skill block {skill_block_ref} not found in profile",
                source_blocks=[],
            )

        # If context block given: check authorization
        if context_block_source_ref:
            context_block = self.blocks_by_source_ref.get(context_block_source_ref)
            if not context_block:
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Context block {context_block_source_ref} not found",
                    source_blocks=[],
                )

            if skill_name not in (context_block.technologies or []):
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Skill '{skill_name}' not authorized in {context_block_source_ref}. "
                    f"Authorized: {context_block.technologies}",
                    source_blocks=[context_block_source_ref],
                )

        # Check: proficiency level claim
        if claimed_proficiency_level is not None:
            if skill_block.proficiency_level is None:
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Cannot claim proficiency level for {skill_name} — block has no level",
                    source_blocks=[skill_block_ref],
                )

            if claimed_proficiency_level > skill_block.proficiency_level:
                level_names = {0: "learning", 1: "beginner", 2: "intermediate", 3: "expert"}
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Claimed level {level_names.get(claimed_proficiency_level, claimed_proficiency_level)} "
                    f"exceeds block's {level_names.get(skill_block.proficiency_level, skill_block.proficiency_level)}",
                    source_blocks=[skill_block_ref],
                )

        return ClaimValidation(
            action=ValidationAction.PASS,
            reason=f"Skill {skill_name} is valid and authorized",
            source_blocks=[skill_block_ref],
        )

    def validate_date_claim(
        self,
        claimed_start_date: Optional[str],
        claimed_end_date: Optional[str],
        block_source_ref: str,
    ) -> ClaimValidation:
        """Validate date claims against block's frozen dates.

        Args:
            claimed_start_date: Start date as claimed (e.g., "2023")
            claimed_end_date: End date as claimed (e.g., "2025")
            block_source_ref: source_ref of the block with frozen dates

        Returns:
            ClaimValidation
        """
        block = self.blocks_by_source_ref.get(block_source_ref)
        if not block:
            return ClaimValidation(
                action=ValidationAction.REMOVE,
                reason=f"Block {block_source_ref} not found",
                source_blocks=[],
            )

        # Check: dates match block's dates
        if claimed_start_date and block.start_date:
            if claimed_start_date not in block.start_date:
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Claimed start date {claimed_start_date} not in block's {block.start_date}",
                    source_blocks=[block_source_ref],
                )

        if claimed_end_date and block.end_date:
            if claimed_end_date not in block.end_date:
                return ClaimValidation(
                    action=ValidationAction.REMOVE,
                    reason=f"Claimed end date {claimed_end_date} not in block's {block.end_date}",
                    source_blocks=[block_source_ref],
                )

        return ClaimValidation(
            action=ValidationAction.PASS,
            reason="Dates match block's frozen dates",
            source_blocks=[block_source_ref],
        )

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _extract_technologies_from_claim(self, claim: str) -> List[str]:
        """Naive extraction of technology names from claim text.

        This is a fallback for cases where semantic parsing hasn't identified them.
        Enhanced by LLM-based semantic parser for ambiguous claims.
        """
        # Known technologies from seed
        known_techs = {
            "Python", "SQL", "Power BI", "Power Query", "Excel", "Pandas",
            "Make", "n8n", "REST APIs", "Webhooks", "JSON", "Google Apps Script",
            "Telegram", "OpenAI", "Claude", "Gemini", "LangChain",
            "PostgreSQL", "FastAPI", "SQLAlchemy", "Jinja2", "Git", "GitHub", "Docker",
            "HubSpot", "Microsoft Dynamics", "Notion", "Airtable", "Google Sheets",
            "Adobe Premiere Pro", "Adobe After Effects", "Photoshop", "Illustrator", "Canva",
        }

        found = [tech for tech in known_techs if tech.lower() in claim.lower()]
        return found

    def _extract_metric_value(self, claim: str) -> Optional[str]:
        """Extract numeric or comparative metric from claim.

        Examples:
        - "30–40 stakeholders" → "30–40"
        - "~10 dashboards" → "~10"
        - "100+ documents" → "100+"
        """
        import re

        # Try to find patterns like "30–40", "~10", "100+", etc.
        patterns = [
            r"\d+–\d+",  # 30–40
            r"~\d+",  # ~10
            r"\d+\+",  # 100+
            r"\d+",  # plain number
        ]

        for pattern in patterns:
            match = re.search(pattern, claim)
            if match:
                return match.group(0)

        return None

    def _check_forbidden_claims(self, claim: str, forbidden: List[str]) -> Optional[str]:
        """Check if claim violates any forbidden claim.

        Returns:
            Violated forbidden claim text, or None if all OK
        """
        if not forbidden:
            return None

        claim_lower = claim.lower()
        for forbidden_claim in forbidden:
            # Extract the core prohibition (e.g., "Do not claim X" → "X")
            if "do not claim" in forbidden_claim.lower():
                # Simple heuristic: check if prohibited word/phrase is in claim
                # This is naive and will be enhanced by semantic parsing
                prohibited = forbidden_claim.lower().replace("do not claim ", "")
                if prohibited in claim_lower:
                    return forbidden_claim

        return None

    def _check_status_claim_compatibility(
        self,
        claim: str,
        block_status: Optional[BlockStatusEnum],
    ) -> Optional[str]:
        """Check if claim's implied status is compatible with block's status.

        Returns:
            Error message if incompatible, None if OK
        """
        if not block_status:
            return None

        claim_lower = claim.lower()

        # Status incompatibilities
        if block_status == BlockStatusEnum.exploratory:
            deployed_words = ["deployed", "production", "shipped", "released", "live"]
            if any(word in claim_lower for word in deployed_words):
                return f"Claim implies 'deployed' but block status is 'exploratory'"

        if block_status == BlockStatusEnum.not_deployed:
            deployed_words = ["deployed", "production", "shipped"]
            if any(word in claim_lower for word in deployed_words):
                return f"Claim implies 'deployed' but block status is 'not_deployed'"

        if block_status == BlockStatusEnum.in_progress:
            completed_words = ["completed", "finished", "done"]
            if any(word in claim_lower for word in completed_words):
                return f"Claim implies 'completed' but block status is 'in_progress'"

        return None
