"""Master V3 Atomic Profile Blocks - Source-of-Truth.

Each block carries only its own verified facts:
- Technologies/tools actually used for THIS block
- Metrics measured for THIS specific achievement
- Proficiency level based on THIS block's usage
- Status reflecting THIS block's real state

Philosophy: Allowlist-first. "Voici ce qui est affirmable."
Then forbidden_claims adds guardrails.

From: app/services/master_cv_service.py
"""
from app.database.db import SessionLocal, engine, Base
from app.database.models import (
    ProfileBlock, CategoryEnum, TruthLevelEnum,
    ProficiencyLevelEnum, BlockStatusEnum
)

PROFILE_BLOCKS_ATOMIC_V3 = [
    # =========================================================================
    # IDENTITY & POSITIONING
    # =========================================================================
    {
        "category": CategoryEnum.skill,
        "title": "Positioning — AI Builder with Data & Analytics foundation",
        "content": (
            "AI Builder focused on building practical systems by combining data, automation, "
            "and LLM workflows. Strong Data & Analytics foundation. Business-oriented. "
            "Location: Paris. Links: madebyakim.com | linkedin.com/in/akimguentas | github.com/akimgnts"
        ),
        "tags": ["positioning", "identity", "ai", "data", "automation", "business_value"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:identity",
        "priority": 10,
    },

    # =========================================================================
    # SIDEL EXPERIENCE (2023–2025) — ATOMIZED
    # =========================================================================
    {
        "category": CategoryEnum.experience,
        "title": "Sidel — Role: Data, Marketing & Communication Analyst (Apprenticeship)",
        "content": (
            "Data, Marketing & Communication Analyst apprenticeship (2023–2025) in international "
            "B2B industrial environment. Role covered: customer analysis, installed base analysis, "
            "lead tracking, campaign monitoring, KPI monitoring, dashboard creation, multi-source "
            "reporting, data quality, stakeholder collaboration, documentation."
        ),
        "tags": ["sidel", "role", "b2b", "international"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.completed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "source_ref": "master_v3:sidel_identity",
        "priority": 10,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Sidel — Dashboard Portfolio: Installed Base, Events, Business KPIs",
        "content": (
            "Built and maintained ~10 dashboards and reporting tools covering installed base, "
            "events and business KPIs. Used weekly and monthly by ~30–40 stakeholders across "
            "marketing, commercial and management teams. Impact: increased visibility on key "
            "business indicators, improved monitoring of activities and priorities, facilitated "
            "decision-making through structured reporting."
        ),
        "tags": ["sidel", "dashboards", "kpi", "reporting", "stakeholders"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "technologies": ["Power BI", "Power Query", "Excel"],
        "job_families": ["Data Analyst", "BI Analyst", "Business Analyst"],
        "metrics": {
            "dashboards": "~10",
            "stakeholders": "~30–40",
            "frequency": "Weekly and monthly"
        },
        "forbidden_claims": [
            "Do not claim specific dashboard names without evidence",
            "Do not change ~30–40 to an exact number",
            "Do not claim automated beyond Power BI capabilities"
        ],
        "source_ref": "master_v3:sidel_dashboard_portfolio",
        "priority": 10,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Sidel — Data Automation: Extraction, Cleaning, Consolidation",
        "content": (
            "Automated recurring extraction, cleaning, consolidation and visualization tasks. "
            "Previous manual processes required half a day to several days depending on analysis. "
            "Impact: reduced repetitive work, accelerated reporting activities, improved consistency "
            "and reliability of business analyses."
        ),
        "tags": ["sidel", "automation", "extraction", "cleaning", "consolidation"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "technologies": ["Python", "SQL", "Power BI"],
        "job_families": ["Data Analyst", "Data Engineer", "Analytics Engineer"],
        "metrics": {
            "before": "Half a day to several days of manual work",
            "after": "Automated",
            "impact": "Reduced repetitive work, accelerated reporting"
        },
        "forbidden_claims": [
            "Do not claim specific time reduction percentage",
            "Do not claim full automation without caveats",
            "Do not claim zero manual intervention"
        ],
        "source_ref": "master_v3:sidel_reporting_automation",
        "priority": 10,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Sidel — Installed Base Analysis: Wines & Spirits, 61 Customers",
        "content": (
            "Analyzed installed base, equipment and service data across 61 customers in the "
            "Wines & Spirits sector. Produced commercial action plans helping teams prioritize "
            "accounts by machine age, installed base evolution and business opportunities. "
            "Impact: improved customer visibility, supported account prioritization, enabled "
            "proactive commercial actions and business monitoring."
        ),
        "tags": ["sidel", "installed_base", "wines_spirits", "customer_analysis"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "technologies": ["SQL", "Power BI", "Excel"],
        "job_families": ["Data Analyst", "Business Analyst"],
        "metrics": {
            "customers": "61",
            "sector": "Wines & Spirits"
        },
        "forbidden_claims": [
            "Do not change 61 customers to another number",
            "Do not claim full predictive modeling",
            "Do not invent customer revenue impact"
        ],
        "source_ref": "master_v3:sidel_installed_base_analytics",
        "priority": 9,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Sidel — Data Consolidation: Multi-Source Business Data",
        "content": (
            "Consolidated multi-source business data (customers, leads, events, campaigns) and "
            "monitored KPIs to improve operational visibility for European marketing and commercial "
            "teams. Integration of diverse data sources, structured KPI tracking."
        ),
        "tags": ["sidel", "consolidation", "kpi", "europe"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "technologies": ["SQL", "Power BI", "Excel"],
        "job_families": ["Data Analyst", "Data Engineer"],
        "forbidden_claims": [
            "Do not claim fully automated consolidation",
            "Do not invent data quality metrics"
        ],
        "source_ref": "master_v3:sidel_data_consolidation",
        "priority": 8,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Sidel — International Collaboration: Europe, French & English",
        "content": (
            "Coordinated with international stakeholders across Europe. Presented analyses, "
            "action plans and business insights in French and English. Led meetings and discussions "
            "depending on project requirements. Impact: improved communication between teams, "
            "increased alignment around priorities and business objectives, supported cross-functional "
            "decision-making."
        ),
        "tags": ["sidel", "international", "communication", "europe"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "job_families": ["Data Analyst", "Business Analyst"],
        "forbidden_claims": [
            "Do not claim translation of technical content",
            "Do not claim native English proficiency"
        ],
        "source_ref": "master_v3:sidel_international_collaboration",
        "priority": 7,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Sidel — Data Quality: Structured Cleaning & Consistency Checks",
        "content": (
            "Supported data quality through structured cleaning, consistency checks and documentation "
            "across multi-source reporting processes. Ensured data reliability and trustworthiness "
            "in business reporting pipelines."
        ),
        "tags": ["sidel", "data_quality", "consistency", "documentation"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Sidel",
        "start_date": "2023",
        "end_date": "2025",
        "technologies": ["SQL", "Excel"],
        "job_families": ["Data Analyst", "Data Engineer"],
        "forbidden_claims": [
            "Do not claim 100% data coverage",
            "Do not claim zero errors"
        ],
        "source_ref": "master_v3:sidel_data_quality",
        "priority": 7,
    },

    # =========================================================================
    # MADEBYAKIM EXPERIENCE (2024–Present) — ATOMIZED
    # =========================================================================
    {
        "category": CategoryEnum.experience,
        "title": "MadeByAkim — Freelance: Data, Automation & Digital Systems",
        "content": (
            "Freelance projects and personal systems around data, automation and AI workflows "
            "(2024–Present). Building operational systems, automating repetitive tasks, integrating "
            "tools, designing dashboards, structuring CRM workflows and managing digital operations."
        ),
        "tags": ["freelance", "madebyakim", "automation", "ai"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.in_progress,
        "company": "MadeByAkim",
        "start_date": "2024",
        "source_ref": "master_v3:madebyakim_identity",
        "priority": 9,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "MadeByAkim — Workflow Automation: Email, Meetings, Lead Enrichment",
        "content": (
            "Automated repetitive operational tasks such as email preparation, meeting workflows, "
            "and lead enrichment. Saved several hours of manual work per workflow across systems "
            "used by clients and personal operations."
        ),
        "tags": ["madebyakim", "automation", "workflow", "efficiency"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "MadeByAkim",
        "start_date": "2024",
        "technologies": ["Make", "n8n", "Python", "Google Apps Script"],
        "job_families": ["Automation Engineer", "Integration Engineer"],
        "metrics": {
            "impact": "Several hours of manual work saved per workflow"
        },
        "forbidden_claims": [
            "Do not claim specific hour counts without evidence",
            "Do not claim 100% automation"
        ],
        "source_ref": "master_v3:madebyakim_automation_workflows",
        "priority": 9,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "MadeByAkim — API & Webhook Integration: CRM, Database, Communication",
        "content": (
            "Built workflow automation using APIs, webhooks, Make, n8n, JSON payloads and Python "
            "scripts — connecting CRM tools, databases and communication channels. Designed integrations "
            "for operational efficiency."
        ),
        "tags": ["madebyakim", "apis", "webhooks", "integration"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "MadeByAkim",
        "start_date": "2024",
        "technologies": ["REST APIs", "Webhooks", "JSON", "Make", "n8n", "Python"],
        "job_families": ["Automation Engineer", "Integration Engineer", "Backend Engineer"],
        "forbidden_claims": [
            "Do not claim complex API authentication without proof",
            "Do not claim error recovery without implementation"
        ],
        "source_ref": "master_v3:madebyakim_api_webhooks",
        "priority": 9,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "MadeByAkim — Dashboards & Reporting: Operational Tracking Systems",
        "content": (
            "Designed dashboards, reporting structures and operational tracking systems for client "
            "and personal use cases. Created visibility into workflows, metrics and business operations."
        ),
        "tags": ["madebyakim", "dashboards", "reporting", "tracking"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "MadeByAkim",
        "start_date": "2024",
        "technologies": ["Google Sheets", "Airtable"],
        "job_families": ["Data Analyst", "BI Analyst"],
        "forbidden_claims": [
            "Do not claim advanced BI tool expertise",
            "Do not claim real-time processing"
        ],
        "source_ref": "master_v3:madebyakim_dashboards",
        "priority": 8,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "MadeByAkim — CRM Systems: HubSpot, ManyChat, Airtable, Notion, Google Sheets",
        "content": (
            "Structured CRM workflows and digital operations using ManyChat, Meta Business Suite, "
            "HubSpot, Airtable, Notion and Google Sheets. Designed workflows for lead management, "
            "customer data organization and campaign tracking."
        ),
        "tags": ["madebyakim", "crm", "systems", "workflow"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "MadeByAkim",
        "start_date": "2024",
        "technologies": ["ManyChat", "Meta Business Suite", "HubSpot", "Airtable", "Notion", "Google Sheets"],
        "job_families": ["CRM Administrator", "Automation Engineer"],
        "forbidden_claims": [
            "Do not claim deep HubSpot development",
            "Do not claim sophisticated AI in ManyChat"
        ],
        "source_ref": "master_v3:madebyakim_crm_systems",
        "priority": 8,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "MadeByAkim — Creative Content: Adobe Suite, Canva, Visual Design",
        "content": (
            "Produced social media assets, visual identities and content using Adobe Premiere Pro, "
            "After Effects, Photoshop and Illustrator. Created visual branding and multimedia content."
        ),
        "tags": ["madebyakim", "creative", "content", "design"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.in_progress,
        "company": "MadeByAkim",
        "start_date": "2024",
        "technologies": ["Adobe Premiere Pro", "Adobe After Effects", "Adobe Photoshop", "Adobe Illustrator", "Canva"],
        "job_families": ["Content Creator", "Graphic Designer"],
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "forbidden_claims": [
            "Do not claim professional designer status",
            "Do not claim broadcast-quality editing"
        ],
        "source_ref": "master_v3:madebyakim_creative",
        "priority": 7,
    },

    # =========================================================================
    # VASSARD EXPERIENCE (2022–2023)
    # =========================================================================
    {
        "category": CategoryEnum.experience,
        "title": "Vassard OMB Mobilier — Business Development & Reporting",
        "content": (
            "Business development and reporting role (2022–2023). Structured CRM and commercial "
            "data, implemented KPI tracking, analyzed customer information to support sales decisions "
            "and business development priorities."
        ),
        "tags": ["vassard", "crm", "reporting", "business_development"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.completed,
        "company": "Vassard OMB Mobilier",
        "start_date": "2022",
        "end_date": "2023",
        "technologies": ["CRM", "Excel", "Data Analysis"],
        "job_families": ["Business Analyst", "Sales Analyst"],
        "forbidden_claims": [
            "Do not claim specific revenue impact",
            "Do not claim technical CRM development"
        ],
        "source_ref": "master_v3:vassard_experience",
        "priority": 7,
    },

    # =========================================================================
    # PROJECTS
    # =========================================================================
    {
        "category": CategoryEnum.project,
        "title": "Elevia — AI Matching Platform for Professional Careers",
        "content": (
            "Personal AI platform dedicated to professional matching and career intelligence. "
            "Domains: CV parsing, skill extraction, canonicalization, matching, scoring, "
            "explainability, document generation, data quality, observability."
        ),
        "tags": ["elevia", "ai", "matching", "career_intelligence"],
        "truth_level": TruthLevelEnum.declared,
        "status": BlockStatusEnum.in_progress,
        "company": "Personal Project",
        "start_date": "2024",
        "technologies": ["Python", "FastAPI", "PostgreSQL", "OpenAI", "LangChain", "SQL", "APIs"],
        "job_families": ["AI Engineer", "ML Engineer", "Backend Engineer", "Data Engineer"],
        "source_ref": "master_v3:elevia_platform",
        "priority": 10,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Elevia — Matching Engine: 10+ Versions, 30 Profiles, 1000+ Opportunities",
        "content": (
            "Designed and iterated through more than 10 versions of a matching engine. Evaluated "
            "across 30 test profiles and over 1,000 job opportunities, improving recommendation "
            "quality and explainability."
        ),
        "tags": ["elevia", "matching", "optimization", "quality"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Personal Project",
        "start_date": "2024",
        "technologies": ["Python", "PostgreSQL", "OpenAI", "LangChain"],
        "job_families": ["ML Engineer", "Data Engineer"],
        "metrics": {
            "versions": "10+",
            "test_profiles": "30",
            "opportunities": "1000+"
        },
        "forbidden_claims": [
            "Do not claim 100% matching accuracy",
            "Do not claim production-scale real users",
            "Do not invent accuracy percentages"
        ],
        "source_ref": "master_v3:elevia_matching_engine",
        "priority": 10,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Elevia — Document Generation: 100+ CVs, ~90% Time Reduction",
        "content": (
            "Generated 100+ AI-assisted application documents (CVs, cover letters, recruiter messages) "
            "— reducing preparation time from dozens of minutes to a few seconds."
        ),
        "tags": ["elevia", "document_generation", "efficiency"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Personal Project",
        "start_date": "2024",
        "technologies": ["Python", "OpenAI", "LangChain", "Jinja2"],
        "job_families": ["AI Engineer", "Backend Engineer"],
        "metrics": {
            "documents": "100+",
            "before": "Dozens of minutes",
            "after": "A few seconds"
        },
        "forbidden_claims": [
            "Do not change 'dozens of minutes' to specific hour counts",
            "Do not claim zero human review needed"
        ],
        "source_ref": "master_v3:elevia_document_generation",
        "priority": 10,
    },
    {
        "category": CategoryEnum.achievement,
        "title": "Elevia — Architecture: ~10 Components, 4 PostgreSQL Tables",
        "content": (
            "Built a modular architecture of ~10 components across 4 PostgreSQL tables, covering "
            "CV parsing, skill extraction, canonicalization, scoring and observability."
        ),
        "tags": ["elevia", "architecture", "design"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Personal Project",
        "start_date": "2024",
        "technologies": ["Python", "PostgreSQL", "FastAPI", "SQL"],
        "job_families": ["Backend Engineer", "Data Engineer"],
        "metrics": {
            "components": "~10",
            "tables": "4"
        },
        "forbidden_claims": [
            "Do not claim 100% production robustness",
            "Do not claim zero maintenance needed"
        ],
        "source_ref": "master_v3:elevia_architecture",
        "priority": 9,
    },
    {
        "category": CategoryEnum.project,
        "title": "Job Apply Assistant — Telegram AI Assistant",
        "content": (
            "Personal Telegram assistant automating job applications. Analyzes job offers, matches "
            "against candidate profile and generates tailored CV, cover letter and recruiter message."
        ),
        "tags": ["job_apply_assistant", "telegram", "automation"],
        "truth_level": TruthLevelEnum.declared,
        "status": BlockStatusEnum.in_progress,
        "company": "Personal Project",
        "start_date": "2025",
        "technologies": ["Python", "Telegram", "OpenAI", "PostgreSQL", "SQLAlchemy", "Jinja2"],
        "job_families": ["AI Engineer", "Backend Engineer", "Automation Engineer"],
        "metrics": {
            "before": "~45 minutes per application",
            "after": "~5 minutes per application",
            "reduction": "~90%"
        },
        "forbidden_claims": [
            "Do not claim production-scale user base",
            "Do not invent user metrics",
            "Do not claim 100% accuracy"
        ],
        "source_ref": "master_v3:job_apply_assistant",
        "priority": 9,
    },
    {
        "category": CategoryEnum.project,
        "title": "V.I.E Matcher — Workflow for Opportunity Matching & Application Prep",
        "content": (
            "Workflow dedicated to V.I.E opportunity analysis, profile matching, scoring and "
            "ATS-oriented application preparation."
        ),
        "tags": ["vie_matcher", "automation", "matching"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.deployed,
        "company": "Personal Project",
        "technologies": ["Make", "Google Sheets", "Telegram", "OpenAI"],
        "job_families": ["Automation Engineer", "Integration Engineer"],
        "forbidden_claims": [
            "Do not claim advanced AI matching",
            "Do not claim high accuracy without data"
        ],
        "source_ref": "master_v3:vie_matcher",
        "priority": 8,
    },
    {
        "category": CategoryEnum.project,
        "title": "SkillMap Automation Console — Data Visualization & Skills Intelligence",
        "content": (
            "Portfolio project transforming structured data into interfaces, dashboards and insights "
            "around skills, offers and workflows."
        ),
        "tags": ["skillmap", "dashboards", "portfolio"],
        "truth_level": TruthLevelEnum.verified,
        "status": BlockStatusEnum.exploratory,
        "company": "Personal Project",
        "technologies": ["Data Visualization", "APIs", "Dashboards"],
        "job_families": ["Data Analyst", "BI Analyst"],
        "forbidden_claims": [
            "Do not claim production deployment",
            "Do not claim real-time data processing"
        ],
        "source_ref": "master_v3:skillmap_automation",
        "priority": 7,
    },

    # =========================================================================
    # SKILLS — INDIVIDUAL (ONE SKILL = ONE BLOCK when levels differ)
    # =========================================================================
    # Data & Analytics
    {
        "category": CategoryEnum.skill,
        "title": "SQL",
        "content": "Structured query language for data extraction, manipulation, transformation and analysis.",
        "tags": ["sql", "data"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "Data Engineer", "BI Analyst"],
        "technologies": ["SQL"],
        "forbidden_claims": ["Do not claim DBA expertise"],
        "source_ref": "master_v3:skill_sql",
        "priority": 10,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Python",
        "content": "General-purpose language used for data manipulation, automation, scripting and backend development.",
        "tags": ["python", "data", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Engineer", "Backend Engineer", "Automation Engineer", "AI Engineer"],
        "technologies": ["Python"],
        "forbidden_claims": ["Do not claim system programming expertise"],
        "source_ref": "master_v3:skill_python",
        "priority": 10,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Power BI",
        "content": "Business intelligence tool for data visualization, dashboarding and interactive reporting.",
        "tags": ["powerbi", "dataviz", "bi"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["BI Analyst", "Data Analyst"],
        "technologies": ["Power BI"],
        "forbidden_claims": ["Do not claim advanced DAX without proven use"],
        "source_ref": "master_v3:skill_power_bi",
        "priority": 10,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Power Query",
        "content": "ETL tool in Excel and Power BI for data transformation, cleaning and consolidation.",
        "tags": ["power_query", "etl", "data_transformation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "BI Analyst"],
        "technologies": ["Power Query"],
        "source_ref": "master_v3:skill_power_query",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Excel (Advanced)",
        "content": "Spreadsheet tool for data analysis, modeling, visualization and reporting.",
        "tags": ["excel", "spreadsheet"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "Business Analyst"],
        "technologies": ["Excel"],
        "forbidden_claims": ["Do not claim VBA development"],
        "source_ref": "master_v3:skill_excel",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Pandas",
        "content": "Python data manipulation and analysis library.",
        "tags": ["pandas", "python", "data"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Data Engineer", "Data Analyst"],
        "technologies": ["Pandas", "Python"],
        "source_ref": "master_v3:skill_pandas",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "KPI Monitoring & Analysis",
        "content": "Definition, tracking, visualization and interpretation of key performance indicators for business decisions.",
        "tags": ["kpi", "monitoring", "analytics"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "Business Analyst"],
        "source_ref": "master_v3:skill_kpi_monitoring",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Dashboard Design & Creation",
        "content": "Creating interactive dashboards and visual reporting systems for business intelligence.",
        "tags": ["dashboards", "design", "reporting"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["BI Analyst", "Data Analyst"],
        "technologies": ["Power BI", "Google Sheets", "Excel"],
        "source_ref": "master_v3:skill_dashboards",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Data Visualization",
        "content": "Designing clear, effective visual representations of data insights.",
        "tags": ["dataviz", "design", "communication"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "BI Analyst"],
        "source_ref": "master_v3:skill_dataviz",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Data Cleaning & Quality Assurance",
        "content": "Identifying, correcting and documenting data inconsistencies and quality issues.",
        "tags": ["data_quality", "data_cleaning", "qa"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "Data Engineer"],
        "source_ref": "master_v3:skill_data_quality",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Reporting & Business Analysis",
        "content": "Structuring information, creating reports and supporting business decisions through data.",
        "tags": ["reporting", "business_analysis"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "Business Analyst"],
        "source_ref": "master_v3:skill_reporting",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Performance Analysis",
        "content": "Analyzing performance metrics, trends and optimization opportunities.",
        "tags": ["performance", "analytics"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Data Analyst", "Business Analyst"],
        "source_ref": "master_v3:skill_performance_analysis",
        "priority": 8,
    },

    # Automation & APIs
    {
        "category": CategoryEnum.skill,
        "title": "Make (Automation Platform)",
        "content": "Low-code automation platform for building workflows, integrations and automations.",
        "tags": ["make", "automation", "integration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Automation Engineer", "Integration Engineer"],
        "technologies": ["Make"],
        "source_ref": "master_v3:skill_make",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "n8n (Workflow Automation)",
        "content": "Open-source workflow automation and integration platform.",
        "tags": ["n8n", "automation", "integration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Automation Engineer", "Integration Engineer"],
        "technologies": ["n8n"],
        "source_ref": "master_v3:skill_n8n",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "REST APIs",
        "content": "Design and integration of RESTful APIs for data exchange and system communication.",
        "tags": ["apis", "rest", "integration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Backend Engineer", "Integration Engineer", "Automation Engineer"],
        "technologies": ["REST APIs"],
        "source_ref": "master_v3:skill_rest_apis",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Webhooks",
        "content": "Event-driven API calls for triggering actions and automations between systems.",
        "tags": ["webhooks", "integration", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Automation Engineer", "Integration Engineer"],
        "technologies": ["Webhooks"],
        "source_ref": "master_v3:skill_webhooks",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "JSON",
        "content": "Lightweight data format for APIs, configuration and data exchange.",
        "tags": ["json", "data_format"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Backend Engineer", "Integration Engineer", "Data Engineer"],
        "technologies": ["JSON"],
        "source_ref": "master_v3:skill_json",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Google Apps Script",
        "content": "JavaScript-based scripting for Google Workspace automation and extensions.",
        "tags": ["google_apps_script", "javascript", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Automation Engineer"],
        "technologies": ["Google Apps Script"],
        "forbidden_claims": ["Do not claim advanced JavaScript"],
        "source_ref": "master_v3:skill_google_apps_script",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Telegram Bot Integration",
        "content": "Building bots and integrations for the Telegram messaging platform.",
        "tags": ["telegram", "bots", "integration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Automation Engineer", "Backend Engineer"],
        "technologies": ["Telegram"],
        "source_ref": "master_v3:skill_telegram_bots",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "CRM Integrations",
        "content": "Integrating and automating workflows across CRM platforms and other business systems.",
        "tags": ["crm", "integration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Integration Engineer", "CRM Administrator"],
        "technologies": ["HubSpot", "Microsoft Dynamics"],
        "source_ref": "master_v3:skill_crm_integrations",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Workflow Automation",
        "content": "Design and implementation of automated processes to reduce manual work.",
        "tags": ["automation", "workflow"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Automation Engineer"],
        "source_ref": "master_v3:skill_workflow_automation",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Lead Enrichment",
        "content": "Automating collection and enrichment of prospect and customer data.",
        "tags": ["lead_enrichment", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Automation Engineer", "Integration Engineer"],
        "source_ref": "master_v3:skill_lead_enrichment",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Document Generation",
        "content": "Automating creation of documents, reports and templates from data and templates.",
        "tags": ["document_generation", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Backend Engineer", "Automation Engineer"],
        "technologies": ["Jinja2", "Python"],
        "source_ref": "master_v3:skill_document_generation",
        "priority": 8,
    },

    # AI & LLM
    {
        "category": CategoryEnum.skill,
        "title": "OpenAI API",
        "content": "Using OpenAI models (GPT-4, GPT-3.5) via API for text generation and analysis.",
        "tags": ["openai", "llm", "ai"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["AI Engineer", "Backend Engineer", "Data Engineer"],
        "technologies": ["OpenAI"],
        "source_ref": "master_v3:skill_openai",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Claude (Anthropic)",
        "content": "Using Claude models via API for text generation, analysis and structured tasks.",
        "tags": ["claude", "llm", "ai"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["AI Engineer", "Backend Engineer"],
        "technologies": ["Claude"],
        "source_ref": "master_v3:skill_claude",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Gemini (Google)",
        "content": "Using Google Gemini models for AI-assisted tasks and text generation.",
        "tags": ["gemini", "llm", "ai"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["AI Engineer"],
        "technologies": ["Gemini"],
        "forbidden_claims": ["Do not claim production-scale expertise"],
        "source_ref": "master_v3:skill_gemini",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Prompt Engineering",
        "content": "Crafting effective prompts to optimize LLM behavior and output quality.",
        "tags": ["prompt_engineering", "ai"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["AI Engineer", "Backend Engineer"],
        "source_ref": "master_v3:skill_prompt_engineering",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Structured Extraction",
        "content": "Using LLMs to parse unstructured text and extract structured data.",
        "tags": ["structured_extraction", "ai", "nlp"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["AI Engineer", "Data Engineer"],
        "technologies": ["OpenAI", "Claude", "Python"],
        "source_ref": "master_v3:skill_structured_extraction",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "RAG (Retrieval-Augmented Generation)",
        "content": "Combining document retrieval with LLMs for knowledge-grounded generation.",
        "tags": ["rag", "ai", "knowledge"],
        "truth_level": TruthLevelEnum.declared,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["AI Engineer"],
        "forbidden_claims": ["Do not claim production RAG systems"],
        "source_ref": "master_v3:skill_rag",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "AI Agents",
        "content": "Designing and building autonomous systems that use LLMs for decision-making and actions.",
        "tags": ["ai_agents", "ai"],
        "truth_level": TruthLevelEnum.declared,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["AI Engineer"],
        "forbidden_claims": ["Do not claim advanced agent reasoning"],
        "source_ref": "master_v3:skill_ai_agents",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Knowledge Bases & Semantic Search",
        "content": "Building and managing structured knowledge for retrieval and matching.",
        "tags": ["knowledge_bases", "semantic_search"],
        "truth_level": TruthLevelEnum.declared,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["AI Engineer", "Data Engineer"],
        "forbidden_claims": ["Do not claim advanced ML expertise"],
        "source_ref": "master_v3:skill_knowledge_bases",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "LLM Workflows",
        "content": "Chaining LLM calls, combining multiple models and orchestrating AI-powered pipelines.",
        "tags": ["llm_workflows", "ai"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["AI Engineer", "Backend Engineer"],
        "technologies": ["OpenAI", "Claude", "LangChain", "Python"],
        "source_ref": "master_v3:skill_llm_workflows",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "LangChain",
        "content": "Framework for building LLM-powered applications with chains, agents and memory.",
        "tags": ["langchain", "ai", "framework"],
        "truth_level": TruthLevelEnum.declared,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["AI Engineer", "Backend Engineer"],
        "technologies": ["LangChain", "Python"],
        "forbidden_claims": ["Do not claim expert-level LangChain design"],
        "source_ref": "master_v3:skill_langchain",
        "priority": 7,
    },

    # Backend & Data Systems
    {
        "category": CategoryEnum.skill,
        "title": "PostgreSQL",
        "content": "Relational database for data storage, querying and management.",
        "tags": ["postgresql", "database"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Engineer", "Backend Engineer", "Data Analyst"],
        "technologies": ["PostgreSQL"],
        "forbidden_claims": ["Do not claim DBA administration"],
        "source_ref": "master_v3:skill_postgresql",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "FastAPI",
        "content": "Modern Python web framework for building APIs with automatic documentation.",
        "tags": ["fastapi", "backend", "api"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Backend Engineer", "AI Engineer"],
        "technologies": ["FastAPI", "Python"],
        "source_ref": "master_v3:skill_fastapi",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "SQLAlchemy",
        "content": "Python ORM library for database abstraction and query building.",
        "tags": ["sqlalchemy", "orm", "python"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Backend Engineer", "Data Engineer"],
        "technologies": ["SQLAlchemy", "Python"],
        "source_ref": "master_v3:skill_sqlalchemy",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Jinja2 (Template Engine)",
        "content": "Python template engine for dynamic content generation and rendering.",
        "tags": ["jinja2", "templating", "python"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Backend Engineer"],
        "technologies": ["Jinja2", "Python"],
        "source_ref": "master_v3:skill_jinja2",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Data Pipelines & ETL",
        "content": "Designing and building data extraction, transformation and loading workflows.",
        "tags": ["pipelines", "etl", "data"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Data Engineer"],
        "technologies": ["Python", "SQL"],
        "source_ref": "master_v3:skill_data_pipelines",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Git & GitHub",
        "content": "Version control, repository management and collaborative development.",
        "tags": ["git", "github", "version_control"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Backend Engineer", "Data Engineer"],
        "technologies": ["Git", "GitHub"],
        "source_ref": "master_v3:skill_git_github",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Docker",
        "content": "Containerization for packaging and deploying applications.",
        "tags": ["docker", "devops", "containerization"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Backend Engineer", "DevOps Engineer"],
        "technologies": ["Docker"],
        "forbidden_claims": ["Do not claim production orchestration"],
        "source_ref": "master_v3:skill_docker",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Supabase",
        "content": "Open-source Firebase alternative with PostgreSQL backend and real-time features.",
        "tags": ["supabase", "backend", "database"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Backend Engineer", "Full-Stack Engineer"],
        "technologies": ["Supabase"],
        "source_ref": "master_v3:skill_supabase",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Firebase",
        "content": "Google's backend-as-a-service for real-time databases, authentication and hosting.",
        "tags": ["firebase", "backend", "realtime"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Backend Engineer", "Full-Stack Engineer"],
        "technologies": ["Firebase"],
        "forbidden_claims": ["Do not claim expert Firebase design"],
        "source_ref": "master_v3:skill_firebase",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "MongoDB",
        "content": "NoSQL document database for flexible data storage.",
        "tags": ["mongodb", "nosql", "database"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Backend Engineer", "Data Engineer"],
        "technologies": ["MongoDB"],
        "forbidden_claims": ["Do not claim deep MongoDB expertise"],
        "source_ref": "master_v3:skill_mongodb",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Elasticsearch",
        "content": "Search and analytics engine for full-text search and log analysis.",
        "tags": ["elasticsearch", "search", "analytics"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Data Engineer", "Backend Engineer"],
        "technologies": ["Elasticsearch"],
        "forbidden_claims": ["Do not claim advanced tuning expertise"],
        "source_ref": "master_v3:skill_elasticsearch",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Technical Documentation",
        "content": "Writing clear, structured documentation for systems, APIs and processes.",
        "tags": ["documentation", "technical_writing"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Backend Engineer", "Data Engineer"],
        "source_ref": "master_v3:skill_technical_documentation",
        "priority": 8,
    },

    # Business Systems
    {
        "category": CategoryEnum.skill,
        "title": "HubSpot CRM",
        "content": "Customer relationship management platform for sales, marketing and service.",
        "tags": ["hubspot", "crm"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["CRM Administrator", "Sales Analyst"],
        "technologies": ["HubSpot"],
        "source_ref": "master_v3:skill_hubspot",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Microsoft Dynamics",
        "content": "Enterprise CRM and business applications platform.",
        "tags": ["dynamics", "crm"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["CRM Administrator"],
        "technologies": ["Microsoft Dynamics"],
        "forbidden_claims": ["Do not claim advanced Dynamics development"],
        "source_ref": "master_v3:skill_dynamics",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Notion",
        "content": "All-in-one workspace for notes, databases, wikis and project management.",
        "tags": ["notion", "productivity", "wiki"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Project Manager", "Knowledge Manager"],
        "technologies": ["Notion"],
        "source_ref": "master_v3:skill_notion",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Airtable",
        "content": "Visual database and spreadsheet hybrid for data management and automation.",
        "tags": ["airtable", "database", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Automation Engineer", "Data Analyst"],
        "technologies": ["Airtable"],
        "source_ref": "master_v3:skill_airtable",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Google Sheets",
        "content": "Cloud-based spreadsheet for data analysis, tracking and collaboration.",
        "tags": ["google_sheets", "spreadsheet"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "Business Analyst"],
        "technologies": ["Google Sheets"],
        "forbidden_claims": ["Do not claim advanced GAS scripting"],
        "source_ref": "master_v3:skill_google_sheets",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Google Drive & Workspace",
        "content": "Cloud storage, collaboration and office productivity tools.",
        "tags": ["google_drive", "google_workspace", "collaboration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Business Analyst"],
        "technologies": ["Google Drive", "Google Workspace"],
        "source_ref": "master_v3:skill_google_drive",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Slack",
        "content": "Team communication and collaboration platform.",
        "tags": ["slack", "communication", "collaboration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Team Collaboration"],
        "technologies": ["Slack"],
        "source_ref": "master_v3:skill_slack",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Microsoft Teams",
        "content": "Enterprise communication and collaboration platform.",
        "tags": ["teams", "communication", "collaboration"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Team Collaboration"],
        "technologies": ["Microsoft Teams"],
        "source_ref": "master_v3:skill_teams",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "ManyChat",
        "content": "Chatbot platform for building conversational automations on messaging apps.",
        "tags": ["manychat", "chatbot", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Automation Engineer"],
        "technologies": ["ManyChat"],
        "forbidden_claims": ["Do not claim advanced AI chatbot design"],
        "source_ref": "master_v3:skill_manychat",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Meta Business Suite",
        "content": "Tools for managing Facebook and Instagram business accounts and advertising.",
        "tags": ["meta", "facebook", "instagram", "marketing"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Marketing Analyst"],
        "technologies": ["Meta Business Suite"],
        "source_ref": "master_v3:skill_meta_business_suite",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "CRM Workflows & Automation",
        "content": "Designing and automating business processes within CRM systems.",
        "tags": ["crm", "workflow", "automation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["CRM Administrator", "Automation Engineer"],
        "source_ref": "master_v3:skill_crm_workflows",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Campaign Reporting & Analytics",
        "content": "Tracking, analyzing and reporting on marketing and sales campaign performance.",
        "tags": ["campaign_reporting", "analytics", "marketing"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Marketing Analyst", "Business Analyst"],
        "source_ref": "master_v3:skill_campaign_reporting",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Customer Data Management",
        "content": "Organizing, cleaning and leveraging customer data for business insights.",
        "tags": ["customer_data", "data_management"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Data Analyst", "Business Analyst"],
        "source_ref": "master_v3:skill_customer_data",
        "priority": 7,
    },

    # Creative & Delivery
    {
        "category": CategoryEnum.skill,
        "title": "Adobe Premiere Pro",
        "content": "Professional video editing and production software.",
        "tags": ["adobe_premiere", "video_editing"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Content Creator"],
        "technologies": ["Adobe Premiere Pro"],
        "forbidden_claims": ["Do not claim broadcast-quality expertise"],
        "source_ref": "master_v3:skill_adobe_premiere_pro",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Adobe After Effects",
        "content": "Motion graphics and visual effects software.",
        "tags": ["adobe_after_effects", "motion_graphics"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Content Creator"],
        "technologies": ["Adobe After Effects"],
        "forbidden_claims": ["Do not claim professional VFX expertise"],
        "source_ref": "master_v3:skill_adobe_after_effects",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Adobe Photoshop",
        "content": "Image editing and design software.",
        "tags": ["adobe_photoshop", "image_editing"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Content Creator", "Graphic Designer"],
        "technologies": ["Adobe Photoshop"],
        "forbidden_claims": ["Do not claim professional retouching"],
        "source_ref": "master_v3:skill_adobe_photoshop",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Adobe Illustrator",
        "content": "Vector graphics and illustration software.",
        "tags": ["adobe_illustrator", "vector_graphics"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.beginner,
        "job_families": ["Content Creator", "Graphic Designer"],
        "technologies": ["Adobe Illustrator"],
        "forbidden_claims": ["Do not claim professional illustration skills"],
        "source_ref": "master_v3:skill_adobe_illustrator",
        "priority": 6,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Canva",
        "content": "Easy-to-use graphic design platform for creating visuals.",
        "tags": ["canva", "design", "graphics"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Content Creator", "Marketing Analyst"],
        "technologies": ["Canva"],
        "source_ref": "master_v3:skill_canva",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Presentation Design & Speaking",
        "content": "Creating engaging presentations and delivering them effectively.",
        "tags": ["presentations", "communication", "design"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Business Analyst", "Data Analyst"],
        "source_ref": "master_v3:skill_presentation_design",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Dashboard Presentations",
        "content": "Presenting insights and data dashboards to stakeholders and executives.",
        "tags": ["dashboards", "presentations", "stakeholder_communication"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Data Analyst", "BI Analyst"],
        "source_ref": "master_v3:skill_dashboard_presentations",
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "User Training & Education",
        "content": "Teaching and training users on tools, processes and systems.",
        "tags": ["training", "user_education", "communication"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Business Analyst"],
        "source_ref": "master_v3:skill_user_training",
        "priority": 7,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Process Mapping & Documentation",
        "content": "Documenting, visualizing and improving business processes.",
        "tags": ["process_mapping", "documentation"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.intermediate,
        "job_families": ["Business Analyst"],
        "source_ref": "master_v3:skill_process_mapping",
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Stakeholder Communication",
        "content": "Communicating clearly with diverse stakeholders and building alignment.",
        "tags": ["communication", "stakeholders"],
        "truth_level": TruthLevelEnum.verified,
        "proficiency_level": ProficiencyLevelEnum.expert,
        "job_families": ["Business Analyst", "Data Analyst"],
        "source_ref": "master_v3:skill_stakeholder_communication",
        "priority": 9,
    },

    # =========================================================================
    # EDUCATION
    # =========================================================================
    {
        "category": CategoryEnum.education,
        "title": "MSc Business Intelligence & Analytics — Eugenia School (2025)",
        "content": (
            "Master of Science in Business Intelligence & Analytics. Specialization: Data Analyst "
            "for Marketing. Focus on Business Intelligence, analytics and data analysis."
        ),
        "tags": ["msc", "business_intelligence", "analytics"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:education_eugenia_2025",
        "priority": 8,
    },
    {
        "category": CategoryEnum.education,
        "title": "Bachelor Responsable Commerce & Marketing — EM Normandie (2023)",
        "content": (
            "Bachelor degree in Business Development and Marketing. Foundation in business, "
            "sales and communication."
        ),
        "tags": ["bachelor", "business", "marketing"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:education_em_normandie_2023",
        "priority": 7,
    },
    {
        "category": CategoryEnum.education,
        "title": "BTS Management Commercial Opérationnel (2021)",
        "content": "Two-year technical degree in operational and commercial management fundamentals.",
        "tags": ["bts", "management", "commercial"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:education_bts_2021",
        "priority": 6,
    },

    # =========================================================================
    # CERTIFICATIONS
    # =========================================================================
    {
        "category": CategoryEnum.certification,
        "title": "Dataiku ML Practitioner",
        "content": "Certification in machine learning using the Dataiku platform.",
        "tags": ["dataiku", "machine_learning", "certification"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:cert_dataiku",
        "priority": 6,
    },
    {
        "category": CategoryEnum.certification,
        "title": "Python for Machine Learning",
        "content": "Certification in Python programming for machine learning applications.",
        "tags": ["python", "machine_learning", "certification"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:cert_python_ml",
        "priority": 7,
    },
    {
        "category": CategoryEnum.certification,
        "title": "Fine-Tuning Large Language Models",
        "content": "Certification in fine-tuning and adapting large language models.",
        "tags": ["llm", "fine_tuning", "certification"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:cert_fine_tuning_llm",
        "priority": 7,
    },

    # =========================================================================
    # LANGUAGES
    # =========================================================================
    {
        "category": CategoryEnum.language,
        "title": "French",
        "content": "French — Native speaker.",
        "tags": ["french", "native"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:language_french",
        "priority": 9,
    },
    {
        "category": CategoryEnum.language,
        "title": "English",
        "content": "English — Professional Working Proficiency (C1 level). Comfortable in technical and business contexts.",
        "tags": ["english", "c1", "professional"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:language_english",
        "priority": 9,
    },
    {
        "category": CategoryEnum.language,
        "title": "Spanish",
        "content": "Spanish — Intermediate level.",
        "tags": ["spanish", "intermediate"],
        "truth_level": TruthLevelEnum.verified,
        "source_ref": "master_v3:language_spanish",
        "priority": 7,
    },
]


def seed_profile_atomic_v3(force: bool = False):
    """Seed atomic v3 profile blocks. Use force=True to replace existing blocks."""
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

        for block_data in PROFILE_BLOCKS_ATOMIC_V3:
            block = ProfileBlock(**block_data)
            db.add(block)
        db.commit()
        print(f"✓ Seeded {len(PROFILE_BLOCKS_ATOMIC_V3)} atomic profile blocks (Master V3)")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    seed_profile_atomic_v3(force=force)
