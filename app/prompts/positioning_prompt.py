def get_positioning_prompt(analysis_json: dict) -> str:
    """Choose best positioning angle from fixed list.

    Returns JSON with choice and reasoning.
    """
    return f"""You are a positioning strategist.

Given this job analysis, choose the BEST positioning angle to present the candidate.

VALID ANGLES (must pick exactly one):
1. Data Analyst BI
2. Marketing Data Analyst
3. Data & AI Project Analyst
4. Automation / AI Workflow Analyst
5. Data Steward / Data Quality
6. Business Analyst orienté data
7. Product / Ops Analyst

JOB CONTEXT:
Company: {analysis_json['company']}
Job Title: {analysis_json['job_title']}
Required Skills: {', '.join(analysis_json['required_skills'])}
Key Missions: {', '.join(analysis_json['missions'][:3])}

Return ONLY valid JSON (no markdown, no explanation):

{{
  "recommended_positioning": "Exact angle name from list above",
  "reasoning": "Why this angle best matches the job and candidate"
}}

RULE: recommended_positioning MUST be exactly one of the 7 angles above."""
