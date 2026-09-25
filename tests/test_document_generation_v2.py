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


def test_servier_fallback_uses_cv_prime_strategy_for_marketing_crm_vie():
    analysis = {
        "company": "Servier International",
        "job_title": "Digital & Data Analytics Officer",
        "missions": [
            "Monitor digital performance and marketing KPIs",
            "Build Power BI dashboards for CRM, leads and funnel tracking",
            "Support teams in Rio de Janeiro during a V.I.E assignment",
        ],
        "required_skills": [
            "Power BI",
            "CRM",
            "marketing performance",
            "NPS",
            "customer feedback",
            "automation",
        ],
        "ats_keywords": ["digital analytics", "crm", "power bi", "marketing automation", "vie"],
        "location": "Rio de Janeiro",
        "contract_type": "V.I.E",
    }

    html = DocumentGenerationV2.build_fallback_cv_html(analysis, load_master_cv())

    assert "Digital & Data Analytics Officer" in html
    assert "CRM & Digital Performance" in html
    assert "Open to V.I.E in Rio de Janeiro from January 2027" in html
    assert "CDI, Paris, immediate" not in html
    assert html.index("Data & Business Analyst — Marketing, Sales & CRM Analytics") < html.index("AI Transformation Consultant & Product Builder")
    assert "CRM dashboard" in html
    assert "NPS" in html
    assert "Claude Code" not in html
    assert "MCP" not in html
    assert "<span class=\"project-title\"></span> |" not in html


def test_quality_rejects_empty_project_shells():
    with pytest.raises(DocumentQualityError):
        DocumentGenerationV2.validate_cv_html(
            "<html><body>AKIM GUENTAS<div class=\"project\"><p><span class=\"project-title\"></span> | </p></div></body></html>"
        )


@pytest.mark.asyncio
async def test_marketing_crm_family_bypasses_generic_llm(monkeypatch):
    async def generic_llm(*args, **kwargs):
        return '{"nom_complet":"AKIM GUENTAS"}'

    import app.services.openai_service as openai_service

    monkeypatch.setattr(openai_service, "call_openai", generic_llm)
    analysis = {
        "company": "Servier International",
        "job_title": "Digital & Data Analytics Officer",
        "missions": ["Power BI dashboards", "CRM funnel tracking", "marketing KPIs"],
        "required_skills": ["CRM", "NPS", "Power BI"],
        "location": "Rio de Janeiro",
        "contract_type": "V.I.E",
    }

    html = await DocumentGenerationV2.generate_cv_html(analysis, load_master_cv())

    assert "CRM dashboard" in html
    assert "V.I.E Rio de Janeiro" in html
    assert "CDI, Paris, immediate" not in html


@pytest.mark.parametrize("contract", [None, "CDI", "CDD"])
def test_apec_marketing_cv_does_not_invent_vie_mobility(contract):
    analysis = {
        "company": "Gan Assurances",
        "job_title": "Commercial Pilotage Analyst",
        "missions": ["CRM dashboards", "marketing KPIs", "assurance vie"],
        "source": "apec",
        "contract_type": contract,
    }
    html = DocumentGenerationV2.build_fallback_cv_html(analysis, load_master_cv())
    assert load_master_cv()["personal_info"]["location"] in html
    for unwanted in ("V.I.E", "January 2027", "12 months", "the target location", "Availability:"):
        assert unwanted not in html
