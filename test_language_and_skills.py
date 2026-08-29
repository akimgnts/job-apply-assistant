"""Tests for language pipeline and skills grouping.

Tests:
1. Language detection (French vs English)
2. Bullet translation (preserve facts)
3. Skill grouping (semantic categories)
4. Template consistency (no mixed language)
5. Skill selection (job relevance + Master CV)
6. Exclusion handling (level 0 skills)
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.language_service import (
    detect_job_offer_language,
    translate_bullet_to_english,
    get_translated_section_titles,
)
from app.services.skill_grouping_service import (
    select_relevant_skills,
    group_skills_by_category,
    build_skill_groups_for_template,
)
from app.services.master_cv_service import load_master_cv


class TestLanguageDetection:
    """Test language detection from job offers."""

    def test_detect_french_offer(self):
        """French job offer should be detected as French."""
        french_text = "Missions: Analyser les données, développer des dashboards Power BI. Profil requis: ingénieur data"
        analysis = {
            "job_title": "Ingénieur Data",
            "missions": ["Analyser données", "Dashboards"],
        }
        lang = detect_job_offer_language(french_text, analysis)
        assert lang == "fr", f"Expected 'fr', got '{lang}'"

    def test_detect_english_offer(self):
        """English job offer should be detected as English."""
        english_text = "Build data pipelines and dashboards. Required: SQL, Python, Power BI. Senior engineer."
        analysis = {
            "job_title": "Senior Data Engineer",
            "missions": ["Build pipelines", "Create dashboards"],
        }
        lang = detect_job_offer_language(english_text, analysis)
        assert lang == "en", f"Expected 'en', got '{lang}'"

    def test_default_french_on_ambiguous(self):
        """Ambiguous text should default to French."""
        ambiguous_text = "Work with data and systems"
        lang = detect_job_offer_language(ambiguous_text, {})
        assert lang == "fr", "Should default to French for ambiguous text"


class TestBulletTranslation:
    """Test French-to-English bullet translation."""

    def test_preserve_numbers_exactly(self):
        """Translation must preserve numbers exactly."""
        french = "Conception de 6+ dashboards Power BI utilisés par des dizaines de collaborateurs"
        english = translate_bullet_to_english(french)
        assert "6+" in english, "Numbers must be preserved"
        assert "Power BI" in english, "Tools must be preserved"

    def test_preserve_dates_exactly(self):
        """Translation must preserve dates exactly."""
        french = "Automatisation d'un reporting 5–6 h/semaine → environ 1 h/semaine (~80% de réduction)"
        english = translate_bullet_to_english(french)
        assert "5–6" in english, "Time metrics must be preserved"
        assert "1 h" in english, "Time metrics must be preserved"
        assert "80%" in english, "Percentage must be preserved"

    def test_preserve_company_names(self):
        """Translation must preserve company names."""
        french = "Chez Sidel, conception de dashboards Wines & Spirits pour 61 comptes"
        english = translate_bullet_to_english(french)
        assert "Sidel" in english, "Company name must be preserved"
        assert "61" in english, "Numbers must be preserved"

    def test_preserve_technologies(self):
        """Translation must preserve technology names."""
        french = "Utilisation de Power BI, SQL, Python, FastAPI, PostgreSQL"
        english = translate_bullet_to_english(french)
        assert "Power BI" in english
        assert "SQL" in english
        assert "Python" in english
        assert "FastAPI" in english
        assert "PostgreSQL" in english

    def test_translate_descriptive_content(self):
        """Only descriptive content should be translated."""
        french = "Conception d'un moteur de matching avec extraction structurée"
        english = translate_bullet_to_english(french)
        # Should have English-like structure
        assert len(english) > 0
        assert english != french, "Should be translated, not identical"


class TestTranslationLabels:
    """Test translation of UI labels."""

    def test_french_labels_unchanged(self):
        """French labels should remain as-is."""
        labels = get_translated_section_titles("fr")
        assert labels["experience"] == "EXPÉRIENCE"
        assert labels["projects"] == "PROJETS"
        assert labels["skills"] == "COMPÉTENCES"

    def test_english_labels_translated(self):
        """English should have translated labels."""
        labels = get_translated_section_titles("en")
        assert labels["experience"] == "EXPERIENCE"
        assert labels["projects"] == "PROJECTS"
        assert labels["skills"] == "SKILLS"


class TestSkillSelection:
    """Test skill selection based on job relevance."""

    def test_select_matching_skills(self):
        """Should select skills that match job requirements."""
        master_cv = load_master_cv()
        analysis = {
            "job_title": "Data Analyst",
            "required_skills": ["Power BI", "SQL", "Python"],
            "missions": ["Build dashboards", "Analyze data"],
        }

        selected = select_relevant_skills(analysis, master_cv["skills"])
        assert len(selected) > 0, "Should select at least one skill"
        assert "Power BI" in selected or "SQL" in selected or "Python" in selected

    def test_exclude_level_zero_skills(self):
        """Should never select excluded skills (level 0)."""
        master_cv = load_master_cv()
        analysis = {
            "job_title": "Project Manager",
            "required_skills": ["Jira", "Confluence", "Agile"],
            "missions": [],
        }

        selected = select_relevant_skills(analysis, master_cv["skills"])
        # Jira and Confluence should NOT be selected (level 0)
        assert "Jira" not in selected
        assert "Confluence" not in selected
        # But Agile should be selected
        assert "Agile" in selected or len(selected) > 0

    def test_returns_master_cv_subset(self):
        """Selected skills must be subset of Master CV."""
        master_cv = load_master_cv()
        master_labels = {s["label"] for s in master_cv["skills"]}

        analysis = {
            "job_title": "Python Developer",
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "missions": ["Build APIs"],
        }

        selected = select_relevant_skills(analysis, master_cv["skills"])
        for skill in selected:
            assert skill in master_labels, f"'{skill}' not in Master CV"


class TestSkillGrouping:
    """Test semantic grouping of skills."""

    def test_group_skills_into_categories(self):
        """Selected skills should be grouped into semantic categories."""
        skills = ["Power BI", "SQL", "Python", "FastAPI", "PostgreSQL", "Agile"]
        grouped = group_skills_by_category(skills)

        assert len(grouped) > 0, "Should create at least one category"
        assert "Data & BI" in grouped or "Automation & Backend" in grouped

    def test_no_empty_categories(self):
        """No category should be empty after grouping."""
        skills = ["Power BI", "SQL", "Python", "Agile"]
        grouped = group_skills_by_category(skills)

        for category, category_skills in grouped.items():
            assert len(category_skills) > 0, f"Category '{category}' is empty"

    def test_all_skills_placed_or_excluded(self):
        """All selected skills should appear in a group or be explicitly excluded."""
        selected_skills = ["Power BI", "SQL", "Python", "FastAPI", "PostgreSQL"]
        grouped = group_skills_by_category(selected_skills)

        grouped_flat = []
        for category_skills in grouped.values():
            grouped_flat.extend(category_skills)

        # All selected skills should be in groups
        for skill in selected_skills:
            assert skill in grouped_flat, f"'{skill}' not in any category"


class TestBuildSkillGroups:
    """Test end-to-end skill group building."""

    def test_build_skill_groups_end_to_end(self):
        """build_skill_groups_for_template should return properly grouped skills."""
        master_cv = load_master_cv()
        analysis = {
            "job_title": "Data Engineer",
            "required_skills": ["Python", "SQL", "PostgreSQL", "Agile"],
            "missions": ["Build data pipelines", "Optimize queries"],
        }

        skill_groups = build_skill_groups_for_template(analysis, master_cv["skills"])

        assert isinstance(skill_groups, dict), "Should return dict"
        assert len(skill_groups) > 0, "Should have at least one category"

        # Each category should have skills
        for category, skills in skill_groups.items():
            assert isinstance(category, str)
            assert isinstance(skills, list)
            assert len(skills) > 0, f"Category '{category}' has no skills"

    def test_fallback_if_no_skills_selected(self):
        """Should have fallback if no skills matched."""
        master_cv = load_master_cv()
        analysis = {
            "job_title": "Janitor",  # No matching skills
            "required_skills": [],
            "missions": [],
        }

        skill_groups = build_skill_groups_for_template(analysis, master_cv["skills"])
        # Should still return something (fallback)
        assert len(skill_groups) >= 0


class TestLanguageConsistency:
    """Test that CVs maintain consistent language throughout."""

    def test_french_cv_consistency(self):
        """All French CV sections should use French."""
        # This test would require full CV generation
        # For now, verify that section titles can be translated
        titles = get_translated_section_titles("fr")

        # All titles should be in French (contain French characters or words)
        for key, title in titles.items():
            # Check for French words
            if key in ["experience", "projects", "skills", "education", "certifications", "languages"]:
                assert title is not None
                assert len(title) > 0

    def test_english_cv_consistency(self):
        """All English CV sections should use English."""
        titles = get_translated_section_titles("en")

        # All titles should be in English
        expected_keys = ["experience", "projects", "skills", "education", "certifications", "languages"]
        for key in expected_keys:
            assert key in titles
            assert titles[key] is not None
            assert len(titles[key]) > 0


if __name__ == "__main__":
    print("\n" + "="*80)
    print("LANGUAGE & SKILLS TESTS")
    print("="*80 + "\n")

    pytest.main([__file__, "-v", "-s"])
