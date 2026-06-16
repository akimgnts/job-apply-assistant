def get_cv_adaptation_prompt(
    analysis: dict,
    positioning: str,
    master_cv: dict,
    skill_profile: str = "general_business_data",
) -> str:
    """Prompt to adapt Master CV to job offer.

    Philosophy: Truth is immutable. Narrative is flexible.

    CRITICAL:
    - No fabricated facts (companies, dates, technologies, metrics)
    - No invented experiences or certifications
    - Preserve underlying facts
    - Flexible wording to match role relevance
    - Eliminate weak/irrelevant bullets
    - Amplify strong/relevant ones
    """

    # Format master CV content for reference
    experiences_text = "\n".join(
        [
            f"#{i} {e['title']} @ {e['company']} ({e['dates']})\n"
            f"  Context: {e.get('context', '')}\n"
            f"  Bullets:\n"
            + "\n".join(f"    - {b}" for b in e.get('bullets', []))
            for i, e in enumerate(master_cv.get("experiences", []))
        ]
    )

    projects_text = "\n".join(
        [
            f"#{i} {p['title']}\n  Stack: {p.get('stack', 'N/A')}\n  Bullets: {p.get('bullets', [])}"
            for i, p in enumerate(master_cv.get("projects", []))
        ]
    )

    skills_text = "\n".join(
        [
            f"• {s['label']}: {s['content']}"
            for s in master_cv.get("skills", [])
        ]
    )

    return f"""ROLE

You are a premium CV positioning specialist.

Your task: Adapt Master CV to position the candidate for THIS role.
Use the skill_profile to reduce noise and emphasize relevant skills.

Philosophy: Truth is immutable. Narrative is flexible. Signal > Noise.

SKILL PROFILE: {skill_profile}

This determines which skills to emphasize. See SKILL PROFILE RULES below.

PRESERVE:
- Facts (companies, dates, technologies, responsibilities, achievements)
- Experience sequence (Sidel → MadeByAkim → Vassard)
- Underlying capabilities and accomplishments

TRANSFORM:
- Wording (adapt for industry/role relevance)
- Emphasis (highlight relevant facts, downplay irrelevant ones)
- Narrative angle (focus on what matters for THIS role)
- Language tone (match business/finance/technical context)

ALLOWED:
- Rewrite bullets to clarify and emphasize relevance
- Remove weak or irrelevant bullets
- Amplify strong bullets that support the positioning
- Reorganize facts within a bullet for clarity
- Simplify jargon or technical language
- Adapt vocabulary to match role domain (e.g., BI → analytics, automation → workflow)
- Use different tool names if technically equivalent (e.g., "data warehouse" vs "SQL")

FORBIDDEN:
- Invent companies, dates, or achievements
- Create new experiences or roles
- Add technologies not mentioned in Master CV
- Fabricate metrics or percentages
- Delete entire experiences (can remove weak bullets, not the job itself)
- Reorder experiences
- Invent certifications or education
- Claim credit for work not done by candidate

---

JOB CONTEXT

Position: {analysis['job_title']} @ {analysis['company']}
Positioning: {positioning}
Key missions: {', '.join(analysis.get('missions', [])[:3])}
Required skills: {', '.join(analysis.get('required_skills', [])[:5])}
ATS keywords: {', '.join(analysis.get('ats_keywords', [])[:8])}

---

MASTER CV CONTENT (source of truth)

Experiences:
{experiences_text}

Projects:
{projects_text}

Skills:
{skills_text}

---

---

SKILL PROFILE RULES

Skills are NOT equally important. The purpose is not to display everything.
The purpose is to highlight what MATTERS for THIS role.

PROFILE: {skill_profile}

For marketing_crm:
  Prioritize: Business Systems, Data & Analytics, Creative & Delivery
  Reduce: Backend & Data Systems, AI & LLM Workflows
  → Make CRM, reporting, campaign analysis, customer data visible
  → De-emphasize FastAPI, Docker, SQLAlchemy, LangChain

For data_bi:
  Prioritize: Data & Analytics, Business Systems, Automation & APIs
  Reduce: Creative & Delivery, AI & LLM Workflows
  → Make SQL, Power BI, reporting, dashboards visible
  → De-emphasize Adobe, social media, backend tools

For finance_reporting:
  Prioritize: Data & Analytics, Business Systems
  Reduce: Backend & Data Systems, AI & LLM Workflows, Creative & Delivery
  → Make Excel, Power BI, KPI monitoring, reporting visible
  → De-emphasize backend, AI, creative tools

For data_ai:
  Prioritize: AI & LLM Workflows, Backend & Data Systems, Data & Analytics, Automation & APIs
  Reduce: Creative & Delivery
  → Make Python, SQL, APIs, OpenAI, LangChain visible
  → De-emphasize Adobe, social media

For automation_ops:
  Prioritize: Automation & APIs, Business Systems, Data & Analytics
  Reduce: AI & LLM Workflows, Creative & Delivery
  → Make Make, n8n, webhooks, CRM integrations visible
  → De-emphasize backend, AI, creative

For creative_marketing:
  Prioritize: Creative & Delivery, Business Systems, Data & Analytics
  Reduce: Backend & Data Systems, AI & LLM Workflows
  → Make Adobe, design, social media, content visible
  → De-emphasize backend, AI, data tools

For general_business_data:
  All skills balanced. Default ordering.

YOUR TASK:
1. Reorder skill sections to match the skill_profile prioritization
2. Assign visibility levels: "high" | "normal" | "low"
   - high: lead with these skills
   - normal: include fully
   - low: keep but de-emphasize (short section, moved later)
3. Return skill_section_order array (reordered labels)
4. Return skill_section_emphasis object (each section's visibility)

---

ADAPTATION TASK

STEP 1: Title
- Adapt positioning to match job
- Max 8 words
- Must be professional and relevant

STEP 2: Summary
- OPTIONAL: Rewrite for job relevance (or leave empty "")
- If writing: mention key areas: {', '.join(analysis.get('missions', [])[:3])}
- Keep factual (only from Master CV)
- Max 70 words
- For finance/business roles: leave empty (experience speaks for itself)

STEP 3: Experience Order
- DO NOT REORDER experiences
- Order is FIXED: [0, 1, 2]
- Always return: "experience_order": [0, 1, 2]
- 0 = Sidel (strongest professional role)
- 1 = MadeByAkim (freelance projects)
- 2 = Vassard (business development)

STEP 4: Experience Bullets
- PRESERVE FACTS, REWRITE NARRATIVE
- Select bullets that support the positioning for THIS role
- Style guide:
  * Clarity over buzzwords
  * Relevance over completeness
  * Signal over noise
  * Business impact over tool lists
- Avoid: generic language, keyword stuffing, ChatGPT tone
- Use: confidence, simplicity, clarity

SIDEL EXPERIENCE (Experience #0) — FLAGSHIP RULE:

Sidel is the anchor experience (2-year apprenticeship, international B2B industrial).
MINIMUM 5 bullets. NEVER compress below this.

Core bullets to preserve in ALL roles:
1. "Consolidated and analyzed multi-source business data related to customers, installed base, leads, events and marketing activity."
2. "Monitored KPIs and business indicators to improve visibility for internal stakeholders."
3. "Structured and maintained reporting supports for marketing, communication and commercial teams using Excel, Power BI and Power Query."
5. "Coordinated with European marketing, communication and sales stakeholders in an international B2B environment."
7. "Analyzed business data using Python, SQL, Snowflake, Excel and Power BI to support decision-making and operational excellence."

Adaptations by role:

For marketing_crm roles:
  - Keep bullets 1, 2, 3, 5, 6
  - Emphasize: Reporting, coordination with marketing teams, communication assets
  - Rewrite to highlight: "coordinated with European marketing teams", "structured reporting for communication"

For data_bi roles:
  - Keep bullets 1, 2, 3, 7
  - Emphasize: Data consolidation, KPI monitoring, SQL/Snowflake/Power BI
  - Rewrite to highlight: "Analyzed customer data using SQL, Python and Snowflake", "Built KPI monitoring dashboards"

For data_ai roles:
  - Keep bullets 1, 7
  - Emphasize: SQL, Python, Snowflake, data analysis
  - Rewrite to highlight: "Analyzed business data using Python, SQL and Snowflake"

For finance/business roles:
  - Keep bullets 1, 2, 5
  - Emphasize: KPI monitoring, business insights, stakeholder reporting
  - Rewrite to highlight: "Monitored KPIs to support business decision-making"

NEVER REMOVE:
- International context (European teams, B2B environment)
- Duration (2-year apprenticeship implies scope and depth)
- Core technologies (SQL, Snowflake, Power BI)

Return: 5-6 bullets that show breadth, context, and impact.

STEP 5: Project Order
- Default order: [0, 1, 2] (Elevia, Job Apply Assistant, V.I.E Matcher)
- These 3 projects ALWAYS required (never delete)
- SkillMap (project 3) only for AI/Product/Data Visualization/Automation roles
- For all other roles: return [0, 1, 2]
- Never rewrite project descriptions
- All project bullets unchanged
- Return as list of project indices

STEP 6: Skill Section Order & Emphasis
- Reorder skill sections based on skill_profile
- Assign visibility levels to each section
- Visibility: "high" (lead), "normal" (include), "low" (de-emphasize)
- Sections: Data & Analytics, Automation & APIs, AI & LLM Workflows, Backend & Data Systems, Business Systems, Creative & Delivery
- Do not invent new sections
- Follow the skill_profile guidance

STEP 7: ATS Keywords
- Select 5-8 keywords matching job
- Use from: {', '.join(analysis.get('ats_keywords', []))}

---

RETURN

Return ONLY valid JSON (no markdown, no explanation):

{{
  "title": "Adapted positioning title (max 8 words)",
  "summary": "" or "Short summary explaining role fit (max 70 words)",
  "experience_order": [0, 1, 2],
  "experience_bullets": {{
    "0": ["Rewritten Sidel bullet 1 (fact-based, role-relevant)", "Rewritten Sidel bullet 2", "Rewritten Sidel bullet 3"],
    "1": ["Rewritten MadeByAkim bullet 1", "Rewritten MadeByAkim bullet 2"],
    "2": ["Rewritten Vassard bullet 1"]
  }},
  "project_order": [0, 1, 2],
  "project_bullets": {{
    "0": ["Rewritten Elevia description (fact-based)"],
    "1": ["Rewritten Job Apply Assistant description"],
    "2": ["Rewritten V.I.E Matcher description"]
  }},
  "skill_section_order": ["Section1", "Section2", "Section3", "Section4", "Section5", "Section6"],
  "skill_section_emphasis": {{
    "Data & Analytics": "high" or "normal" or "low",
    "Automation & APIs": "high" or "normal" or "low",
    "AI & LLM Workflows": "high" or "normal" or "low",
    "Backend & Data Systems": "high" or "normal" or "low",
    "Business Systems": "high" or "normal" or "low",
    "Creative & Delivery": "high" or "normal" or "low"
  }},
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

---

CRITICAL RULES

TRUTH IS IMMUTABLE:
- Companies, dates, roles NEVER fabricated
- Technologies mentioned must exist in Master CV
- Achievements must be real and provable
- No invented metrics or percentages
- No false claims of responsibility
- experience_order: [0, 1, 2] (sequence immutable)

NARRATIVE IS FLEXIBLE:
- Bullets can be rewritten for clarity and relevance
- Weak bullets can be removed if irrelevant to role
- Strong bullets can be amplified
- Vocabulary can adapt to match role domain
- Tone can shift (technical → business, ops → finance)
- Focus: signal over noise, relevance over completeness

STYLE GUIDELINES:
- Clarity beats complexity
- Relevance beats exhaustiveness
- Signal beats noise
- Credibility beats keyword stuffing
- Simple + clear beats buzzword-heavy
- Avoid: ChatGPT tone, generic language, keyword stuffing
- Use: confidence, simplicity, clarity, directness

FINAL TEST:
Would a founder, recruiter, or hiring manager understand in 30 seconds:
1. Who this person is?
2. What value they bring?
3. Why they fit this role?

If not: SIMPLIFY. Clarity beats everything.

PHILOSOPHY:
100% truthful source material. Flexible wording. Flexible emphasis. Flexible narrative.
No fabricated facts. No invented metrics. No invented technologies.
"""
