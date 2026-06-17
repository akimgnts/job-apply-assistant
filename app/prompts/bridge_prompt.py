def get_bridge_prompt(analysis: dict, positioning: str, master_cv: dict) -> str:
    """Bridge Engine: Explicit reasoning about candidate-role fit.

    Philosophy: Build bridges, not identities.
    Candidate remains recognizable. Only narrative adapts.

    BEFORE generating CV:
    1. What business problem does this role solve?
    2. What does Akim actually possess?
    3. Where are the overlaps?
    4. Where are the gaps?
    5. Can we build bridges without inventing experience?

    If answer to (5) is NO → gaps are acceptable. Lies are not.
    """

    # Extract key candidate info from master CV
    candidate_capabilities = []
    for exp in master_cv.get("experiences", []):
        candidate_capabilities.append(f"• {exp.get('title', '')}: {exp.get('context', '')}")

    candidate_expertise = ", ".join(
        [s["label"] for s in master_cv.get("skills", [])]
    )

    projects_desc = "; ".join(
        [f"{p.get('title', '')}" for p in master_cv.get("projects", [])]
    )

    return f"""BRIDGE ENGINE: Explicit Reasoning About Role Fit

=== ROLE CONTEXT ===

Company: {analysis.get('company', 'Unknown')}
Title: {analysis.get('job_title', 'Unknown')}
Positioning: {positioning}

Key Missions: {', '.join(analysis.get('missions', [])[:3])}
Required Skills: {', '.join(analysis.get('required_skills', [])[:5])}
Business Context: {analysis.get('analysis_summary', 'No context')}

=== CANDIDATE PROFILE ===

Name: Akim Guentas

Professional Background:
{chr(10).join(candidate_capabilities)}

Technical Expertise:
{candidate_expertise}

Projects:
{projects_desc}

=== BRIDGE ANALYSIS TASK ===

You are a BRIDGE BUILDER, not a identity transformer.

Task: Answer these 5 questions explicitly.

1. BUSINESS PROBLEM
What problem is the company solving? (What is the business purpose of this role?)
Be specific. Example: "Need someone to coordinate data pipelines for European stakeholders"

2. PRIMARY STRENGTHS
What does Akim possess that directly addresses the business problem?
List 3-5 specific capabilities from the profile above.

3. GAPS
What does the role ask for that Akim does NOT have?
Be honest. Do not hide gaps. Do not try to bridge them with invented experience.

4. BRIDGES
For each strength → how does it connect to the business problem?
Examples of valid bridges:
- "Has built data pipelines → Can coordinate technical setup"
- "Worked internationally → Understands multi-team coordination"
- "Created Telegram bot + OpenAI integration → Can work with AI workflows"

Invalid bridges (do NOT use):
- "Has Python → Can be a Backend Engineer" (too loose)
- "Has reported to stakeholders → Can be a Team Lead" (authority claim)
- "Has used SQL → Can architect databases" (scope inflation)

5. SENIORITY REALITY
Never inherit seniority from the offer.
Candidate seniority comes from candidate reality.

If offer is "Team Lead" and candidate is junior → do NOT claim leadership seniority.

Valid seniority statements:
- "Junior in domain X, solid foundation"
- "Mid-level in data, contributing as individual contributor"
- "Senior in automation, less experience in Y"

Invalid:
- "Senior Manager" (if not senior)
- "Technical Lead" (if no leadership experience)
- "Principal Engineer" (if not principal level)

=== RETURN ===

Return ONLY valid JSON:

{{
  "business_problem": "Specific business problem this role solves",
  "primary_strengths": [
    "Strength 1 with specific evidence",
    "Strength 2 with specific evidence"
  ],
  "gaps": [
    "Gap 1 (missing domain/experience)",
    "Gap 2"
  ],
  "bridges": [
    "How strength 1 addresses business problem",
    "How strength 2 addresses business problem"
  ],
  "seniority_assessment": "Junior|Mid|Senior|Overqualified",
  "positioning_rationale": "Concise explanation of why positioning makes sense given this analysis"
}}

=== CRITICAL PRINCIPLES ===

- Do NOT compensate gaps with invented experience
- Do NOT claim titles Akim has not held
- Do NOT inflate scope of existing work
- Do NOT hide gaps (gaps are acceptable, lies are not)
- Be honest about misalignment
- Focus on what genuinely connects candidate to role

The goal is NOT to make Akim seem perfect.
The goal is to explain why Akim still makes sense despite gaps.

If gaps are too large:
- Say so honestly
- Still list bridges for what does connect
- Acknowledge mismatch while respecting candidate truth
"""
