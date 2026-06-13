def get_analysis_prompt(job_offer: str, profile_blocks: list) -> str:
    profile_text = "\n".join(
        [f"- [{block['title']}] {block['content']}" for block in profile_blocks]
    )

    return f"""Analyze this job offer and match it with the candidate's profile.

JOB OFFER:
{job_offer}

CANDIDATE PROFILE:
{profile_text}

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "company": "Company name",
  "job_title": "Job title",
  "sector": "Industry sector",
  "seniority": "Experience level required (junior/mid/senior/lead)",
  "missions": ["List of main responsibilities"],
  "required_skills": ["Technical skills required"],
  "soft_skills": ["Soft skills required"],
  "ats_keywords": ["Important keywords for ATS parsing"],
  "candidate_profile_needed": "Description of ideal candidate",
  "recommended_angle": "Positioning angle for this candidate",
  "match_score": 0-10,
  "strengths": ["Why candidate is a good fit"],
  "missing_points": ["Skills/experience not covered"],
  "cv_strategy": "How to structure CV for this role",
  "profile_blocks_to_use": [list of block IDs to highlight],
  "profile_blocks_to_avoid": [list of block IDs to minimize],
  "risk_of_overclaiming": ["Any fields where candidate might overstate capabilities"]
}}

CRITICAL RULES:
- Candidate can ONLY use what exists in their profile
- Cannot invent experiences
- Cannot exaggerate skill levels
- Must be honest about gaps
- If critical skill is missing, it MUST appear in missing_points
- match_score reflects realistic potential, not perfect fit"""
