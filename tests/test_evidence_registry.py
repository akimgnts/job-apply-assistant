"""Tests for Evidence Registry — Canonical Evidence ID validation and stability.

Ensures:
- Evidence Registry loads from production Master CV
- Canonical IDs are non-positional and stable
- All registry entries resolve correctly
- Phase 3 skill mapping uses canonical IDs (not exp_0, proj_1, etc.)
"""
import pytest


class TestEvidenceRegistryIntegrity:
    """Test Evidence Registry structure and production validity."""

    def test_registry_loads_successfully(self):
        """Test registry file exists and loads as valid JSON."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()

        assert registry is not None
        assert "metadata" in registry
        assert "evidence" in registry
        print(f"✅ Registry loaded: {registry['metadata']['total_canonical_ids']} canonical IDs")

    def test_registry_has_required_metadata(self):
        """Test registry includes version, creation date, and Master CV lock info."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        metadata = registry["metadata"]

        assert "version" in metadata
        assert "created_at" in metadata
        assert "master_cv_locked_date" in metadata
        assert "total_canonical_ids" in metadata
        assert metadata["total_canonical_ids"] > 0
        print(f"✅ Registry metadata valid: v{metadata['version']}, "
              f"{metadata['total_canonical_ids']} IDs, "
              f"locked to Master {metadata['master_cv_locked_date']}")

    def test_registry_canonical_ids_not_positional(self):
        """Test that canonical IDs are NOT simple array indices."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        evidence = registry["evidence"]

        # Canonical IDs should NOT be "0", "1", "2", etc.
        for cid in evidence.keys():
            assert not cid.isdigit(), f"Found positional ID (not canonical): {cid}"
            assert not cid.startswith("exp_"), f"Found positional ID: {cid}"
            assert not cid.startswith("proj_"), f"Found positional ID: {cid}"

        print(f"✅ All {len(evidence)} canonical IDs are non-positional")

    def test_production_master_cv_evidence_count(self):
        """Test registry contains evidence from all 3 production companies and 3 production projects."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        evidence = registry["evidence"]

        # Count by namespace
        sidel_count = sum(1 for cid in evidence if cid.startswith("SIDEL."))
        madebyakim_count = sum(1 for cid in evidence if cid.startswith("MADEBYAKIM_"))
        vassard_count = sum(1 for cid in evidence if cid.startswith("VASSARD_"))
        project_count = sum(1 for cid in evidence if cid.startswith("PROJECT."))
        skill_count = sum(1 for cid in evidence if cid.startswith("SKILL."))

        assert sidel_count > 0, "Should have Sidel experience entries"
        assert madebyakim_count > 0, "Should have MadeByAkim experience entries"
        assert vassard_count > 0, "Should have Vassard experience entries"
        assert project_count > 0, "Should have project entries"
        assert skill_count > 0, "Should have skill entries"

        print(f"✅ Registry entries by source:")
        print(f"   Sidel: {sidel_count}")
        print(f"   MadeByAkim: {madebyakim_count}")
        print(f"   Vassard: {vassard_count}")
        print(f"   Projects: {project_count}")
        print(f"   Skills: {skill_count}")


class TestEvidenceRegistryValidation:
    """Test evidence ID validation and resolution."""

    def test_validate_valid_evidence_id(self):
        """Test that valid evidence IDs from registry are recognized."""
        from app.services.evidence_registry_service import (
            validate_evidence_id,
            load_evidence_registry,
        )

        registry = load_evidence_registry()
        all_ids = list(registry["evidence"].keys())

        # Pick first ID and validate it
        test_id = all_ids[0]
        assert validate_evidence_id(test_id) is True
        print(f"✅ Valid evidence ID recognized: {test_id}")

    def test_validate_invalid_evidence_id(self):
        """Test that invalid evidence IDs are rejected."""
        from app.services.evidence_registry_service import validate_evidence_id

        assert validate_evidence_id("NONEXISTENT.SKILL.999") is False
        assert validate_evidence_id("exp_0") is False  # Positional, not canonical
        assert validate_evidence_id("proj_1") is False  # Positional, not canonical
        print("✅ Invalid evidence IDs correctly rejected")

    def test_resolve_evidence_by_canonical_id(self):
        """Test resolving canonical ID to full registry entry."""
        from app.services.evidence_registry_service import (
            resolve_evidence,
            load_evidence_registry,
        )

        registry = load_evidence_registry()
        test_id = list(registry["evidence"].keys())[0]

        entry = resolve_evidence(test_id)
        assert entry is not None
        assert "source_type" in entry
        print(f"✅ Resolved {test_id}: {entry.get('text', '')[:80]}...")


class TestPhase3CanonicalMapping:
    """Test Phase 3 skill mapping using canonical Evidence Registry."""

    def test_find_skill_evidence_returns_canonical_ids(self):
        """Test that Phase 3 skill search returns canonical IDs, not positional."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_registry

        # Test with a skill that should exist
        evidence = find_skill_evidence_in_registry("Python")

        # Should return canonical IDs, not exp_0/proj_0
        for ev in evidence:
            evidence_id = ev["evidence_id"]
            assert not evidence_id.startswith("exp_"), f"Should not be positional: {evidence_id}"
            assert not evidence_id.startswith("proj_"), f"Should not be positional: {evidence_id}"
            # Should be canonical: SKILL.*, SIDEL.*, PROJECT.*, etc.
            assert "." in evidence_id or "_" in evidence_id, f"Should be canonical format: {evidence_id}"
            print(f"  ✓ {evidence_id}: {ev['match_type']}")

        print(f"✅ Skill evidence returns canonical IDs, not positional")

    def test_skill_mapping_stability(self):
        """Test that canonical IDs are stable across multiple calls."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_registry

        # Get evidence for Python twice
        evidence_1 = find_skill_evidence_in_registry("Python")
        ids_1 = sorted([ev["evidence_id"] for ev in evidence_1])

        evidence_2 = find_skill_evidence_in_registry("Python")
        ids_2 = sorted([ev["evidence_id"] for ev in evidence_2])

        # IDs should be identical (stable)
        assert ids_1 == ids_2, "Canonical IDs should be stable across calls"
        print(f"✅ Canonical IDs stable: {ids_1}")

    def test_unknown_skill_returns_gap(self):
        """Test that unknown skills return empty list (GAP)."""
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_registry

        # "Jira" should not be in Master CV
        evidence = find_skill_evidence_in_registry("Jira")

        assert evidence == [], "Unknown skill should return empty list (GAP)"
        print("✅ Unknown skill correctly returns empty list (GAP)")
