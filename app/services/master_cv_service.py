import logging

logger = logging.getLogger(__name__)


def load_master_cv() -> dict:
    """Load hardcoded Master CV data structure.

    This is the single source of truth for CV content.
    Never modified by AI, only adapted.
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
                    "Consolidated and analyzed multi-source business data related to customers, installed base, leads, events and marketing activity.",
                    "Monitored KPIs, lead tracking and business indicators to improve visibility for internal stakeholders.",
                    "Structured and maintained reporting supports for marketing, communication and commercial teams using Excel, Power BI and Power Query.",
                    "Supported data quality through cleaning, consistency checks, documentation and structured reporting processes.",
                    "Coordinated with European marketing, communication and sales stakeholders in an international B2B environment.",
                    "Presented business insights through dashboards, campaign reporting and communication assets for internal and external stakeholders.",
                    "Analyzed business data using Python, SQL, Snowflake, Excel and Power BI to support decision-making and operational excellence.",
                ]
            },
            {
                "id": 1,
                "title": "Freelance Projects · Data, Automation & Digital Systems",
                "company": "MadeByAkim / Made By Curve",
                "context": "",
                "dates": "2024 – Present",
                "bullets": [
                    "Built freelance and personal projects around automation, reporting, content production, CRM workflows and digital systems.",
                    "Worked on workflow automation using APIs, webhooks, Make, n8n, JSON payloads and lightweight Python scripts.",
                    "Created dashboards, reporting structures, lead generation workflows and operational tracking systems.",
                    "Used ManyChat, Meta Business Suite, CRM tools, Airtable, Notion, Google Sheets and automation tools to support digital workflows.",
                    "Produced social media assets, visual identities, presentations and content using Adobe Photoshop, Illustrator, Premiere Pro and After Effects.",
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
                    "Personal project in development around CV parsing, skills extraction, canonicalization, scoring, matching, explainability, data quality, observability and AI-assisted document generation.",
                ]
            },
            {
                "id": 1,
                "title": "Job Apply Assistant",
                "stack": "Telegram · OpenAI · PostgreSQL · Jinja2 · SQLAlchemy · Coolify",
                "dates": "",
                "bullets": [
                    "Telegram assistant that analyzes job offers, compares them with a candidate profile, proposes positioning and generates adapted CV, letter and recruiter message.",
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
                "content": "OpenAI API, Claude, Gemini, Prompt Engineering, Structured Extraction, RAG Concepts, AI Agents, Knowledge Bases, LLM Workflows, LangChain."
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


def validate_adaptation(adaptation: dict, master_cv: dict) -> dict:
    """Validate adaptation against master CV.

    Ensure:
    - Experience order is FIXED: [0, 1, 2]
    - ALL bullets present (no deletion or creation)
    - ALL projects present
    - No bullet rewriting (content unchanged)
    """
    issues = []

    # FIXED experience order (never reorder)
    expected_exp_order = [0, 1, 2]
    actual_exp_order = adaptation.get("experience_order", [])
    if actual_exp_order != expected_exp_order:
        issues.append(f"Experience order must be {expected_exp_order}. Got {actual_exp_order}")

    # Check all bullets present (no deletion, no creation)
    exp_bullets = adaptation.get("experience_bullets", {})
    for exp_id in [0, 1, 2]:
        exp_id_str = str(exp_id)
        master_bullets = master_cv["experiences"][exp_id].get("bullets", [])
        actual_bullets = exp_bullets.get(exp_id_str, [])

        if len(actual_bullets) != len(master_bullets):
            issues.append(
                f"Experience {exp_id}: Expected {len(master_bullets)} bullets, "
                f"got {len(actual_bullets)}. Bullets must not be deleted or added."
            )

        # Check bullet content unchanged
        for i, (expected, actual) in enumerate(zip(master_bullets, actual_bullets)):
            if actual != expected:
                issues.append(
                    f"Experience {exp_id} bullet {i}: Bullet rewritten. "
                    f"Must use original content unchanged."
                )

    # Check projects valid (default 3, can include 4 if relevant)
    proj_order = adaptation.get("project_order", [])
    valid_projects = {0, 1, 2, 3}
    if not proj_order or not all(p in valid_projects for p in proj_order):
        issues.append(f"Invalid project order. Got {proj_order}")
    # SkillMap (3) optional; Elevia, Job Apply Assistant, V.I.E Matcher (0,1,2) required
    required_projects = {0, 1, 2}
    if not required_projects.issubset(set(proj_order)):
        issues.append(f"Projects 0, 1, 2 (Elevia, Job Apply Assistant, V.I.E Matcher) required. Got {proj_order}")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
    }
