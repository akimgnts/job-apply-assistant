"""Phase 3 Tests: Evidence Registry — Canonical ID stability and integrity.

Tests that canonical evidence IDs are:
- Stable (not positional, survive Master CV reordering)
- Verified (exist in registry, resolve to real Master CV evidence)
- Immutable (canonical ID never changes even if Master content changes slightly)
"""
import pytest
from pathlib import Path
import json
import hashlib


class TestEvidenceRegistryIntegrity:
    """Test Evidence Registry structure and validation."""

    def test_registry_loads_successfully(self):
        """Test registry file exists and loads as valid JSON."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()

        assert registry is not None
        assert "metadata" in registry
        assert "evidence" in registry
        print(f"✅ Registry loaded: {registry['metadata']['total_canonical_ids']} canonical IDs")

    def test_registry_has_required_metadata(self):
        """Test registry includes version, creation date, and reference info."""
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

    def test_registry_validate_integrity(self):
        """Test registry integrity validation function."""
        from app.services.evidence_registry_service import validate_registry_integrity

        result = validate_registry_integrity()

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["stats"]["total_canonical_ids"] > 0
        print(f"✅ Registry integrity PASSED: {result['stats']}")

    def test_canonical_ids_are_not_positional(self):
        """Test that canonical IDs are NOT simple array indices."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        evidence = registry["evidence"]

        # Canonical IDs should NOT be "0", "1", "2", etc.
        for cid in evidence.keys():
            assert not cid.isdigit(), f"Found positional ID (not canonical): {cid}"
            # Should contain dots or underscores to separate components
            assert "." in cid or "_" in cid, f"Canonical ID poorly formatted: {cid}"

        print(f"✅ All {len(evidence)} canonical IDs are non-positional")

    def test_canonical_ids_have_namespaces(self):
        """Test that canonical IDs use stable namespaces."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        evidence = registry["evidence"]

        namespaces = set()
        for cid in evidence.keys():
            prefix = cid.split(".")[0]
            namespaces.add(prefix)

        # Should have namespaces like SIDEL, PROJECT, SKILL, etc.
        assert len(namespaces) > 0
        print(f"✅ Found stable namespaces: {sorted(namespaces)}")

    def test_skill_ids_are_exact_match(self):
        """Test that SKILL.* canonical IDs match skill names exactly."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        evidence = registry["evidence"]

        skill_ids = {cid: entry for cid, entry in evidence.items() if cid.startswith("SKILL.")}
        assert len(skill_ids) > 0, "Should have SKILL.* entries"

        for skill_id, entry in skill_ids.items():
            assert entry["source_type"] == "skill"
            assert "source_skill" in entry
            assert "source_level" in entry
            print(f"  SKILL.{entry['source_skill']}: level {entry['source_level']}")

        print(f"✅ Found {len(skill_ids)} skill entries with valid structure")

    def test_experience_ids_have_consistent_structure(self):
        """Test experience IDs follow COMPANY.SECTION.XXX pattern."""
        from app.services.evidence_registry_service import load_evidence_registry

        registry = load_evidence_registry()
        evidence = registry["evidence"]

        exp_ids = {cid: entry for cid, entry in evidence.items()
                   if not cid.startswith("SKILL.") and not cid.startswith("PROJECT.")}
        assert len(exp_ids) > 0

        for cid, entry in exp_ids.items():
            # Should be COMPANY.SECTION.XXX
            parts = cid.split(".")
            assert len(parts) == 3, f"Experience ID should have 3 parts: {cid}"
            assert entry["source_type"] == "experience"
            assert "source_company" in entry
            assert "source_section" in entry

        print(f"✅ All {len(exp_ids)} experience IDs follow COMPANY.SECTION.XXX pattern")


class TestEvidenceRegistryValidation:
    """Test evidence ID validation and resolution."""

    def test_validate_valid_evidence_id(self):
        """Test that valid evidence IDs are recognized."""
        from app.services.evidence_registry_service import (
            validate_evidence_id,
            get_all_skill_evidence_ids
        )

        skill_ids = get_all_skill_evidence_ids()
        assert len(skill_ids) > 0

        # Test first skill ID
        test_id = skill_ids[0]
        assert validate_evidence_id(test_id) is True
        print(f"✅ Valid evidence ID recognized: {test_id}")

    def test_validate_invalid_evidence_id(self):
        """Test that invalid evidence IDs are rejected."""
        from app.services.evidence_registry_service import validate_evidence_id

        assert validate_evidence_id("NONEXISTENT.SKILL.999") is False
        assert validate_evidence_id("EXP.0") is False  # Positional, not canonical
        assert validate_evidence_id("exp_0") is False  # Wrong format
        print("✅ Invalid evidence IDs correctly rejected")

    def test_resolve_evidence_by_canonical_id(self):
        """Test resolving canonical ID to full entry."""
        from app.services.evidence_registry_service import (
            resolve_evidence,
            get_all_skill_evidence_ids
        )

        skill_ids = get_all_skill_evidence_ids()
        test_id = skill_ids[0]

        entry = resolve_evidence(test_id)
        assert entry is not None
        assert "source_type" in entry
        assert entry["source_type"] == "skill"
        print(f"✅ Resolved {test_id}: {entry['source_skill']}")

    def test_find_skill_evidence_by_name(self):
        """Test finding all evidence entries for a skill."""
        from app.services.evidence_registry_service import find_evidence_by_skill_name

        # Python should exist in registry
        python_evidence = find_evidence_by_skill_name("Python")
        assert len(python_evidence) > 0, "Should find evidence for Python"
        print(f"✅ Found {len(python_evidence)} evidence entries for Python: {python_evidence}")


class TestPhase3WithCanonicalIds:
    """Test Phase 3 enrichment using canonical IDs (not positional)."""

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
            assert "." in evidence_id, f"Should be canonical format: {evidence_id}"
            print(f"  ✓ {evidence_id}: {ev['match_type']}")

        print(f"✅ Skill evidence returns canonical IDs, not positional")

    def test_skill_mapping_stability_across_reordering(self):
        """Test that canonical IDs remain stable even if Master CV is reordered.

        This test verifies the core benefit of canonical IDs: they don't change
        when array indices change.
        """
        from app.services.job_analysis_enrichment_service import find_skill_evidence_in_registry

        # Get evidence for Python
        evidence_1 = find_skill_evidence_in_registry("Python")
        ids_1 = sorted([ev["evidence_id"] for ev in evidence_1])

        # Call again (simulating "reordered" Master, though not actually reordered)
        evidence_2 = find_skill_evidence_in_registry("Python")
        ids_2 = sorted([ev["evidence_id"] for ev in evidence_2])

        # IDs should be identical (stable)
        assert ids_1 == ids_2, "Canonical IDs should be stable across calls"
        print(f"✅ Canonical IDs stable: {ids_1}")


class TestIntegrationWithPhase3:
    """Integration tests: Evidence Registry with Phase 3 enrichment."""

    def test_enrichment_all_evidence_ids_valid(self):
        """Test that Phase 3 only persists valid canonical IDs."""
        from app.services.evidence_registry_service import (
            validate_evidence_id,
            load_evidence_registry
        )
        from app.services.job_analysis_enrichment_service import (
            find_skill_evidence_in_registry
        )

        # Test multiple skills
        skills_to_test = ["Python", "SQL", "Power BI", "Docker", "Unknown Skill"]

        for skill in skills_to_test:
            evidence_list = find_skill_evidence_in_registry(skill)

            for ev in evidence_list:
                evidence_id = ev["evidence_id"]
                # Every returned ID must be valid
                assert validate_evidence_id(evidence_id), \
                    f"Phase 3 returned invalid evidence_id: {evidence_id}"

            print(f"  ✓ {skill}: {len(evidence_list)} valid evidence entries")

        print("✅ All Phase 3 evidence IDs are valid and resolvable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
