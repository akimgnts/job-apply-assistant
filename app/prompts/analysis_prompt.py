def get_analysis_prompt(job_offer: str, profile_blocks: list) -> str:
    """Analyze job offer only. Do not rewrite or fabricate.

    This prompt:
    - Extracts requirements from the offer
    - Matches against provided profile blocks
    - NEVER creates content
    - NEVER rewrites experiences
    - Returns only structured analysis
    """
    profile_text = "\n".join(
        [f"- [{block['title']}] {block['content']}" for block in profile_blocks]
    )

    return f"""You are a job offer analyst.

Analyze this job offer to understand:
- Business challenges
- Key missions and responsibilities
- Required technical skills
- Required soft skills
- Domain and sector
- Seniority level
- Hidden expectations
- ATS keywords

Then match against the candidate's profile.

JOB OFFER:
{job_offer}

CANDIDATE PROFILE:
{profile_text}

Return ONLY valid JSON (no markdown, no explanation, no HTML):

{{
  "company": "Company name",
  "job_title": "Job title",
  "sector": "Industry or domain",
  "seniority": "junior/mid/senior/lead",

  "missions": ["Main responsibility 1", "Main responsibility 2"],
  "required_skills": ["Skill 1", "Skill 2"],
  "soft_skills": ["Soft skill 1", "Soft skill 2"],
  "ats_keywords": ["Keyword1", "Keyword2"],

  "business_challenges": "What problems this role solves",
  "match_score": 0-10,

  "strengths": ["Why candidate fits", "Existing skill match"],
  "missing_points": ["Gap 1", "Gap 2"],

  "profile_blocks_to_use": [1, 2, 3],
  "profile_blocks_to_avoid": [4, 5]
}}

CRITICAL RULES - DO NOT VIOLATE:
- Analyze offer only, do not create candidate content
- Never invent experiences
- Never invent skills
- Never fabricate companies or schools
- Match_score = honest assessment (0-10)
- If skill is missing from profile, put in missing_points
- Profile blocks to use = indices of best matching blocks"""
