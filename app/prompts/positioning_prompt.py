def get_positioning_prompt(analysis_json: dict) -> str:
    """Choose best positioning angle + skill profile.

    Returns JSON with positioning, skill_profile, and reasoning.
    Skill profile determines which skills to emphasize in CV.
    """
    return f"""You are a positioning strategist.

Given this job analysis, choose the BEST positioning angle and skill profile.

VALID POSITIONING ANGLES (pick exactly one):
1. Data Analyst BI
2. Marketing Data Analyst
3. Data & AI Project Analyst
4. Automation / AI Workflow Analyst
5. Data Steward / Data Quality
6. Business Analyst orienté data
7. Product / Ops Analyst

VALID SKILL PROFILES (pick exactly one):
These determine which skills to emphasize in CV:

* marketing_crm: For CRM, customer experience, campaign, marketing project roles
  → Emphasize: Business Systems, Data & Analytics, Creative & Delivery
  → Reduce: Backend, AI/LLM

* data_bi: For BI, business intelligence, analytics, reporting, dashboard roles
  → Emphasize: Data & Analytics, Business Systems, Automation & APIs
  → Reduce: Creative, AI/LLM

* finance_reporting: For finance, business reporting, KPI, decision support
  → Emphasize: Data & Analytics, Business Systems
  → Reduce: AI/LLM, Creative, Backend

* data_ai: For AI, LLM workflows, automation, Python, data engineering
  → Emphasize: AI & LLM, Backend & Data Systems, Data & Analytics
  → Reduce: Creative

* automation_ops: For automation, workflow, operations, integrations
  → Emphasize: Automation & APIs, Business Systems, Data & Analytics
  → Reduce: AI/LLM, Creative

* creative_marketing: For design, content, Adobe, social, branding
  → Emphasize: Creative & Delivery, Business Systems
  → Reduce: Backend, AI/LLM

* general_business_data: Default for general business/data roles
  → Balance all skills equally

JOB CONTEXT:
Company: {analysis_json['company']}
Job Title: {analysis_json['job_title']}
Required Skills: {', '.join(analysis_json['required_skills'])}
Key Missions: {', '.join(analysis_json['missions'][:3])}

Return ONLY valid JSON (no markdown, no explanation):

{{
  "positioning": "Exact angle name from positioning list above",
  "skill_profile": "Exact skill profile key from valid list above",
  "reasoning": "Why this positioning + skill profile combo best fits the job"
}}

RULES:
- positioning MUST be exactly one of the 7 angles above
- skill_profile MUST be exactly one of the 7 keys above
- skill_profile determines CV skill section emphasis
- Choose skill_profile to minimize noise and maximize role fit"""
