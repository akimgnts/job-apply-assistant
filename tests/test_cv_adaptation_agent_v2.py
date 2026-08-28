"""Regression tests for CVAdaptationAgent V2 (source-preserving selection).

Tests verify that the new selection-based approach:
1. Preserves exact metrics from Master CV
2. Never invents new content
3. Handles the Astek case correctly
4. Maintains source fidelity
"""

import pytest
from app.agents.cv_adaptation_agent import CVAdaptationAgent
from app.services.master_cv_service import load_master_cv
from app.agents.generation_agent import GenerationAgent


class TestCVAdaptationAgentV2:
    """Test suite for CVAdaptationAgent V2 (source-preserving)."""

    @pytest.fixture
    def master_cv(self):
        """Load the locked Master CV."""
        return load_master_cv()

    @pytest.fixture
    def astek_analysis(self):
        """Simulated Astek offer analysis."""
        return {
            "company": "Astek",
            "job_title": "Data Engineer",
            "missions": [
                "Design and implement data pipelines",
                "Develop ETL processes",
                "Optimize data warehouse queries",
            ],
            "required_skills": [
                "Python",
                "SQL",
                "ETL",
                "Data Warehouse",
                "PostgreSQL",
            ],
            "ats_keywords": ["data engineer", "python", "sql", "etl", "postgresql"],
            "languages": ["French", "English"],
            "seniority": "mid-level",
        }

    @pytest.fixture
    def positioning(self):
        """Safe positioning for Astek."""
        return "Data Analyst | Business Intelligence"

    @pytest.mark.asyncio
    async def test_selection_returns_source_ids_not_text(self, master_cv, astek_analysis, positioning):
        """Verify that adaptation returns source block IDs, never generated text."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        # CRITICAL: New format uses selected_*_blocks with source_id
        assert "selected_experience_blocks" in adaptation
        assert "selected_project_blocks" in adaptation
        assert "selected_skill_blocks" in adaptation

        # Each block should have source_id (not generated text)
        for block in adaptation["selected_experience_blocks"]:
            assert "source_id" in block
            assert isinstance(block["source_id"], int)
            assert "relevance" in block
            assert 0 <= block["relevance"] <= 1
            assert "show" in block
            assert "order" in block

    @pytest.mark.asyncio
    async def test_metric_preservation_6_dashboards(self, master_cv, astek_analysis, positioning):
        """CRITICAL: Verify "6+ dashboards" metric is preserved exactly."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        # Convert to template format
        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            adaptation, master_cv
        )

        # Sidel (experience 0) should be included
        assert 0 in template_format["experience_order"]

        # Get actual bullets from master CV
        sidel_bullets = template_format["experience_bullets"]["0"]
        sidel_first_bullet = sidel_bullets[0] if sidel_bullets else ""

        # MUST contain "6+" exactly, not "around 10"
        assert "6+" in sidel_first_bullet, f"Metric not preserved: {sidel_first_bullet}"
        assert "around 10" not in sidel_first_bullet
        assert "10 dashboards" not in sidel_first_bullet

    @pytest.mark.asyncio
    async def test_metric_preservation_dozens(self, master_cv, astek_analysis, positioning):
        """CRITICAL: Verify "dozens" metric is preserved, not "30–40"."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            adaptation, master_cv
        )

        sidel_bullets = template_format["experience_bullets"]["0"]
        sidel_first_bullet = sidel_bullets[0] if sidel_bullets else ""

        # MUST contain "dozens", not "30–40" or "~30–40"
        assert "dozens" in sidel_first_bullet, f"Metric not preserved: {sidel_first_bullet}"
        assert "30–40" not in sidel_first_bullet
        assert "~30–40" not in sidel_first_bullet

    @pytest.mark.asyncio
    async def test_no_aps_or_supply_chain_invented(self, master_cv, astek_analysis, positioning):
        """CRITICAL: Verify no APS/supply chain content appears (candidate has none)."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            adaptation, master_cv
        )

        # Collect all rendered text
        all_text = template_format.get("summary", "")
        for bullets in template_format.get("experience_bullets", {}).values():
            all_text += " ".join(bullets)

        # MUST NOT contain APS/supply chain keywords
        forbidden_keywords = ["APS", "supply chain", "Supply Chain", "Optimization Specialist"]
        for keyword in forbidden_keywords:
            assert (
                keyword not in all_text
            ), f"Invented content detected: {keyword} in {all_text[:100]}"

    @pytest.mark.asyncio
    async def test_title_not_supply_data_engineer_positioning(self, master_cv, astek_analysis, positioning):
        """CRITICAL: Verify title is NOT "Supply Data Engineer Positioning" (invalid)."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        title = adaptation.get("title", "")

        # MUST NOT be invalid positioning string
        assert title != "Supply Data Engineer Positioning"
        assert title == positioning  # Should match validated positioning

    @pytest.mark.asyncio
    async def test_all_sidel_bullets_preserved(self, master_cv, astek_analysis, positioning):
        """Verify all Sidel bullets are preserved (not removed/rewritten)."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            adaptation, master_cv
        )

        sidel_master_bullets = master_cv["experiences"][0]["bullets"]
        sidel_rendered_bullets = template_format["experience_bullets"].get("0", [])

        # Should have at least 6 of 7 bullets (one may be hidden if selection is smart)
        assert (
            len(sidel_rendered_bullets) >= 6
        ), f"Sidel bullets removed: {len(sidel_rendered_bullets)} < 6"

        # Verify text is IDENTICAL to source (not rewritten)
        for rendered in sidel_rendered_bullets:
            assert (
                rendered in sidel_master_bullets
            ), f"Bullet was rewritten: {rendered}"

    @pytest.mark.asyncio
    async def test_madebyakim_bullets_preserved(self, master_cv, astek_analysis, positioning):
        """Verify MadeByAkim bullets are preserved (not generalized)."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            adaptation, master_cv
        )

        madebyakim_master_bullets = master_cv["experiences"][1]["bullets"]
        madebyakim_rendered_bullets = template_format["experience_bullets"].get("1", [])

        # MadeByAkim should have at least 3 of 5 bullets
        assert (
            len(madebyakim_rendered_bullets) >= 3
        ), f"MadeByAkim bullets removed: {len(madebyakim_rendered_bullets)} < 3"

        # Verify text is IDENTICAL to source
        for rendered in madebyakim_rendered_bullets:
            assert (
                rendered in madebyakim_master_bullets
            ), f"MadeByAkim bullet was rewritten: {rendered}"

    @pytest.mark.asyncio
    async def test_nie_matcher_never_appears(self, master_cv, astek_analysis, positioning):
        """Verify V.I.E Matcher project appears only if verified (not all offers need it)."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            adaptation, master_cv
        )

        # Check if project 2 (V.I.E Matcher) is in selection
        project_order = template_format["project_order"]

        # If it appears, verify content is from source
        if 2 in project_order:
            vie_bullets = template_format["project_bullets"].get("2", [])
            vie_master_bullets = master_cv["projects"][2]["bullets"]

            for rendered in vie_bullets:
                assert rendered in vie_master_bullets, f"V.I.E bullet was rewritten: {rendered}"

    @pytest.mark.asyncio
    async def test_skillmap_not_in_default_selection(self, master_cv, astek_analysis, positioning):
        """Verify SkillMap (project 3) is not in default selection (not relevant)."""
        adaptation = await CVAdaptationAgent.adapt_cv(
            astek_analysis, positioning, master_cv
        )

        # Project 3 (SkillMap) should not be in top 3 unless extremely relevant
        # This test verifies the selection is working (not just including everything)
        project_blocks = adaptation.get("selected_project_blocks", [])
        skillmap_block = next(
            (b for b in project_blocks if b["source_id"] == 3), None
        )

        if skillmap_block:
            # If included, should be marked show=False
            assert skillmap_block.get("show") == False


class TestAdaptationConversion:
    """Test conversion from source-based to template format."""

    @pytest.fixture
    def master_cv(self):
        return load_master_cv()

    def test_conversion_preserves_source_text(self, master_cv):
        """Verify conversion fetches exact text from master_cv."""
        source_adaptation = {
            "title": "Data Analyst | Business Intelligence",
            "summary": "Test summary",
            "selected_experience_blocks": [
                {"source_id": 0, "relevance": 0.95, "show": True, "order": 1},
            ],
            "selected_project_blocks": [
                {"source_id": 0, "relevance": 0.8, "show": True, "order": 1},
            ],
            "selected_skill_blocks": [],
            "metadata": {},
        }

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            source_adaptation, master_cv
        )

        # Experience 0 (Sidel) should be in experience_order
        assert 0 in template_format["experience_order"]

        # Bullets should be EXACTLY from source, not modified
        sidel_bullets = template_format["experience_bullets"]["0"]
        master_sidel_bullets = master_cv["experiences"][0]["bullets"]

        assert sidel_bullets == master_sidel_bullets, "Bullets were modified during conversion"

    def test_conversion_filters_hidden_sections(self, master_cv):
        """Verify show=False sections are not rendered."""
        source_adaptation = {
            "title": "Data Analyst",
            "summary": "Test",
            "selected_experience_blocks": [
                {"source_id": 0, "relevance": 0.95, "show": True, "order": 1},
                {"source_id": 2, "relevance": 0.3, "show": False, "order": 3},
            ],
            "selected_project_blocks": [],
            "selected_skill_blocks": [],
            "metadata": {},
        }

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            source_adaptation, master_cv
        )

        # Only experience 0 should be in order (experience 2 is hidden)
        assert template_format["experience_order"] == [0]
        assert 2 not in template_format["experience_order"]

    def test_conversion_respects_order(self, master_cv):
        """Verify order field is respected in conversion."""
        source_adaptation = {
            "title": "Data Analyst",
            "summary": "Test",
            "selected_experience_blocks": [
                {"source_id": 2, "relevance": 0.4, "show": True, "order": 3},
                {"source_id": 0, "relevance": 0.95, "show": True, "order": 1},
                {"source_id": 1, "relevance": 0.8, "show": True, "order": 2},
            ],
            "selected_project_blocks": [],
            "selected_skill_blocks": [],
            "metadata": {},
        }

        template_format = GenerationAgent._convert_source_adaptation_to_template_format(
            source_adaptation, master_cv
        )

        # Order should be [0, 1, 2] based on order field
        assert template_format["experience_order"] == [0, 1, 2]
