"""Phase 6: Validate message against Master CV evidence."""

import re
from app.services.evidence_registry_service import load_evidence_registry
import logging

logger = logging.getLogger(__name__)


class GroundingValidator:
    @staticmethod
    def validate(message: str, evidence_ids_used: list[str], gap_skills: list[str]) -> dict:
        """Validate message against evidence and gaps.

        Returns {grounded: bool, unsupported_claims: [], evidence_ids_valid: bool}
        """
        unsupported = []
        registry = load_evidence_registry()

        # Validate evidence IDs
        for eid in evidence_ids_used:
            if eid not in registry:
                unsupported.append(f"Invalid evidence ID: {eid}")

        # Check for fabricated patterns
        suspicious = [
            (r"led \d+ person teams?", "Invented team size"),
            (r"managed \d+ people", "Invented direct reports"),
            (r"\d+ years? (of )?(machine learning|ml|ai|automation)", "Unverified ML/AI years"),
            (r"built .{20,100} (system|platform|product)", "Likely invented project"),
        ]

        for pattern, desc in suspicious:
            if re.search(pattern, message, re.IGNORECASE):
                unsupported.append(f"{desc} in message")

        # Check for GAP skills mentioned as capabilities
        for gap_skill in gap_skills:
            # Look for statements like "I have X" or "proficient in X" for gap skills
            if re.search(rf"(proficient|expert|skilled|experienced|advanced) .{0,10}\b{gap_skill}\b", message, re.IGNORECASE):
                unsupported.append(f"GAP skill '{gap_skill}' mentioned as current capability")

        return {
            "grounded": len(unsupported) == 0,
            "unsupported_claims": unsupported,
            "evidence_ids_valid": all(eid in registry for eid in evidence_ids_used),
        }
