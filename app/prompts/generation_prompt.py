def get_cv_prompt(analysis_json: dict, profile_blocks: list, positioning: str) -> str:
    profile_text = "\n".join(
        [f"- {block['title']}: {block['content']}" for block in profile_blocks]
    )

    return f"""Generate a professional CV summary for this job application.

POSITIONING: {positioning}
JOB: {analysis_json['job_title']} at {analysis_json['company']}
REQUIRED SKILLS: {', '.join(analysis_json['required_skills'])}

CANDIDATE DATA (use ONLY what's listed below):
{profile_text}

Generate CV content (HTML format ready for embedding) with:
1. Professional summary (3-4 lines) tailored to "{positioning}"
2. Key skills (5-7 skills that match job requirements)
3. Experience (2-3 most relevant roles, using ONLY provided data)
4. Projects (1-2 if relevant, using ONLY provided data)
5. Education (if relevant to role)
6. ATS keywords at bottom

CRITICAL:
- Only use data from CANDIDATE DATA
- Cannot invent or exaggerate
- Focus on what makes candidate valuable for THIS specific role
- Be specific and concrete, never generic"""

def get_letter_prompt(analysis_json: dict, positioning: str) -> str:
    return f"""Write a compelling but concise motivation letter (max 450 words, HTML format).

POSITIONING: {positioning}
JOB: {analysis_json['job_title']} at {analysis_json['company']}
MATCH SCORE: {analysis_json['match_score']}/10

Tone: Professional, direct, authentic (NOT generic template language)

Structure:
1. Opening (why this company/role matters to you)
2. How your background aligns with their needs
3. Specific value you can bring
4. Call to action

CRITICAL: Never invent experience. Reference only what was provided in profile."""

def get_mail_prompt(analysis_json: dict, positioning: str) -> str:
    return f"""Write a short professional email to recruiter (max 120 words, plain text).

JOB: {analysis_json['job_title']} at {analysis_json['company']}
POSITIONING: {positioning}

Tone: Direct, professional, natural (not robotic)

Structure:
1. Quick intro + role you're applying for
2. 1-2 key points why you're interested
3. Call to action (e.g., "happy to discuss further")

CRITICAL: Keep it SHORT and genuine."""
