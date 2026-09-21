import pytest

from app.services.document_generation_v2 import (
    DocumentGenerationV2,
    DocumentQualityError,
)
from app.services.master_cv_service import load_master_cv


@pytest.fixture
def luxurynsight_analysis():
    return {
        "company": "Luxurynsight",
        "job_title": "Data Engineer",
        "missions": [
            "Build and maintain data pipelines",
            "Improve data quality and reliability",
            "Deliver datasets for business users",
        ],
        "required_skills": [
            "Python",
            "SQL",
            "PostgreSQL",
            "data pipelines",
            "data quality",
            "Docker",
        ],
        "ats_keywords": ["data engineer", "python", "sql", "data quality", "etl"],
    }


def test_targeted_cv_fallback_uses_claude_template_and_data_engineer_positioning(luxurynsight_analysis):
    html = DocumentGenerationV2.build_fallback_cv_html(
        luxurynsight_analysis,
        load_master_cv(),
    )

    assert "AKIM GUENTAS" in html
    assert "Data Engineer" in html
    assert "Python" in html
    assert "SQL" in html
    assert "PostgreSQL" in html
    assert "Alembic" in html
    assert "Docker" in html
    assert "Coolify" in html
    assert "TEMPLATE DE RÉFÉRENCE" not in html
    assert "{{" not in html
    assert "Candidate – Master CV" not in html
    assert "Designed and deployed de" not in html


def test_quality_rejects_placeholders_and_hybrid_language():
    with pytest.raises(DocumentQualityError):
        DocumentGenerationV2.validate_cv_html(
            "<html>{{NOM_COMPLET}} Designed and deployed de 6+ dashboards</html>"
        )


def test_letter_fallback_uses_apec_template_without_placeholders(luxurynsight_analysis):
    html = DocumentGenerationV2.build_fallback_letter_html(
        luxurynsight_analysis,
        load_master_cv(),
    )

    assert "Lettre de motivation" in html
    assert "Luxurynsight" in html
    assert "Data Engineer" in html
    assert "Madame, Monsieur" in html
    assert "{{" not in html
    assert "TEMPLATE DE RÉFÉRENCE" not in html
