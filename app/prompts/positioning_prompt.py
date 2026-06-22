def get_positioning_prompt_enriched_elevia(analysis_json: dict, matching_signals: dict) -> str:
    """Choose positioning angle enriched by Elevia matching signals.

    Uses Elevia's match_score, strengths, gaps, and explanation to guide
    positioning strategy:
    - High score (>7): Confident, direct angle
    - Medium score (4-7): Potential/bridge angle emphasizing transferable skills
    - Low score (<4): Adaptation/upskilling angle leveraging existing strengths

    Returns JSON with positioning, skill_profile, and reasoning informed by Elevia.
    """
    match_score = matching_signals.get("match_score", 0)
    strengths = matching_signals.get("strengths", [])
    gaps = matching_signals.get("gaps", [])
    explanation = matching_signals.get("explanation", "")

    # Determine confidence level from match_score
    if match_score >= 7:
        confidence_guidance = """CONFIDENCE LEVEL: HIGH (score >= 7)
Strategy: You have strong alignment with this role.
- Position yourself as a confident, qualified candidate
- Emphasize the skills and experience where you EXCEL
- Frame gaps (if any) as natural progression opportunities"""
    elif match_score >= 4:
        confidence_guidance = """CONFIDENCE LEVEL: MEDIUM (score 4-7)
Strategy: You have solid foundations with growth potential.
- Position yourself as someone who can quickly ramp up
- Lead with TRANSFERABLE STRENGTHS (emphasize what you're great at)
- Frame gaps as "exciting learning opportunities" or areas you're eager to develop
- Show how your existing skills create value NOW"""
    else:
        confidence_guidance = """CONFIDENCE LEVEL: LOW (score < 4)
Strategy: You have valuable complementary skills.
- Position yourself as someone bringing a UNIQUE ANGLE to the role
- Lead with your strongest relevant competencies
- Frame gaps as intentional specialization (you bring depth in other areas)
- Show concrete examples of how you've mastered complex skills quickly"""

    strengths_text = "\n".join([f"• {s}" for s in strengths[:5]]) if strengths else "None identified"
    gaps_text = "\n".join([f"• {s}" for s in gaps[:3]]) if gaps else "None"

    return f"""You are a PREMIUM POSITIONING STRATEGIST informed by Elevia's job matching analysis.

Your role: Choose the positioning angle that HONESTLY reflects this candidate's fit,
informed by REAL MATCHING SIGNALS from Elevia.

ELEVIA MATCHING ANALYSIS:
- Match Score: {match_score}/10
- Explanation: {explanation}

CANDIDATE STRENGTHS (align with this role):
{strengths_text}

CANDIDATE GAPS (skills/experience missing for this role):
{gaps_text}

{confidence_guidance}

VALID POSITIONING ANGLES (real market titles recruiters actually use):
1. Data Analyst BI
2. Marketing Data Analyst
3. Data Steward / Data Quality
4. Business Analyst orienté data
5. Data & AI Consultant
6. Product / Ops Analyst
7. Business Intelligence Analyst

SKILL PROFILES (determine CV emphasis):

* marketing_crm: Marketing Project Manager, CRM Lead, Customer Success roles
  Prioritize: Business Systems, Data & Analytics, Creative & Delivery
  Reduce: Backend, AI/LLM
  Signal: Project management + CRM execution

* data_bi: BI Analyst, Analytics Lead, Reporting roles
  Prioritize: Data & Analytics, Business Systems, Automation & APIs
  Reduce: Creative, AI/LLM
  Signal: Analytics depth + stakeholder reporting

* finance_reporting: Finance Analyst, CFO-level reporting
  Prioritize: Data & Analytics, Business Systems
  Reduce: AI/LLM, Creative, Backend
  Signal: Financial acumen + KPI discipline

* data_ai: Data Engineer, AI/ML roles, AI Workflows
  Prioritize: AI & LLM, Backend & Data Systems, Data & Analytics
  Reduce: Creative
  Signal: Technical depth + AI capability

* automation_ops: Automation Engineer, Ops roles, Integration specialist
  Prioritize: Automation & APIs, Business Systems, Data & Analytics
  Reduce: AI/LLM, Creative
  Signal: Process improvement + workflow design

* creative_marketing: Designer, Content Lead, Creative roles
  Prioritize: Creative & Delivery, Business Systems
  Reduce: Backend, AI/LLM
  Signal: Creative execution + production

* general_business_data: Default for undefined roles
  Prioritize: Data & Analytics, Business Systems
  Reduce: Nothing
  Signal: Balanced business intelligence

JOB CONTEXT:
Company: {analysis_json['company']}
Job Title: {analysis_json['job_title']}
Required Skills: {', '.join(analysis_json.get('required_skills', [])[:5])}
Key Missions: {', '.join(analysis_json.get('missions', [])[:3])}

TASK:
1. Understand the BUSINESS PURPOSE of this role
2. Consider the ELEVIA MATCHING SIGNALS above
3. Choose positioning that is HONEST and STRATEGIC:
   - At high confidence: Lead with strongest fit
   - At medium confidence: Lead with transferable strengths, acknowledge growth path
   - At low confidence: Lead with unique angle, reframe experience as complementary
4. Choose skill_profile that maximizes fit clarity AND authenticity
5. Return positioning that recruiter immediately recognizes

Return ONLY valid JSON:

{{
  "positioning": "Real market title from angles above",
  "skill_profile": "Skill profile key that emphasizes role fit given Elevia signals",
  "reasoning": "How Elevia signals informed this positioning choice. Be specific: mention key strengths used, how gaps are reframed, confidence level."
}}

CRITICAL RULES:

1. NEVER create synthetic titles — use only VALID_ANGLES

2. When Elevia score < 0.60 (weak fit):
   - Do NOT invent closer alignment
   - Do NOT force fit through misleading positioning
   - Choose angle that honestly reflects what you bring
   - Better: authentic positioning at lower fit than false confidence

3. Positioning MUST be from VALID_ANGLES only

4. Ensure reasoning EXPLICITLY mentions Elevia signals:
   - e.g., "Match score 8.2 shows strong alignment in analytics;
     positioning emphasizes BI depth via data_bi skill_profile"
   - e.g., "Match score 5.1 with gaps in AI; positioning leads with
     data quality expertise (strength) via Data Steward angle"

5. Recruiter should recognize title in <2 seconds"""


def get_positioning_prompt(analysis_json: dict) -> str:
    """Choose best positioning angle + skill profile (Premium Narrative Engine V2).

    Returns JSON with positioning, skill_profile, and reasoning.
    Skill profile determines which skills to emphasize in CV.

    PHILOSOPHY:
    - Never invent job titles (use real market titles)
    - Distinguish primary role from secondary domains
    - Do NOT infer role from isolated responsibilities
    - Infer from business PURPOSE of the position
    - Signal > Noise
    - Clarity > Keyword stuffing
    """
    return f"""You are a PREMIUM POSITIONING STRATEGIST.

Your role: Understand the business purpose of the job opening.
Identify the primary role, secondary domains, and tools.
Never invent synthetic titles.

Do NOT infer role from isolated responsibilities like "CRM", "reporting", "analytics".
Instead, understand the BUSINESS PURPOSE of the position.

Example:
Bad: "Role involves CRM, reporting, analytics → Analyst"
Good: "Role manages marketing projects with CRM tools → Project Manager"

VALID POSITIONING ANGLES (real market titles recruiters actually use):
1. Data Analyst BI
2. Marketing Data Analyst
3. Data Steward / Data Quality
4. Business Analyst orienté data
5. Data & AI Consultant
6. Product / Ops Analyst
7. Business Intelligence Analyst

INVALID (synthetic AI-generated titles — NEVER use):
❌ Data Infrastructure Engineer (too specific, not a market title)
❌ Customer Experience Marketing Analyst (made-up)
❌ Solution Engineer Focused on Automation (jargon, not recruiter-searchable)
❌ AI Solutions Specialist (marketing speak)
❌ Team Lead (authority claim if not held)

SKILL PROFILES (determine CV emphasis):

* marketing_crm: Marketing Project Manager, CRM Lead, Customer Success roles
  Prioritize: Business Systems, Data & Analytics, Creative & Delivery
  Reduce: Backend, AI/LLM
  Signal: Project management + CRM execution

* data_bi: BI Analyst, Analytics Lead, Reporting roles
  Prioritize: Data & Analytics, Business Systems, Automation & APIs
  Reduce: Creative, AI/LLM
  Signal: Analytics depth + stakeholder reporting

* finance_reporting: Finance Analyst, CFO-level reporting
  Prioritize: Data & Analytics, Business Systems
  Reduce: AI/LLM, Creative, Backend
  Signal: Financial acumen + KPI discipline

* data_ai: Data Engineer, AI/ML roles, AI Workflows
  Prioritize: AI & LLM, Backend & Data Systems, Data & Analytics
  Reduce: Creative
  Signal: Technical depth + AI capability

* automation_ops: Automation Engineer, Ops roles, Integration specialist
  Prioritize: Automation & APIs, Business Systems, Data & Analytics
  Reduce: AI/LLM, Creative
  Signal: Process improvement + workflow design

* creative_marketing: Designer, Content Lead, Creative roles
  Prioritize: Creative & Delivery, Business Systems
  Reduce: Backend, AI/LLM
  Signal: Creative execution + production

* general_business_data: Default for undefined roles
  Prioritize: Data & Analytics, Business Systems
  Reduce: Nothing
  Signal: Balanced business intelligence

JOB CONTEXT:
Company: {analysis_json['company']}
Job Title: {analysis_json['job_title']}
Required Skills: {', '.join(analysis_json['required_skills'])}
Key Missions: {', '.join(analysis_json['missions'][:3])}

TASK:
1. Understand the BUSINESS PURPOSE of this role
2. Identify PRIMARY ROLE (real market title)
3. Identify SECONDARY DOMAINS (dimensions, not titles)
4. Choose skill_profile that maximizes fit clarity
5. Return positioning that recruiter immediately recognizes

Return ONLY valid JSON:

{{
  "positioning": "Real market title from angles above",
  "skill_profile": "Skill profile key that emphasizes role fit",
  "reasoning": "Business purpose + primary role + why this skill_profile maximizes clarity"
}}

CRITICAL RULES:

1. NEVER create synthetic titles (AI-generated nonsense)

FORBIDDEN (hard):
  ❌ Data Solutions Engineer
  ❌ AI Solutions Specialist
  ❌ Customer Experience Analytics Expert
  ❌ Data Infrastructure Engineer
  ❌ Solution Engineer Focused on Automation

ALLOWED (real market titles):
  ✓ Data Engineer
  ✓ Data Analyst BI
  ✓ Consultant Analytics
  ✓ Marketing Project Manager
  ✓ Product Analyst

2. When confidence < 0.60 (weak fit):
   - Do NOT invent new positioning
   - Do NOT force closer alignment to offer
   - Fallback to: original offer title or closest VALID_ANGLE
   - Better: weak fit with truth than strong claim with lies

3. Positioning MUST be from VALID_ANGLES only
   - Never create new angles
   - Never customize titles per offer
   - Positioning is strategy, not description

4. Recruiter should recognize title in <2 seconds
5. Candidate value proposition should be obvious"""
