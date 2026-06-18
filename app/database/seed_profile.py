from app.database.db import SessionLocal, engine, Base
from app.database.models import ProfileBlock, CategoryEnum, TruthLevelEnum

PROFILE_BLOCKS = [
    # -------------------------------------------------------------------------
    # IDENTITY
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.skill,
        "title": "Identité professionnelle — AI Builder",
        "content": (
            "AI Builder with a strong Data & Analytics foundation. Business-oriented profile "
            "combining data analysis, automation, reporting and AI workflows. Comfortable "
            "translating business needs into practical systems, tools and decision-support solutions. "
            "Core values: curiosity, continuous learning, delivery, experimentation, business value, "
            "simplicity, continuous improvement. "
            "Positioning: AI Builder focused on building practical systems by combining data, "
            "automation and LLM workflows."
        ),
        "tags": ["identity", "positioning", "ai", "data", "automation", "business_value", "delivery"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 10,
    },

    # -------------------------------------------------------------------------
    # EXPERIENCES
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.experience,
        "title": "Sidel — Data, Reporting & Business Operations",
        "content": (
            "Data, reporting and business operations experience within an international B2B industrial environment. "
            "Responsibilities: customer and installed base analysis, lead tracking and campaign monitoring, "
            "KPI monitoring and dashboard creation, multi-source reporting, data quality and consistency checks, "
            "internal communication and content support, collaboration with European marketing and commercial teams, "
            "stakeholder presentations, process improvement and documentation. "
            "Tools: Excel, Power BI, Power Query, Python, SQL, Snowflake, Microsoft Dynamics. "
            "Soft skills: stakeholder communication, cross-functional collaboration, business understanding, "
            "analytical thinking."
        ),
        "tags": [
            "data", "reporting", "powerbi", "excel", "sql", "python", "snowflake",
            "dynamics", "kpi", "dashboards", "b2b", "international", "stakeholders",
            "data_quality", "power_query",
        ],
        "truth_level": TruthLevelEnum.verified,
        "priority": 10,
    },
    {
        "category": CategoryEnum.experience,
        "title": "Vassard OMB Mobilier — Business Development & Reporting",
        "content": (
            "Business development and reporting experience. "
            "Responsibilities: CRM structuring, sales activity reporting, KPI tracking, "
            "customer analysis, commercial process improvement, decision support."
        ),
        "tags": ["crm", "reporting", "kpi", "business_development", "sales", "data_analysis"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },
    {
        "category": CategoryEnum.experience,
        "title": "MadeByAkim — Freelance Data, Automation & AI",
        "content": (
            "Freelance activity and personal systems around data, automation and AI workflows. "
            "Responsibilities: workflow automation, APIs and webhook integrations, reporting systems, "
            "document generation, CRM workflows, database structuring, AI-assisted systems, "
            "documentation, user support, process improvement. "
            "Stack: Python, SQL, OpenAI, Claude, Gemini, Make, n8n, PostgreSQL, Supabase, Firebase, "
            "MongoDB, Airtable, Notion, HubSpot, Slack, Teams, Google Sheets, APIs, Webhooks. "
            "Soft skills: autonomy, curiosity, delivery, rapid prototyping, communication, continuous learning."
        ),
        "tags": [
            "automation", "python", "sql", "openai", "claude", "make", "n8n",
            "postgresql", "supabase", "firebase", "mongodb", "airtable", "notion",
            "hubspot", "apis", "webhooks", "reporting", "document_generation",
            "crm", "freelance", "ai",
        ],
        "truth_level": TruthLevelEnum.verified,
        "priority": 9,
    },

    # -------------------------------------------------------------------------
    # PROJECTS
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.project,
        "title": "Elevia — AI Matching Platform",
        "content": (
            "AI platform dedicated to professional matching and career intelligence. "
            "Domains: CV parsing, skill extraction, canonicalization, matching, scoring, "
            "explainability, document generation, data quality, observability. "
            "Stack: Python, FastAPI, PostgreSQL, Git, OpenAI, Claude. "
            "Concepts: AI agents, structured extraction, pipelines, testing, explainability, "
            "continuous improvement."
        ),
        "tags": [
            "ai", "matching", "fastapi", "postgresql", "cv_parsing", "skills",
            "scoring", "explainability", "document_generation", "openai", "claude",
            "agents", "pipelines", "data_quality",
        ],
        "truth_level": TruthLevelEnum.in_progress,
        "priority": 10,
    },
    {
        "category": CategoryEnum.project,
        "title": "Job Apply Assistant — Telegram AI Assistant",
        "content": (
            "Telegram assistant automating job applications. "
            "Features: offer analysis, positioning, CV generation, cover letter generation, "
            "recruiter message generation. "
            "Stack: Telegram, OpenAI, PostgreSQL, SQLAlchemy, Jinja2, Coolify."
        ),
        "tags": [
            "telegram", "openai", "postgresql", "sqlalchemy", "jinja2",
            "automation", "cv_generation", "job_application", "ai",
        ],
        "truth_level": TruthLevelEnum.in_progress,
        "priority": 9,
    },
    {
        "category": CategoryEnum.project,
        "title": "V.I.E Matcher — Workflow Automation",
        "content": (
            "Workflow dedicated to V.I.E opportunity analysis and application preparation. "
            "Domains: matching, scoring, workflow automation, offer analysis. "
            "Stack: Make, GPT-4o, Google Sheets, Telegram."
        ),
        "tags": ["make", "gpt4o", "google_sheets", "telegram", "automation", "matching", "scoring", "vie"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },
    {
        "category": CategoryEnum.project,
        "title": "V.I.E Career Intelligence Assistant",
        "content": (
            "Conversational assistant connected to career intelligence workflows. "
            "Domains: AI assistant, market insights, CV analysis, matching. "
            "Stack: n8n, PostgreSQL, Telegram, OpenAI."
        ),
        "tags": ["n8n", "postgresql", "telegram", "openai", "ai_assistant", "career", "matching", "vie"],
        "truth_level": TruthLevelEnum.in_progress,
        "priority": 8,
    },
    {
        "category": CategoryEnum.project,
        "title": "Hackathon — AI Personalization & Workflows",
        "content": (
            "Collaborative project built with partner companies around AI-powered personalization "
            "and workflows. "
            "Domains: segmentation, personalization, campaign generation, workflow design. "
            "Stack: Make, Mistral."
        ),
        "tags": ["make", "mistral", "segmentation", "personalization", "campaign_generation", "hackathon"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 7,
    },

    # -------------------------------------------------------------------------
    # EDUCATION
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.education,
        "title": "MSc Business Intelligence & Analytics",
        "content": (
            "Master of Science in Business Intelligence & Analytics. "
            "Specialization: Business Intelligence, Analytics, data analysis, marketing analytics, "
            "business problems."
        ),
        "tags": ["business_intelligence", "analytics", "data_analysis", "marketing", "msc"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },
    {
        "category": CategoryEnum.education,
        "title": "Bachelor Business Development & Marketing",
        "content": "Bachelor in Business Development & Marketing. Business, sales and communication foundations.",
        "tags": ["business_development", "marketing", "sales", "communication", "bachelor"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 6,
    },
    {
        "category": CategoryEnum.education,
        "title": "BTS Management Commercial Opérationnel",
        "content": "BTS MCO — Operational and commercial fundamentals.",
        "tags": ["bts", "management", "commercial", "operations"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 5,
    },

    # -------------------------------------------------------------------------
    # SKILLS
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.skill,
        "title": "Compétences Data",
        "content": (
            "Python, SQL, Pandas, Power BI, Power Query, Excel, KPI monitoring, dashboards, "
            "reporting, data visualization, data cleaning, data quality, business analysis, "
            "performance analysis."
        ),
        "tags": [
            "python", "sql", "pandas", "powerbi", "power_query", "excel",
            "kpi", "dashboards", "reporting", "dataviz", "data_quality",
            "business_analysis",
        ],
        "truth_level": TruthLevelEnum.verified,
        "priority": 10,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Compétences AI & LLM",
        "content": (
            "OpenAI, Claude, Gemini, prompt engineering, structured extraction, AI agents, "
            "RAG concepts, knowledge bases, document generation, LLM workflows."
        ),
        "tags": [
            "openai", "claude", "gemini", "prompt_engineering", "structured_extraction",
            "ai_agents", "rag", "knowledge_bases", "document_generation", "llm_workflows",
        ],
        "truth_level": TruthLevelEnum.project,
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Compétences Automatisation",
        "content": (
            "Make, n8n, REST APIs, webhooks, JSON, Google Apps Script, "
            "workflow automation, lead enrichment."
        ),
        "tags": ["make", "n8n", "rest_api", "webhooks", "json", "google_apps_script", "automation", "lead_enrichment"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Backend & Data Systems",
        "content": (
            "FastAPI, PostgreSQL, Supabase, Firebase, MongoDB, Snowflake, Elasticsearch, "
            "SQLAlchemy, Git, GitHub, Docker basics, data pipelines, technical documentation."
        ),
        "tags": [
            "fastapi", "postgresql", "supabase", "firebase", "mongodb", "snowflake",
            "elasticsearch", "sqlalchemy", "git", "docker", "pipelines",
        ],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Business Systems",
        "content": (
            "HubSpot, Microsoft Dynamics, Notion, Airtable, Slack, Teams, "
            "Google Sheets, Google Drive, CRM workflows."
        ),
        "tags": ["hubspot", "dynamics", "notion", "airtable", "slack", "teams", "google_sheets", "crm"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Delivery & Communication",
        "content": (
            "Workshops, demos, dashboard presentations, user training, documentation, "
            "process mapping, stakeholder communication, rapid prototyping, product thinking, "
            "continuous improvement."
        ),
        "tags": [
            "workshops", "demos", "presentations", "training", "documentation",
            "process_mapping", "stakeholder_communication", "prototyping", "product_thinking",
        ],
        "truth_level": TruthLevelEnum.verified,
        "priority": 9,
    },

    # -------------------------------------------------------------------------
    # LANGUAGES
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.language,
        "title": "Langues",
        "content": "French — Native. English — Professional Working Proficiency (C1). Spanish — Intermediate.",
        "tags": ["french", "english", "spanish", "c1"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },

    # -------------------------------------------------------------------------
    # CERTIFICATIONS
    # -------------------------------------------------------------------------
    {
        "category": CategoryEnum.certification,
        "title": "Certifications",
        "content": (
            "Dataiku ML Practitioner. Python for Machine Learning. "
            "Fine-Tuning Large Language Models."
        ),
        "tags": ["dataiku", "machine_learning", "python", "llm", "fine_tuning", "certification"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 7,
    },
]


def seed_profile(force: bool = False):
    """Seed profile blocks. Use force=True to replace existing blocks."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_count = db.query(ProfileBlock).count()

        if existing_count > 0 and not force:
            print(f"Profile already seeded ({existing_count} blocks). Use force=True to replace.")
            return

        if existing_count > 0 and force:
            db.query(ProfileBlock).delete()
            db.commit()
            print(f"Cleared {existing_count} existing blocks.")

        for block_data in PROFILE_BLOCKS:
            block = ProfileBlock(**block_data)
            db.add(block)
        db.commit()
        print(f"✓ Seeded {len(PROFILE_BLOCKS)} profile blocks")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    seed_profile(force=force)
