def get_cv_payload_prompt(analysis_json: dict, profile_blocks: list, positioning: str) -> str:
    """Generate prompt for structured CV payload (JSON only)."""
    profile_text = "\n".join(
        [f"- {block['title']}: {block['content']}" for block in profile_blocks]
    )

    return f"""Generate a structured CV payload as JSON for this job application.

POSITIONING: {positioning}
JOB: {analysis_json['job_title']} at {analysis_json['company']}
REQUIRED SKILLS: {', '.join(analysis_json['required_skills'])}

CANDIDATE DATA (use ONLY what's listed below):
{profile_text}

Return ONLY valid JSON (no markdown, no code fences) with this exact structure:

{{
  "title": "Job-aligned title (max 8 words, e.g. 'Data Analyst - Business Intelligence')",
  "summary": "Professional summary tailored to {positioning} (plain text, max 70 words)",
  "experiences": [
    {{
      "title": "Job title",
      "company": "Company name",
      "context": "Brief context (e.g. 'International B2B, 200+ employees')",
      "dates": "YYYY – YYYY",
      "bullets": ["Bullet 1", "Bullet 2", "Bullet 3"]
    }}
  ],
  "projects": [
    {{
      "title": "Project name",
      "context": "Project context",
      "dates": "YYYY – YYYY",
      "bullets": ["Bullet 1", "Bullet 2"]
    }}
  ],
  "skills_sections": [
    {{
      "label": "Skill category",
      "content": "Skill 1, Skill 2, Skill 3 (plain text, comma-separated)"
    }}
  ],
  "education": [
    {{
      "title": "Degree name",
      "school": "School name",
      "year": "YYYY",
      "meta": "Additional info if relevant"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification name"
    }}
  ],
  "languages": [
    {{
      "name": "Language name",
      "level": "Proficiency level (e.g. Native, Professional, Intermediate)"
    }}
  ],
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

CRITICAL RULES:
- Return ONLY JSON, no other text
- No markdown code fences (```json or ```)
- No HTML tags in any text field
- Bullets must be plain text, actionable, and CV-ready
- Extract experiences/projects from CANDIDATE DATA, rewrite them CV-style
- ATS keywords must match job requirements
- Never invent skills or experience
- If a section is empty, use empty array []
- All text must be plain text (no special formatting)"""

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
