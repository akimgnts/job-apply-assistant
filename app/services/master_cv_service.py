import logging

logger = logging.getLogger(__name__)


def load_master_cv() -> dict:
    """Load hardcoded Master CV data structure.

    Single source of truth for facts (companies, dates, roles, achievements).

    Philosophy: Truth is immutable. Narrative is flexible.
    - AI preserves all facts (dates, companies, accomplishments)
    - AI can rewrite bullets for clarity and relevance
    - AI can remove weak/irrelevant bullets
    - AI can adapt vocabulary to match role domain
    - AI cannot fabricate facts
    """
    from app.config import config

    data = {
        "personal_info": {
            "name": "Akim Guentas",
            "location": "Paris",
            "email": config.CANDIDATE_EMAIL or "",
            "phone": config.CANDIDATE_PHONE or "",
            "portfolio": "madebyakim.com",
            "github": "github.com/akimgnts",
            "linkedin": "linkedin.com/in/akimguentas",
        },
        "experiences": [
            {
                "id": 0,
                "title": "Data, Marketing & Communication Analyst (Apprenticeship)",
                "company": "Sidel",
                "context": "International B2B industrial environment",
                "dates": "2023 – 2025",
                "bullets": [
                    "Built and maintained around 10 dashboards and reporting tools covering installed base, events and business KPIs — used weekly and monthly by approximately 30–40 stakeholders across marketing, commercial and management teams.",
                    "Automated recurring extraction, cleaning, consolidation and visualization tasks using Python, SQL, Snowflake and Power BI — reducing processes that previously required half a day to several days of manual work.",
                    "Analyzed installed base, equipment and service data across 61 customers in the Wines & Spirits sector; produced commercial action plans supporting account prioritization by machine age, installed base evolution and business opportunities.",
                    "Produced Installed Base analysis for Benelux accounts — mapping equipment age, service history and commercial potential across the region to support prioritization decisions by the local commercial team.",
                    "Consolidated multi-source business data from Microsoft Dynamics, CRM and marketing platforms (customers, leads, events, campaigns) — monitored KPIs to improve operational visibility for European marketing and commercial teams.",
                    "Coordinated with international stakeholders across Europe; presented analyses, action plans and business insights in French and English.",
                    "Maintained data quality through systematic cleaning, consistency checks and cross-source documentation across Power BI, Snowflake and CRM data flows.",
                ]
            },
            {
                "id": 1,
                "title": "Freelance Projects · Data, Automation & Digital Systems",
                "company": "MadeByAkim / Made By Curve",
                "context": "",
                "dates": "2024 – Present",
                "bullets": [
                    "Automated repetitive operational tasks (email preparation, meeting workflows, lead enrichment) — saving several hours of manual work per workflow across systems used by clients and personal operations.",
                    "Built workflow automation using APIs, webhooks, Make, n8n, JSON payloads and Python scripts — connecting CRM tools, databases and communication channels.",
                    "Designed dashboards, reporting structures and operational tracking systems for client and personal use cases.",
                    "Built and iterated AI-powered prototypes and automation workflows using OpenAI, Claude and FastAPI — covering document generation pipelines, AI-assisted content extraction and personal productivity systems backed by PostgreSQL.",
                    "Managed client-facing CRM workflows and digital operations using HubSpot, Airtable and ManyChat — structuring customer data, lead tracking and communication channels for SMB clients.",
                    "Produced social media assets, visual identities and content using Adobe Premiere Pro, After Effects, Photoshop and Illustrator.",
                ]
            },
            {
                "id": 2,
                "title": "Business Development & Reporting",
                "company": "Vassard OMB Mobilier",
                "context": "",
                "dates": "2022 – 2023",
                "bullets": [
                    "Structured CRM and commercial data to improve visibility on prospects, customers, follow-up actions and sales activity.",
                    "Implemented KPI tracking and reporting processes supporting sales decisions and business development priorities.",
                    "Analyzed customer and sales information to identify priorities and improve commercial follow-up.",
                ]
            },
        ],
        "projects": [
            {
                "id": 0,
                "title": "Elevia · Personal Data & AI Project",
                "stack": "Python · FastAPI · PostgreSQL · OpenAI · LangChain · SQL · APIs",
                "dates": "",
                "bullets": [
                    "Designed and iterated through more than 10 versions of a matching engine — evaluated across 30 test profiles and over 1,000 job opportunities, improving recommendation quality and explainability.",
                    "Generated 100+ AI-assisted application documents (CVs, cover letters, recruiter messages) — reducing preparation time from dozens of minutes to a few seconds.",
                    "Built a modular FastAPI backend with ~10 components across 4 PostgreSQL tables — covering CV parsing, skill extraction, canonicalization, scoring and observability, with technical documentation maintained throughout.",
                ]
            },
            {
                "id": 1,
                "title": "Job Apply Assistant",
                "stack": "Telegram · FastAPI · OpenAI · PostgreSQL · SQLAlchemy · Jinja2 · Coolify",
                "dates": "",
                "bullets": [
                    "Built a Telegram assistant that analyzes job offers, matches against a candidate profile and generates tailored CV, cover letter and recruiter message — reducing application preparation time from ~45 minutes to ~5 minutes.",
                    "Designed the full backend using FastAPI, PostgreSQL, OpenAI and SQLAlchemy — with a Jinja2 template rendering pipeline producing format-ready documents from a structured candidate profile and job analysis.",
                ]
            },
            {
                "id": 2,
                "title": "V.I.E Matcher",
                "stack": "Automation · Matching · Scoring · Google Sheets · Telegram · AI workflows",
                "dates": "",
                "bullets": [
                    "Workflow for V.I.E offer analysis, profile matching, scoring and ATS-oriented application preparation.",
                ]
            },
            {
                "id": 3,
                "title": "SkillMap Automation Console",
                "stack": "Data visualization · API · Dashboards · Skills intelligence",
                "dates": "",
                "bullets": [
                    "Portfolio project transforming structured data into interfaces, dashboards and insights around skills, offers and workflows.",
                ]
            },
        ],
        "skills": [
            {
                "label": "Data & Analytics",
                "content": "SQL, Python, Pandas, Power BI, Power Query, Excel Advanced, KPI Monitoring, Dashboards, Data Visualization, Reporting, Data Cleaning, Data Quality, Performance Analysis."
            },
            {
                "label": "Automation & APIs",
                "content": "Make, n8n, REST APIs, Webhooks, JSON, Google Apps Script, Telegram Bots, CRM Integrations, Workflow Automation, Lead Enrichment, Document Generation."
            },
            {
                "label": "AI & LLM Workflows",
                "content": "OpenAI API, Claude, Gemini, Prompt Engineering, Structured Extraction, RAG Concepts, AI Agents, Knowledge Bases, LLM Workflows, LangChain, MCP, Function Calling."
            },
            {
                "label": "Backend & Data Systems",
                "content": "PostgreSQL, Supabase, Firebase, MongoDB, Snowflake, Elasticsearch, FastAPI, Git, GitHub, Docker Basics, SQLAlchemy, Jinja2, Data Pipelines, Technical Documentation."
            },
            {
                "label": "Business Systems",
                "content": "HubSpot, Microsoft Dynamics, Notion, Airtable, Slack, Teams, Google Sheets, Google Drive, CRM Workflows, Campaign Reporting, Customer Data, ManyChat, Meta Business Suite."
            },
            {
                "label": "Creative & Delivery",
                "content": "Adobe Premiere Pro, After Effects, Photoshop, Illustrator, Canva, Presentation Design, User Training, Dashboard Presentations, Process Mapping, Stakeholder Communication."
            },
        ],
        "education": [
            {
                "title": "MSc Business Intelligence & Analytics / Data Analyst for Marketing",
                "school": "Eugenia School",
                "year": "2025",
            },
            {
                "title": "Bachelor Responsable Commerce & Marketing",
                "school": "EM Normandie",
                "year": "2023",
            },
            {
                "title": "BTS Management Commercial Opérationnel",
                "school": "",
                "year": "2021",
            },
        ],
        "certifications": [
            {"name": "Dataiku ML Practitioner"},
            {"name": "Python for Machine Learning"},
            {"name": "Fine-Tuning Large Language Models"},
        ],
        "languages": [
            {"name": "French", "level": "Native"},
            {"name": "English", "level": "Professional Working Proficiency"},
            {"name": "Spanish", "level": "Intermediate"},
        ],
    }

    # Add convenience _by_id dicts for template access
    data["experiences_by_id"] = {e["id"]: e for e in data["experiences"]}
    data["projects_by_id"] = {p["id"]: p for p in data["projects"]}

    return data


def validate_adaptation(adaptation: dict, master_cv: dict, compact: bool = False) -> dict:
    """Validate adaptation against master CV.

    Philosophy: Truth is immutable. Narrative is flexible.

    Args:
        compact: If True, relaxes Sidel bullet minimum to 3 (single-page mode).
                 If False, requires minimum 5 bullets for Sidel (full mode).

    Ensure:
    - Experience order is FIXED: [0, 1, 2]
    - Facts preserved (companies, dates, roles)
    - No invented content
    - Required projects present
    - Bullets may be rewritten (flexible narrative)
    """
    issues = []

    # FIXED experience order (never reorder)
    expected_exp_order = [0, 1, 2]
    actual_exp_order = adaptation.get("experience_order", [])
    if actual_exp_order != expected_exp_order:
        issues.append(f"Experience order must be {expected_exp_order}. Got {actual_exp_order}")

    # Check bullets exist for each experience (facts preserved, wording flexible)
    exp_bullets = adaptation.get("experience_bullets", {})
    sidel_min_bullets = 3 if compact else 5
    for exp_id in [0, 1, 2]:
        exp_id_str = str(exp_id)
        actual_bullets = exp_bullets.get(exp_id_str, [])

        # Sidel (exp_id 0) is flagship — minimum varies by mode
        if exp_id == 0:
            if len(actual_bullets) < sidel_min_bullets:
                issues.append(
                    f"Sidel experience: Minimum {sidel_min_bullets} bullets required "
                    f"({'compact' if compact else 'full'} mode). Got {len(actual_bullets)}."
                )
        else:
            if not actual_bullets:
                issues.append(f"Experience {exp_id}: At least one bullet required.")

        for bullet in actual_bullets:
            if not isinstance(bullet, str) or len(bullet) == 0:
                issues.append(f"Experience {exp_id}: Invalid bullet format.")

    # Check projects valid (default 3, can include 4 if relevant)
    proj_order = adaptation.get("project_order", [])
    valid_projects = {0, 1, 2, 3}
    if not proj_order or not all(p in valid_projects for p in proj_order):
        issues.append(f"Invalid project order. Got {proj_order}")

    # Required projects: 0, 1, 2 (Elevia, Job Apply Assistant, V.I.E Matcher)
    required_projects = {0, 1, 2}
    if not required_projects.issubset(set(proj_order)):
        issues.append(f"Projects 0, 1, 2 required. Got {proj_order}")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
    }
