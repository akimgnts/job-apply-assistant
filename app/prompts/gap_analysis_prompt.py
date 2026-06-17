def get_gap_analysis_prompt(analysis: dict, positioning: str, master_cv: dict) -> str:
    """Gap Analysis: Measure exact mismatch between offer and candidate.

    P0 Priority: This is the real bottleneck.
    Not about understanding offer better.
    About measuring gap accurately.

    Philosophy:
    - Level gap is OK (can be bridged in interviews)
    - Skill gaps are manageable (can be learned)
    - Family mismatch is serious (different career)
    - Seniority claims are dangerous (dishonest)
    """

    candidate_profile = f"""
Name: Akim Guentas

Professional Background:
- Sidel (2 years, international B2B, data + analytics + automation + business)
- MadeByAkim (freelance, technical projects)
- Vassard (business development)

Level: Junior-Mid
Evidence: 2-year professional experience (apprenticeship), technical foundation strong,
         leadership/management experience: none

Technical Skills: SQL, Python, Power BI, Snowflake, FastAPI, PostgreSQL, OpenAI, Telegram
Business Skills: Data consolidation, reporting, stakeholder coordination, international
Language: French (native), English (fluent)

Multi-dimensional: Data + Analytics + Automation + Business + Communication
NOT: single-domain expert, NOT: architect/lead level
"""

    offer_context = f"""
Position: {analysis.get('job_title', 'Unknown')}
Company: {analysis.get('company', 'Unknown')}
Level indication: (inferred from title, missions, required_skills)

Key Missions: {', '.join(analysis.get('missions', [])[:3])}
Required Skills: {', '.join(analysis.get('required_skills', [])[:5])}
Soft Skills: {', '.join(analysis.get('soft_skills', [])[:3])}
"""

    return f"""GAP ANALYSIS AGENT

=== WHAT THIS IS ===

Not: "How can we make Akim seem like a match?"
Not: "What's our best narrative?"
Yes: "What's the actual gap?"

Output: Structured assessment of mismatch + confidence score.

=== ROLES FAMILIES ===

Families are independent of level:
- data_engineering: SQL, Python, data pipelines, ETL, databases
- data_analytics: SQL, reporting, dashboards, business intelligence, KPIs
- marketing: campaigns, CRM, customer analysis, automation
- product: roadmap, metrics, experimentation, user research
- ops: processes, efficiency, automation, workflows
- finance: budgets, forecasting, financial analysis, compliance
- automation: workflows, integrations, RPA, process improvement
- governance: data quality, compliance, data management

=== LEVELS (independent of family) ===

- junior: <2 years, foundation strong, no leadership
- mid: 2-4 years, specialist in domain, contributing individually
- senior: 4+ years, deep expertise, mentoring/influence
- lead: Managing people or technical direction
- director: Strategic responsibility

Akim: Junior-Mid level across all families
Evidence: 2-year professional experience

=== STEP 1: Extract Role Requirements ===

From title, missions, required_skills:
1. What family does this belong to? (data_eng? marketing? product?)
2. What level is actually required? (junior? senior? lead?)
3. What are MUST-HAVE skills? (non-negotiable)
4. What are NICE-TO-HAVE skills?
5. Any authority/leadership requirements? (manage? lead? own?)

=== STEP 2: Assess Candidate Match ===

For each requirement:
- Does Akim have it? (yes/partial/no)
- Evidence from profile
- Transferable? (if different domain)

=== STEP 3: Gap Assessment ===

Measure three types of gaps:

A) FAMILY GAP (serious):
   If offer wants "Product Manager" but Akim is data engineer → family mismatch
   Cost: Career pivot needed

B) LEVEL GAP (manageable):
   If offer wants "Senior" but Akim is junior → level mismatch
   Cost: Can be bridged in interview
   Risk: Don't claim senior if junior

C) SKILL GAP (manageable):
   If offer wants "Machine Learning" but Akim has Python → skill gap
   Cost: Can learn
   Evidence: Foundation present?

=== STEP 4: Confidence Score ===

Combine three factors:

fit_factors = {
  "family_match": 0.0-1.0 (is this same career family?),
  "level_match": 0.0-1.0 (is this same level?),
  "skill_match": 0.0-1.0 (does candidate have skills?)
}

confidence = (family_match * 0.5) + (level_match * 0.3) + (skill_match * 0.2)

Confidence interpretation:
- 0.80-1.00: Strong fit (family + level match, skills present)
- 0.60-0.79: Decent fit (family match, level or skill gap)
- 0.40-0.59: Weak fit (family match but significant gaps)
- 0.00-0.39: Poor fit (family mismatch or too high level)

=== STEP 5: Bridges ===

For each gap, can we build a bridge?

Example bridges (valid):
- "Automation experience + process improvement → can support ops efficiency"
- "Data + Python + FastAPI → can contribute to data platform"
- "International coordination → can work in global teams"

Invalid bridges (do NOT use):
- "Has Python → can be a Lead" (scope inflation)
- "Worked on projects → can manage teams" (authority claim)
- "Used SQL → can architect databases" (expertise claim)

=== STEP 6: Weak Fit Behavior (confidence < 0.50) ===

When fit is weak:

Do NOT:
- Try harder to make it fit
- Move closer to offer
- Invent bridges
- Claim capabilities not held

DO:
- Increase truth
- Prefer candidate identity over offer alignment
- Accept weak fit
- Acknowledge gaps honestly

Weak fit is ACCEPTABLE.
Forced fit is NOT.

Example:
- Offer: Team Lead (requires management)
- Candidate: junior IC (no management)
- Weak fit: confidence 0.45
- Action: Position as IC, acknowledge gap, let recruiter decide

=== RETURN ===

Return ONLY valid JSON:

{{
  "role_family": "data_engineering|marketing|product|ops|finance|automation|governance|unknown",
  "required_level": "junior|mid|senior|lead|director",
  "candidate_level": "junior|mid|senior",
  "level_gap": "junior_vs_mid|mid_vs_senior|junior_vs_lead|null",
  "must_haves": {{
    "SQL": true,
    "Team Leadership": false,
    "5+ years experience": false
  }},
  "nice_to_haves": {{
    "Snowflake": true,
    "Power BI": true,
    "Machine Learning": false
  }},
  "missing_dimensions": [
    "Team leadership experience",
    "People management",
    "Advanced ML"
  ],
  "bridges": [
    "Data engineering background supports data engineering roles",
    "Automation experience bridges to ops efficiency",
    "International coordination experience applies to global teams"
  ],
  "fit_factors": {{
    "family_match": 0.85,
    "level_match": 0.50,
    "skill_match": 0.70,
    "seniority_feasible": false
  }},
  "confidence": 0.62,
  "confidence_rationale": "Family match strong (data_engineering). Level gap significant
                           (lead required vs mid-candidate). Skills present but management
                           experience missing. Feasible as IC contributor, not as lead."
}}

=== CRITICAL RULES ===

- Never hide gaps (gaps are OK, dishonesty is not)
- Never inflate candidate level
- Never claim authority not held
- Be honest about family mismatch
- Confidence <0.50 is still OK (just say so)
- Bridges must be credible

=== EXAMPLES ===

Example 1: Sopra Steria "Consultant Analytics & IA"
- Role family: data_analytics + data_ai
- Required level: mid-senior
- Candidate level: mid
- Level gap: null (alignment)
- Confidence: 0.75 (strong family match)

Example 2: Pelico "Team Lead Data Engineering"
- Role family: data_engineering
- Required level: lead (managing people)
- Candidate level: junior
- Level gap: junior_vs_lead (serious)
- Confidence: 0.45 (family OK, but can't manage teams)
- Seniority feasible: false (don't claim lead)

Example 3: Ever.t "Data Engineer"
- Role family: data_engineering
- Required level: junior-mid
- Candidate level: mid
- Level gap: null (alignment)
- Confidence: 0.80 (strong match)

=== OFFER CONTEXT ===

{offer_context}

=== CANDIDATE PROFILE ===

{candidate_profile}

=== POSITIONING ===

Selected: {positioning}

Now assess gap for THIS offer + THIS positioning.
"""
