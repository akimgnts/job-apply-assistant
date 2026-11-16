import pytest
from datetime import date

from app.services.document_generation_v2 import (
    DocumentGenerationV2,
    DocumentQualityError,
)
from app.services.master_cv_service import load_master_cv
from app.agents.generation_agent import GenerationAgent
from app.prompts.generation_prompt import get_mail_prompt


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


def test_letter_payload_rejects_a_string_instead_of_four_paragraphs(monkeypatch, luxurynsight_analysis):
    async def malformed_letter_payload(*args, **kwargs):
        return '''{
          "nom_complet": "Akim Guentas",
          "intitule_cible": "Data Engineer",
          "positionnement": "Data",
          "entreprise": "Luxurynsight",
          "objet": "Candidature",
          "formule_appel": "Madame, Monsieur,",
          "paragraphes": "Le texte entier de la lettre"
        }'''

    import app.services.openai_service as openai_service

    monkeypatch.setattr(openai_service, "call_openai", malformed_letter_payload)
    html = __import__("asyncio").run(
        DocumentGenerationV2.generate_letter_html(luxurynsight_analysis, load_master_cv())
    )

    assert "Le texte entier de la lettre" not in html
    assert "Chez Sidel" in html


def test_letter_uses_the_generation_date_not_an_llm_supplied_date():
    html = DocumentGenerationV2.render_letter_payload({
        "nom_complet": "Akim Guentas",
        "intitule_cible": "Data Analyst",
        "positionnement": "Data",
        "entreprise": "Entreprise test",
        "objet": "Candidature",
        "formule_appel": "Madame, Monsieur,",
        "paragraphes": ["A", "B", "C", "D"],
        "date": "1900-01-01",
    })

    assert date.today().strftime("%d/%m/%Y") in html
    assert "1900-01-01" not in html


def test_mail_body_removes_a_model_generated_wrapper_before_template_rendering():
    body = GenerationAgent._normalize_mail_body("""Bonjour,

Subject: Application for Data Analyst

Dear [Recruiter's Name],

I am applying for the Data Analyst position at Credit Agricole Business Digital.

Best regards,
  
Akim Guentas
""")

    assert body == "I am applying for the Data Analyst position at Credit Agricole Business Digital."


def test_source_language_overrides_an_english_analysis_summary():
    assert DocumentGenerationV2._language({
        "source_language": "fr",
        "job_title": "Data Analyst",
        "missions": ["Build and maintain dashboards"],
    }) == "fr"


def test_mail_prompt_uses_the_source_offer_language():
    prompt = get_mail_prompt({"job_title": "Data Analyst", "company": "Entreprise", "source_language": "fr"}, "Data Analyst")
    assert "Write in French." in prompt
    assert "No attachments are confirmed" in prompt
    with_attachments = get_mail_prompt({"job_title": "Data Analyst", "company": "Entreprise", "source_language": "fr", "available_documents": ["letter", "cv"], "letter_argument": "Power BI dashboards for the sales team"}, "Data Analyst")
    assert "the motivation letter and the CV" in with_attachments
    assert "Power BI dashboards for the sales team" in with_attachments


def test_french_offer_with_english_skill_terms_stays_french():
    assert DocumentGenerationV2._language({
        "raw_offer": "Nous recherchons un analyste pour construire des dashboards Power BI et suivre les KPI de l'équipe.",
        "job_title": "Data Analyst",
        "missions": ["Build pipelines SQL"],
        "required_skills": ["Python", "Data Quality"],
    }) == "fr"


def test_offer_language_uses_description_not_english_job_title_or_skills():
    from app.services.language_service import detect_job_offer_language
    french = "Nous recherchons un Data Engineer pour accompagner les équipes. Vos missions : analyser les besoins, assurer le suivi et contribuer aux projets avec Python et SQL."
    english = "We are looking for a Data Engineer to join our team. You will develop and support data pipelines, work with business users, and provide reporting."
    assert detect_job_offer_language(french, {"job_title": "Data Engineer", "required_skills": ["Data Quality"]}) == "fr"
    assert detect_job_offer_language(english, {"job_title": "Data Analyst"}) == "en"


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

