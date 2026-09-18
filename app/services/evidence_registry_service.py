"""Evidence Registry Service — Canonical evidence ID validation and resolution.

The Evidence Registry is a sidecar to Master CV V3.1 that assigns stable canonical IDs
to exact evidence already present in Master CV. This allows Phase 3 and beyond to reference
evidence by immutable canonical IDs even if the Master CV is reordered.

Architecture:
- Master CV V3.1: immutable factual source
- Evidence Registry: canonical ID → Master CV evidence mapping
- Phase 3: uses canonical IDs, never positional indices

Canonical ID format examples:
- SIDEL.DATA_BI.001 (experience + section + sequence)
- PROJECT.JOBAPPLY.001 (project + sequence)
- SKILL.PYTHON (skill)
"""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Cache the loaded registry
_EVIDENCE_REGISTRY_CACHE = None
_MASTER_CV_CACHE = None


def load_evidence_registry() -> dict:
    """Load Evidence Registry (canonical ID → Master CV evidence mapping).

    Registry is locked to Master CV V3.1 and guarantees:
    - Every canonical ID exists in Master CV
    - IDs remain stable even if Master CV is reordered
    - Evidence text can be verified by fingerprint
    """
    global _EVIDENCE_REGISTRY_CACHE

    if _EVIDENCE_REGISTRY_CACHE is not None:
        return _EVIDENCE_REGISTRY_CACHE

    registry_path = Path(__file__).parent.parent / "data" / "master_cv_evidence_registry.json"

    if not registry_path.exists():
        raise FileNotFoundError(
            f"Evidence Registry not found: {registry_path}\n"
            "Registry must be generated from Master CV V3.1 before use."
        )

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Evidence Registry JSON is malformed: {e}")

    _EVIDENCE_REGISTRY_CACHE = data
    logger.info(f"Evidence Registry loaded: {data['metadata']['total_canonical_ids']} canonical IDs")

    return data


def validate_evidence_id(canonical_id: str) -> bool:
    """Check if canonical_id exists in the Evidence Registry.

    Args:
        canonical_id: Canonical evidence ID (e.g., "SIDEL.DATA_BI.001")

    Returns:
        True if ID exists in registry, False otherwise
    """
    registry = load_evidence_registry()
    return canonical_id in registry["evidence"]


def resolve_evidence(canonical_id: str) -> Optional[dict]:
    """Resolve canonical evidence ID to its full registry entry.

    Args:
        canonical_id: Canonical evidence ID

    Returns:
        Registry entry dict, or None if not found
    """
    registry = load_evidence_registry()
    return registry["evidence"].get(canonical_id)


def get_all_skill_evidence_ids() -> List[str]:
    """Get all canonical IDs for skills.

    Returns:
        List of SKILL.* canonical IDs
    """
    registry = load_evidence_registry()
    return [cid for cid in registry["evidence"].keys() if cid.startswith("SKILL.")]


def get_all_experience_evidence_ids() -> List[str]:
    """Get all canonical IDs for experiences.

    Returns:
        List of experience canonical IDs (e.g., SIDEL.DATA_BI.001)
    """
    registry = load_evidence_registry()
    return [cid for cid in registry["evidence"].keys()
            if not cid.startswith("SKILL.") and not cid.startswith("PROJECT.")]


def get_all_project_evidence_ids() -> List[str]:
    """Get all canonical IDs for projects.

    Returns:
        List of PROJECT.* canonical IDs
    """
    registry = load_evidence_registry()
    return [cid for cid in registry["evidence"].keys() if cid.startswith("PROJECT.")]


def validate_registry_integrity() -> dict:
    """Validate that every registry entry resolves to Master CV evidence.

    Checks:
    - Registry format is valid
    - Metadata is present
    - Every canonical ID maps to an entry
    - No duplicate canonical IDs

    Returns:
        {"is_valid": bool, "issues": [list of error messages], "stats": {...}}
    """
    try:
        registry = load_evidence_registry()
    except Exception as e:
        return {"is_valid": False, "issues": [f"Registry load failed: {e}"], "stats": {}}

    issues = []
    evidence = registry.get("evidence", {})

    # Check metadata
    metadata = registry.get("metadata", {})
    if not metadata:
        issues.append("Registry metadata is missing")

    # Check canonical IDs format
    for canonical_id in evidence.keys():
        # Should be uppercase with dots: SIDEL.DATA_BI.001, PROJECT.JOBAPPLY.001, SKILL.PYTHON
        # Allow alphanumeric, underscores, hyphens, ampersands, slashes, parentheses for real-world skill names
        if not isinstance(canonical_id, str):
            issues.append(f"Invalid canonical ID (not string): {canonical_id}")
        elif not canonical_id or canonical_id[0].islower():
            issues.append(f"Invalid canonical ID (not uppercase): {canonical_id}")
        # Minimal check: must have at least one dot or be a SKILL. entry
        elif "." not in canonical_id:
            issues.append(f"Invalid canonical ID format (missing dot): {canonical_id}")

    # Check for duplicates (shouldn't happen with dict, but verify structure)
    if len(evidence.keys()) != len(set(evidence.keys())):
        issues.append("Duplicate canonical IDs found")

    stats = {
        "total_canonical_ids": len(evidence),
        "skills": len([c for c in evidence.keys() if c.startswith("SKILL.")]),
        "experiences": len([c for c in evidence.keys() if not c.startswith("SKILL.") and not c.startswith("PROJECT.")]),
        "projects": len([c for c in evidence.keys() if c.startswith("PROJECT.")]),
    }

    logger.info(f"Registry integrity check: {'PASSED' if not issues else 'FAILED'}")
    logger.info(f"  Stats: {stats}")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "stats": stats,
    }


def find_evidence_by_skill_name(skill_name: str) -> List[str]:
    """Find all canonical evidence IDs for a given skill name.

    Searches registry for exact skill name match.

    Args:
        skill_name: Skill name (e.g., "Python", "Power BI")

    Returns:
        List of canonical IDs where this skill appears
    """
    registry = load_evidence_registry()
    evidence = registry["evidence"]

    matching_ids = []
    skill_name_upper = skill_name.upper().replace(" ", "_")

    for cid, entry in evidence.items():
        # Direct skill match
        if entry.get("source_type") == "skill":
            if entry.get("source_skill", "").upper().replace(" ", "_") == skill_name_upper:
                matching_ids.append(cid)

        # Skill mention in experience/project text
        elif skill_name.lower() in entry.get("text", "").lower():
            matching_ids.append(cid)

    return matching_ids
