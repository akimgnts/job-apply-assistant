"""Claude-grade CV and cover letter generation.

This module keeps the facts locked to Master CV V3 while using the stricter
targeted templates supplied by the user. The LLM may write positioning copy, but
the service validates the rendered HTML before it is saved.
"""

from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates"
DATA_DIR = ROOT / "data" / "document_generation"


class DocumentQualityError(ValueError):
    """Raised when a generated document fails mandatory quality gates."""


class DocumentGenerationV2:
    """Generate targeted application documents from the locked Master CV."""

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)

    @staticmethod
    async def generate_cv_html(analysis: dict, master_cv: dict) -> str:
        """Generate a targeted CV using the strict template and quality gates."""
        if DocumentGenerationV2._cv_prime_strategy(analysis)["family"] == "marketing_crm_bi":
            return DocumentGenerationV2.build_fallback_cv_html(analysis, master_cv)
        try:
            payload = await DocumentGenerationV2._generate_cv_payload(analysis, master_cv)
            html_doc = DocumentGenerationV2.render_cv_payload(payload)
            DocumentGenerationV2.validate_cv_html(html_doc)
            return html_doc
        except Exception as exc:
            logger.warning("CV V2 LLM generation failed, using deterministic fallback: %s", type(exc).__name__)
            return DocumentGenerationV2.build_fallback_cv_html(analysis, master_cv)

    @staticmethod
    async def generate_letter_html(analysis: dict, master_cv: dict) -> str:
        """Generate an APEC-style motivation letter using the strict template."""
        try:
            payload = await DocumentGenerationV2._generate_letter_payload(analysis, master_cv)
            html_doc = DocumentGenerationV2.render_letter_payload(payload)
            DocumentGenerationV2.validate_letter_html(html_doc)
            return html_doc
        except Exception as exc:
            logger.warning("Letter V2 LLM generation failed, using deterministic fallback: %s", type(exc).__name__)
            return DocumentGenerationV2.build_fallback_letter_html(analysis, master_cv)

    @staticmethod
    async def _generate_cv_payload(analysis: dict, master_cv: dict) -> dict:
        from app.services.openai_service import call_openai

        prompt = DocumentGenerationV2._cv_prompt(analysis, master_cv)
        raw = await call_openai(prompt, json_mode=True)
        payload = json.loads(raw)
        DocumentGenerationV2._require_keys(payload, {
            "nom_complet", "intitule_cible", "mots_cles_differenciants",
            "resume", "competences", "experiences", "projet_cible",
            "projets_complementaires", "formation",
        })
        return payload

    @staticmethod
    async def _generate_letter_payload(analysis: dict, master_cv: dict) -> dict:
        from app.services.openai_service import call_openai

        prompt = DocumentGenerationV2._letter_prompt(analysis, master_cv)
        raw = await call_openai(prompt, json_mode=True)
        payload = json.loads(raw)
        DocumentGenerationV2._require_keys(payload, {
            "nom_complet", "intitule_cible", "positionnement",
            "entreprise", "objet", "formule_appel", "paragraphes",
        })
        return payload

    @staticmethod
    def build_fallback_cv_html(analysis: dict, master_cv: dict) -> str:
        payload = DocumentGenerationV2._fallback_cv_payload(analysis, master_cv)
        html_doc = DocumentGenerationV2.render_cv_payload(payload)
        DocumentGenerationV2.validate_cv_html(html_doc)
        return html_doc

    @staticmethod
    def build_fallback_letter_html(analysis: dict, master_cv: dict) -> str:
        payload = DocumentGenerationV2._fallback_letter_payload(analysis, master_cv)
        html_doc = DocumentGenerationV2.render_letter_payload(payload)
        DocumentGenerationV2.validate_letter_html(html_doc)
        return html_doc

    @staticmethod
    def render_cv_payload(payload: dict) -> str:
        template = DocumentGenerationV2.env.get_template("cv_targeted.html")
        replacements = DocumentGenerationV2._cv_replacements(payload)
        rendered = template.render(**replacements)
        return DocumentGenerationV2._strip_reference_comments(rendered)

    @staticmethod
    def render_letter_payload(payload: dict) -> str:
        template = DocumentGenerationV2.env.get_template("letter_apec.html")
        replacements = DocumentGenerationV2._letter_replacements(payload)
        rendered = template.render(**replacements)
        return DocumentGenerationV2._strip_reference_comments(rendered)

    @staticmethod
    def validate_cv_html(html_doc: str) -> None:
        DocumentGenerationV2._validate_common(html_doc)
        if "Candidate – Master CV" in html_doc:
            raise DocumentQualityError("Old generic CV template detected")
        if "Designed and deployed de" in html_doc or re.search(r"\b(de|des|du)\s+\d+\+", html_doc):
            raise DocumentQualityError("Hybrid French/English wording detected")
        if re.search(r'<span class="project-title">\s*</span>\s*\|\s*(?:</p>|<)', html_doc):
            raise DocumentQualityError("Empty project shell detected")
        if re.search(r"<li>\s*</li>", html_doc):
            raise DocumentQualityError("Empty bullet detected")
        if "AKIM GUENTAS" not in html_doc.upper():
            raise DocumentQualityError("Candidate identity missing")

    @staticmethod
    def validate_letter_html(html_doc: str) -> None:
        DocumentGenerationV2._validate_common(html_doc)
        if "Lettre de motivation" not in html_doc:
            raise DocumentQualityError("Letter title missing")

    @staticmethod
    def _validate_common(html_doc: str) -> None:
        if re.search(r"\{\{[A-Z0-9_ .-]+\}\}", html_doc):
            raise DocumentQualityError("Unresolved template placeholder")
        if "TEMPLATE DE RÉFÉRENCE" in html_doc:
            raise DocumentQualityError("Internal template comment leaked")
        if re.search(r">\s*(None|null)\s*<", html_doc, re.I):
            raise DocumentQualityError("Null value leaked into document")

    @staticmethod
    def _fallback_cv_payload(analysis: dict, master_cv: dict) -> dict:
        info = master_cv["personal_info"]
        company = analysis.get("company") or "Entreprise cible"
        role = analysis.get("job_title") or "Data / AI Role"
        language = DocumentGenerationV2._language(analysis)
        is_en = language == "en"
        strategy = DocumentGenerationV2._cv_prime_strategy(analysis)

        if strategy["family"] == "marketing_crm_bi":
            return DocumentGenerationV2._fallback_marketing_crm_cv_payload(
                analysis, master_cv, info, company, role, is_en
            )

        if is_en:
            profile_title = "Profile"
            skills_title = "Technical Skills"
            exp_title = "Professional Experience"
            project_title = "Key Data Project"
            extra_projects_title = "Additional Project"
            education_title = "Education & Certifications"
            availability = "CDI, Paris, immediate"
            profile = (
                "Data profile building pipelines end to end, from ingestion and transformation "
                "to storage, quality control and delivery. Since 2024, freelance activity with "
                "Python, SQL, PostgreSQL, FastAPI, SQLAlchemy, Alembic, tests, Git and Docker; "
                "before that, two years at Sidel consolidating customer, sales and Installed Base "
                "data, modeling star schemas and automating reporting with about 80% time saved."
            )
        else:
            profile_title = "Profil"
            skills_title = "Compétences techniques"
            exp_title = "Expérience professionnelle"
            project_title = "Projet data clé"
            extra_projects_title = "Projet complémentaire"
            education_title = "Formation & certifications"
            availability = "CDI, Paris, immédiate"
            profile = (
                "Profil data capable de construire des pipelines de bout en bout, de l’ingestion "
                "à la transformation, au stockage, au contrôle qualité et à la restitution. Depuis "
                "2024, activité freelance avec Python, SQL, PostgreSQL, FastAPI, SQLAlchemy, "
                "Alembic, tests, Git et Docker ; auparavant deux ans chez Sidel sur la consolidation "
                "de données clients, commerciales et Installed Base, la modélisation en étoile et "
                "l’automatisation d’un reporting avec environ 80 % de temps économisé."
            )

        return {
            "nom_complet": (info["name"] or "Akim Guentas").upper(),
            "intitule_cible": role,
            "entreprise": company,
            "mots_cles_differenciants": "Python & SQL Pipelines, Data Quality, Data Modeling, Production Delivery",
            "localisation": f"{info.get('location') or 'Paris, France'} | Available immediately (CDI)",
            "telephone": info.get("phone", ""),
            "email": info.get("email", ""),
            "linkedin_url": DocumentGenerationV2._url(info.get("linkedin", ""), "https://"),
            "linkedin_label": "linkedin.com/in/akimguentas",
            "github_url": DocumentGenerationV2._url(info.get("github", ""), "https://"),
            "github_label": "github.com/akimgnts",
            "portfolio_url": DocumentGenerationV2._url(info.get("portfolio", ""), "https://"),
            "portfolio_label": info.get("portfolio", "madebyakim.com"),
            "titres": {
                "profil": profile_title,
                "competences": skills_title,
                "experiences": exp_title,
                "projet_cible": project_title,
                "projets_complementaires": extra_projects_title,
                "formation": education_title,
            },
            "resume": profile,
            "competences": [
                ("Languages & Databases", "Python, SQL, PostgreSQL, SQLAlchemy, Alembic"),
                ("Pipelines & Quality", "Ingestion, transformation, normalization, data quality checks, replay workflows, REST APIs"),
                ("Data Modeling", "Dimensional modeling, star schema, fact/dimension tables, Power BI, Power Query, DAX"),
                ("Engineering Practices", "Git/GitHub, Docker, Coolify, tests, logs, documentation, Agile delivery"),
                ("Automation & AI Tools", "n8n, Make, webhooks, OpenAI API, LangChain, Claude Code, MCP, RAG"),
            ],
            "precision": "Cloud data stack: Databricks, BigQuery and AWS at foundational level; medallion architecture notions.",
            "experiences": DocumentGenerationV2._fallback_experiences(master_cv, is_en),
            "projet_cible": {
                "name": "Elevia — Recommendation platform & data quality",
                "description": (
                    "Pipeline combining structured extraction, ESCO skills normalization, semantic matching and explainable scoring "
                    "(Python, FastAPI, PostgreSQL, OpenAI, LangChain). 10+ evaluation cycles on 30 profiles and 1,000+ job offers; "
                    "replay workflows and frozen scoring keep runs reproducible and auditable."
                ),
                "status": "2025 – Present",
            },
            "projets_complementaires": [
                {
                    "name": "Job Apply Assistant — Multi-agent data pipeline",
                    "description": (
                        "Manual process of about 45 minutes turned into an automated workflow of about 5 minutes; PostgreSQL "
                        "persistence with Alembic migrations, structured schemas, Docker/Coolify deployment and Telegram notifications."
                    ),
                }
            ],
            "formation": {
                "diplomes": [
                    ("MSc Business Intelligence & Analytics — Data Analyst for Marketing", "Eugenia School", "2025"),
                    ("Bachelor in Business & Marketing Management", "EM Normandie", "2023"),
                ],
                "certifications": "Python for Machine Learning | Dataiku ML Practitioner | Fine-Tuning Large Language Models",
                "langues": "French (native), English (professional), Spanish (intermediate)",
                "disponibilite": availability,
            },
        }

    @staticmethod
    def _fallback_marketing_crm_cv_payload(
        analysis: dict,
        master_cv: dict,
        info: dict,
        company: str,
        role: str,
        is_en: bool,
    ) -> dict:
        contract = re.sub(r"[\s.]", "", str(analysis.get("contract_type") or "")).upper()
        mobility = info.get("location") or "Paris, France"
        availability = ""
        if contract in {"VIE", "VOLONTARIATINTERNATIONALENENTREPRISE"}:
            vie_location = DocumentGenerationV2._vie_location(analysis)
            mobility = f"{mobility} | Open to V.I.E in {vie_location} from January 2027"
            availability = f"V.I.E {vie_location} · January 2027 · 12 months"
        return {
            "nom_complet": (info["name"] or "Akim Guentas").upper(),
            "intitule_cible": role,
            "entreprise": company,
            "mots_cles_differenciants": "Power BI · CRM & Digital Performance · Marketing Automation",
            "localisation": mobility,
            "telephone": info.get("phone", ""),
            "email": info.get("email", ""),
            "linkedin_url": DocumentGenerationV2._url(info.get("linkedin", ""), "https://"),
            "linkedin_label": "linkedin.com/in/akimguentas",
            "github_url": DocumentGenerationV2._url(info.get("github", ""), "https://"),
            "github_label": "github.com/akimgnts",
            "portfolio_url": DocumentGenerationV2._url(info.get("portfolio", ""), "https://"),
            "portfolio_label": info.get("portfolio", "madebyakim.com"),
            "titres": {
                "profil": "Profile" if is_en else "Profil",
                "competences": "Core Skills" if is_en else "Compétences clés",
                "experiences": "Professional Experience" if is_en else "Expérience professionnelle",
                "projet_cible": "Selected Digital & Automation Project" if is_en else "Projet digital & automation ciblé",
                "projets_complementaires": "Selected Digital & Automation Projects" if is_en else "Projets digitaux & automation sélectionnés",
                "formation": "Education & Certifications" if is_en else "Formation & certifications",
            },
            "resume": (
                "Data & Business Analyst with an MSc focused on marketing analytics and two years' experience "
                "turning CRM, commercial and customer data into performance dashboards and business recommendations. "
                "At Sidel, delivered 6+ Power BI dashboards used weekly by dozens of employees and managers, connected "
                "previously separate data sources and reduced a weekly reporting process by about 80%. Also builds "
                "automation and data-integration workflows through MadeByAkim. Combines analytical rigor, business "
                "understanding and proactive delivery in international environments."
            ),
            "competences": [
                ("Digital performance & CRM", "Lead and funnel tracking, marketing KPIs, NPS, customer feedback, touchpoints, commercial prioritisation"),
                ("Dashboards & analytics", "Power BI, Power Query, DAX (operational), advanced Excel, Tableau (intermediate)"),
                ("Data integration & quality", "SQL, Python, PostgreSQL, REST APIs, webhooks, consistency checks, dimensional modelling"),
                ("Marketing automation", "n8n, Make, Google Apps Script, automated workflows, system-to-system data flows"),
                ("Business delivery", "KPI definition, user stories, testing, Agile/Kanban, cross-functional stakeholder management"),
            ],
            "precision": "",
            "experiences": DocumentGenerationV2._fallback_marketing_crm_experiences(),
            "projet_cible": {
                "name": "Nuit Blanche — Content production automation",
                "description": (
                    "Designed a Google Sheets and Apps Script workflow that turns event data into visual deliverables "
                    "through validation, filtering, prioritisation and automated generation."
                ),
                "status": "",
            },
            "projets_complementaires": [
                {
                    "name": "Job Apply Assistant — Multi-agent workflow",
                    "description": (
                        "Converted a manual process of about 45 minutes into an automated workflow of about 5 minutes, "
                        "covering data parsing, analysis, matching, document generation and tracking."
                    ),
                }
            ],
            "formation": {
                "diplomes": [
                    ("MSc Business Intelligence & Analytics — Data Analyst for Marketing", "Eugenia School", "2025"),
                    ("Bachelor in Business & Marketing Management", "EM Normandie", "2023"),
                ],
                "certifications": "Dataiku ML Practitioner · Python for Machine Learning · Fine-Tuning Large Language Models",
                "langues": "French (native), English (professional), Spanish (intermediate)",
                "disponibilite": availability,
            },
        }

    @staticmethod
    def _fallback_marketing_crm_experiences() -> list[dict]:
        return [
            {
                "title": "Data & Business Analyst — Marketing, Sales & CRM Analytics",
                "company": "Sidel (Tetra Laval Group)",
                "dates": "2023 – 2025 | International",
                "bullets": [
                    "Designed and deployed 6+ Power BI dashboards used weekly by dozens of employees and managers to monitor business performance across Marketing, Sales, Communication and Management use cases.",
                    "Built a European event-performance dashboard by reconciling attendance, contact and satisfaction data; structured a funnel from visits and contacts to meetings and commercial opportunities.",
                    "Developed a CRM dashboard covering sales activity, meetings, new opportunities and customer touchpoints; used interaction history to help teams prioritise follow-ups.",
                    "Tracked leads, marketing KPIs, NPS and customer feedback; translated analyses into recommendations and presentations for business teams.",
                    "Automated a weekly Excel report from 5–6 hours to about 1 hour, including controls — approximately 80% less processing time.",
                ],
            },
            {
                "title": "AI Transformation Consultant & Product Builder (Freelance)",
                "company": "MadeByAkim",
                "dates": "2024 – Present | Paris / Remote",
                "bullets": [
                    "Analyse business needs and design end-to-end data solutions with Python, FastAPI, PostgreSQL, SQL and REST APIs, from ingestion and transformation to storage and delivery.",
                    "Build automations with n8n, Make, Google Apps Script, webhooks and APIs to connect systems, reduce manual work and make recurring data flows more reliable.",
                    "Set up tests, logs, Git versioning, Docker and Coolify deployment for traceability and maintainability.",
                ],
            },
        ]

    @staticmethod
    def _fallback_experiences(master_cv: dict, is_en: bool) -> list[dict]:
        experiences = master_cv.get("experiences", [])
        made = experiences[1]
        sidel = experiences[0]
        return [
            {
                "title": "AI Transformation Consultant & Product Builder (Freelance)",
                "company": "MadeByAkim",
                "dates": "2024 – Present | Paris / Remote",
                "bullets": [
                    "Design end-to-end data solutions with Python, FastAPI, PostgreSQL, SQL and REST APIs: ingestion, transformation, storage and delivery.",
                    "Build pipelines combining quality control, normalization, classification, scoring and human validation before data is persisted.",
                    "Set up tests, logs, documentation, Git versioning, Docker and Coolify deployment for traceability and maintainability.",
                    "Automate processing with n8n, Make, Google Apps Script, webhooks and APIs to remove manual steps and make runs reliable.",
                    "Scope each product end to end, from business need and architecture to development and production delivery.",
                ],
            },
            {
                "title": "Data & Business Analyst",
                "company": "Sidel (Tetra Laval Group)",
                "dates": "2023 – 2025 | Octeville-sur-Mer / International",
                "bullets": [
                    "Consolidated and analyzed customer, sales and Installed Base data with Python, SQL, Power Query and Excel; ran consistency checks to improve data quality.",
                    "Modeled data upstream of reporting with star schemas, fact and dimension tables, and built DAX measures to make KPIs reliable.",
                    "Automated a weekly Excel report from 5–6 h to about 1 h per week, controls included — about 80% processing time saved.",
                    "Merged previously separate sources, including trade-show contacts and satisfaction surveys, into one continuously updated Europe-wide dataset.",
                    "Delivered 6+ Power BI dashboards used weekly by dozens of employees; gathered requirements with IT, CRM, Sales and Marketing before release.",
                ],
            },
        ]

    @staticmethod
    def _fallback_letter_payload(analysis: dict, master_cv: dict) -> dict:
        info = master_cv["personal_info"]
        company = analysis.get("company") or "Entreprise cible"
        role = analysis.get("job_title") or "poste ciblé"
        today = "21 septembre 2026"
        return {
            "nom_complet": info["name"] or "Akim Guentas",
            "intitule_cible": role,
            "positionnement": "Data, pipelines et qualité de données",
            "localisation": info.get("location", "Paris"),
            "telephone": info.get("phone", ""),
            "email": info.get("email", ""),
            "linkedin_url": DocumentGenerationV2._url(info.get("linkedin", ""), "https://"),
            "linkedin_label": "linkedin.com/in/akimguentas",
            "github_url": DocumentGenerationV2._url(info.get("github", ""), "https://"),
            "github_label": "github.com/akimgnts",
            "portfolio_url": DocumentGenerationV2._url(info.get("portfolio", ""), "https://"),
            "portfolio_label": info.get("portfolio", "madebyakim.com"),
            "entreprise": company,
            "destinataire": "Équipe de recrutement",
            "ville": "",
            "date": today,
            "objet": f"Candidature — {role}",
            "formule_appel": "Madame, Monsieur,",
            "paragraphes": [
                f"Le poste de {role} chez {company} demande de transformer des données en flux fiables, exploitables et utiles aux équipes métier. Les enjeux principaux sont la qualité des données, la robustesse des traitements et la capacité à livrer des résultats compréhensibles par les utilisateurs.",
                "Ma pratique de Python, SQL, PostgreSQL et FastAPI permet de construire des pipelines de bout en bout, depuis l’ingestion jusqu’à la restitution. Dans mes projets MadeByAkim, les workflows associent normalisation, contrôle qualité, scoring, validation humaine, tests, logs et déploiement Docker/Coolify.",
                "Chez Sidel, la consolidation de données clients, commerciales et Installed Base a servi des dashboards Power BI utilisés chaque semaine par plusieurs fonctions métier. L’automatisation d’un reporting hebdomadaire a ramené un traitement de 5–6 h à environ 1 h, contrôles inclus.",
                "Un entretien permettrait d’échanger sur vos priorités data et sur la mise au service de ces compétences pour fiabiliser vos pipelines, améliorer la qualité des données et accélérer la livraison de cas d’usage concrets.",
            ],
            "formule_politesse": "Je vous prie d’agréer, Madame, Monsieur, l’expression de mes salutations distinguées.",
            "signature": info["name"] or "Akim Guentas",
        }

    @staticmethod
    def _cv_replacements(payload: dict) -> dict:
        comp = payload.get("competences", [])
        while len(comp) < 5:
            comp.append(("", ""))
        exps = payload.get("experiences", [])
        while len(exps) < 2:
            exps.append({"title": "", "company": "", "dates": "", "bullets": []})
        p2 = (payload.get("projets_complementaires") or [{"name": "", "description": ""}])[0]
        formation = payload.get("formation", {})
        diplomas = formation.get("diplomes", [])
        while len(diplomas) < 2:
            diplomas.append(("", "", ""))
        titles = payload.get("titres", {})
        return {
            "NOM_COMPLET": payload.get("nom_complet", "Akim Guentas"),
            "INTITULE_POSTE": payload.get("intitule_cible", ""),
            "ENTREPRISE_CIBLE": payload.get("entreprise", ""),
            "INTITULE_CIBLE": payload.get("intitule_cible", ""),
            "MOTS_CLES_DIFFERENCIANTS": payload.get("mots_cles_differenciants", ""),
            "LOCALISATION_ET_MOBILITE": payload.get("localisation", "Paris, France"),
            "TELEPHONE": payload.get("telephone", ""),
            "EMAIL": payload.get("email", ""),
            "URL_LINKEDIN": payload.get("linkedin_url", ""),
            "AFFICHAGE_LINKEDIN": payload.get("linkedin_label", ""),
            "URL_GITHUB": payload.get("github_url", ""),
            "AFFICHAGE_GITHUB": payload.get("github_label", ""),
            "URL_PORTFOLIO": payload.get("portfolio_url", ""),
            "AFFICHAGE_PORTFOLIO": payload.get("portfolio_label", ""),
            "TITRE_SECTION_PROFIL": titles.get("profil", "Profile"),
            "RESUME_PROFESSIONNEL_CIBLE_AVEC_PREUVES_ET_MOTS_CLES": payload.get("resume", ""),
            "TITRE_SECTION_COMPETENCES": titles.get("competences", "Technical Skills"),
            "FAMILLE_COMPETENCE_1": comp[0][0], "COMPETENCES_PERTINENTES_1": comp[0][1],
            "FAMILLE_COMPETENCE_2": comp[1][0], "COMPETENCES_PERTINENTES_2": comp[1][1],
            "FAMILLE_COMPETENCE_3": comp[2][0], "COMPETENCES_PERTINENTES_3": comp[2][1],
            "FAMILLE_COMPETENCE_4": comp[3][0], "COMPETENCES_PERTINENTES_4": comp[3][1],
            "FAMILLE_COMPETENCE_5": comp[4][0], "COMPETENCES_PERTINENTES_5": comp[4][1],
            "PRECISION_HONNETE_SUR_COMPETENCE_EN_COURS": payload.get("precision", ""),
            "TITRE_SECTION_EXPERIENCES": titles.get("experiences", "Professional Experience"),
            "POSTE_1_REFORMULE": exps[0]["title"], "ENTREPRISE_1": exps[0]["company"], "DATES_ET_LIEU_1": exps[0]["dates"],
            "REALISATION_1_1_ALIGNEE_SUR_OFFRE": DocumentGenerationV2._bullet(exps[0], 0),
            "REALISATION_1_2_ALIGNEE_SUR_OFFRE": DocumentGenerationV2._bullet(exps[0], 1),
            "REALISATION_1_3_ALIGNEE_SUR_OFFRE": DocumentGenerationV2._bullet(exps[0], 2),
            "REALISATION_1_4_AVEC_RESULTAT": DocumentGenerationV2._bullet(exps[0], 3),
            "REALISATION_1_5_AVEC_RESULTAT": DocumentGenerationV2._bullet(exps[0], 4),
            "POSTE_2_REFORMULE": exps[1]["title"], "ENTREPRISE_2": exps[1]["company"], "DATES_ET_LIEU_2": exps[1]["dates"],
            "REALISATION_2_1_ALIGNEE_SUR_OFFRE": DocumentGenerationV2._bullet(exps[1], 0),
            "REALISATION_2_2_ALIGNEE_SUR_OFFRE": DocumentGenerationV2._bullet(exps[1], 1),
            "REALISATION_2_3_AVEC_RESULTAT": DocumentGenerationV2._bullet(exps[1], 2),
            "TITRE_SECTION_PROJET_CIBLE": titles.get("projet_cible", "Key Project"),
            "NOM_PROJET_CIBLE": payload.get("projet_cible", {}).get("name", ""),
            "PROBLEME_SOLUTION_TECHNOLOGIES_RESULTAT": payload.get("projet_cible", {}).get("description", ""),
            "STATUT_EVENTUEL": payload.get("projet_cible", {}).get("status", ""),
            "TITRE_SECTION_PROJETS_COMPLEMENTAIRES": titles.get("projets_complementaires", "Additional Project"),
            "NOM_PROJET_2": p2.get("name", ""),
            "DESCRIPTION_CIBLEE_PROJET_2_AVEC_PREUVE": p2.get("description", ""),
            "NOM_PROJET_3": "",
            "DESCRIPTION_CIBLEE_PROJET_3_AVEC_PREUVE": "",
            "TITRE_SECTION_FORMATION": titles.get("formation", "Education & Certifications"),
            "DIPLOME_1": diplomas[0][0], "ETABLISSEMENT_1": diplomas[0][1], "ANNEE_1": diplomas[0][2],
            "DIPLOME_2": diplomas[1][0], "ETABLISSEMENT_2": diplomas[1][1], "ANNEE_2": diplomas[1][2],
            "LABEL_CERTIFICATIONS": "Certifications:", "CERTIFICATIONS_PERTINENTES": formation.get("certifications", ""),
            "LABEL_LANGUES": "Languages:", "LANGUES": formation.get("langues", ""),
            "LABEL_DISPONIBILITE": "Availability:", "DISPONIBILITE": formation.get("disponibilite", ""),
        }

    @staticmethod
    def _letter_replacements(payload: dict) -> dict:
        paragraphs = payload.get("paragraphes", [])
        while len(paragraphs) < 4:
            paragraphs.append("")
        return {
            "NOM_COMPLET": payload.get("nom_complet", "Akim Guentas"),
            "INTITULE_POSTE": payload.get("intitule_cible", ""),
            "INTITULE_CIBLE": payload.get("intitule_cible", ""),
            "POSITIONNEMENT_DIFFERENCIANT": payload.get("positionnement", ""),
            "LOCALISATION": payload.get("localisation", "Paris"),
            "TELEPHONE": payload.get("telephone", ""),
            "EMAIL": payload.get("email", ""),
            "URL_LINKEDIN": payload.get("linkedin_url", ""),
            "AFFICHAGE_LINKEDIN": payload.get("linkedin_label", ""),
            "URL_GITHUB": payload.get("github_url", ""),
            "AFFICHAGE_GITHUB": payload.get("github_label", ""),
            "URL_PORTFOLIO": payload.get("portfolio_url", ""),
            "AFFICHAGE_PORTFOLIO": payload.get("portfolio_label", ""),
            "ENTREPRISE": payload.get("entreprise", ""),
            "DESTINATAIRE_OU_EQUIPE_RECRUTEMENT": payload.get("destinataire", "Équipe de recrutement"),
            "VILLE_ENTREPRISE": payload.get("ville", ""),
            "DATE_LETTRE": payload.get("date", ""),
            "LABEL_OBJET": "Objet :",
            "OBJET_CANDIDATURE": payload.get("objet", ""),
            "FORMULE_APPEL": payload.get("formule_appel", "Madame, Monsieur,"),
            "ACCROCHE_ANALYSE_DEUX_ENJEUX_MAJEURS": paragraphs[0],
            "OFFRE_DE_SERVICE_ENJEU_1_COMPETENCE_PREUVE_PROJECTION": paragraphs[1],
            "OFFRE_DE_SERVICE_ENJEU_2_COMPETENCE_PREUVE_PROJECTION": paragraphs[2],
            "SYNTHESE_VALEUR_ET_PROPOSITION_ENTRETIEN": paragraphs[3],
            "FORMULE_POLITESSE": payload.get("formule_politesse", ""),
            "SIGNATURE": payload.get("signature", "Akim Guentas"),
        }

    @staticmethod
    def _cv_prompt(analysis: dict, master_cv: dict) -> str:
        instructions = DocumentGenerationV2._read_instruction("cv_instructions.md")
        doctrine = DocumentGenerationV2._read_instruction("cv_prime_doctrine.md")
        return f"""{instructions}

CV Prime doctrine to apply before writing:
{doctrine}

Return JSON only. Fill the supplied targeted CV template indirectly through these keys:
nom_complet, intitule_cible, entreprise, mots_cles_differenciants, localisation,
telephone, email, linkedin_url, linkedin_label, github_url, github_label,
portfolio_url, portfolio_label, titres, resume, competences, precision,
experiences, projet_cible, projets_complementaires, formation.

Job analysis:
{json.dumps(analysis, ensure_ascii=False)}

Master CV source data:
{json.dumps(master_cv, ensure_ascii=False)[:24000]}
"""

    @staticmethod
    def _letter_prompt(analysis: dict, master_cv: dict) -> str:
        instructions = DocumentGenerationV2._read_instruction("letter_apec_instructions.md")
        return f"""{instructions}

Return JSON only with keys:
nom_complet, intitule_cible, positionnement, localisation, telephone, email,
linkedin_url, linkedin_label, github_url, github_label, portfolio_url,
portfolio_label, entreprise, destinataire, ville, date, objet, formule_appel,
paragraphes, formule_politesse, signature.

Job analysis:
{json.dumps(analysis, ensure_ascii=False)}

Master CV source data:
{json.dumps(master_cv, ensure_ascii=False)[:20000]}
"""

    @staticmethod
    def _require_keys(payload: dict, keys: set[str]) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise DocumentQualityError(f"Missing payload keys: {', '.join(missing)}")

    @staticmethod
    def _bullet(exp: dict, index: int) -> str:
        bullets = exp.get("bullets", [])
        return bullets[index] if index < len(bullets) else ""

    @staticmethod
    def _cv_prime_strategy(analysis: dict) -> dict:
        text = DocumentGenerationV2._analysis_text(analysis)
        marketing_markers = (
            "crm", "marketing", "digital performance", "kpi", "lead", "funnel",
            "nps", "customer feedback", "customer touchpoint", "power bi", "dashboard",
            "campaign", "sales activity", "commercial", "event"
        )
        if sum(1 for marker in marketing_markers if marker in text) >= 3:
            return {
                "family": "marketing_crm_bi",
                "positioning": "Data Marketing / CRM / BI",
            }
        return {
            "family": "data_engineering",
            "positioning": "Data pipelines / quality / production delivery",
        }

    @staticmethod
    def _analysis_text(analysis: dict) -> str:
        parts: list[str] = []
        for key in ("company", "job_title", "location", "contract_type", "description", "raw_offer"):
            parts.append(str(analysis.get(key, "")))
        for key in ("missions", "required_skills", "ats_keywords", "soft_skills"):
            value = analysis.get(key, [])
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            else:
                parts.append(str(value))
        return " ".join(parts).lower()

    @staticmethod
    def _vie_location(analysis: dict) -> str:
        text = DocumentGenerationV2._analysis_text(analysis)
        if "rio" in text:
            return "Rio de Janeiro"
        if "brazil" in text or "brésil" in text:
            return "Brazil"
        return "the target location"

    @staticmethod
    def _url(value: str, prefix: str) -> str:
        if not value:
            return ""
        if value.startswith(("http://", "https://")):
            return value
        return prefix + value

    @staticmethod
    def _language(analysis: dict) -> str:
        text = " ".join([
            str(analysis.get("job_title", "")),
            " ".join(analysis.get("missions", [])),
            " ".join(analysis.get("required_skills", [])),
        ]).lower()
        english_markers = ("build", "maintain", "pipeline", "deliver", "data quality", "engineer")
        return "en" if any(marker in text for marker in english_markers) else "fr"

    @staticmethod
    def _read_instruction(filename: str) -> str:
        path = DATA_DIR / filename
        return path.read_text(encoding="utf-8") if path.exists() else ""

    @staticmethod
    def _strip_reference_comments(html_doc: str) -> str:
        return re.sub(r"<!--.*?-->", "", html_doc, flags=re.S)
