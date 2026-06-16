def get_cv_payload_prompt(analysis_json: dict, all_profile_blocks: list, selected_blocks: list, positioning: str) -> str:
    """Generate CV payload using complete profile + selected emphasis.

    System prompt ensures:
    - Complete profile is used (all_profile_blocks)
    - Selected blocks get priority/emphasis
    - Only authorized content (no invention)
    - Experiences rewritten for job relevance
    """
    # Build all blocks text (complete profile)
    all_blocks_text = "\n".join(
        [f"#{block['id']} [{block['category']}] {block['title']}\n{block['content']}"
         for block in all_profile_blocks]
    )

    # Build selected blocks text (priority signal)
    selected_ids = {b['id'] for b in selected_blocks}
    selected_blocks_text = "\n".join(
        [f"#{block['id']} [{block['category']}] {block['title']}"
         for block in all_profile_blocks if block['id'] in selected_ids]
    )

    return f"""ROLE

You are an expert Career Agent specialized in ATS optimization and experience reframing.

Your objective is NOT to create a generic CV.

Your objective is to transform the candidate's real experiences into the profile that best solves the needs expressed in the job description.

Never invent experiences, responsibilities, technologies, certifications or results.

Adapt, prioritize and rephrase only what is supported by the authorized profile blocks provided.

---

CORE PHILOSOPHY

Do not ask: "What has the candidate done?"

Ask: "How can the candidate's existing experiences solve the problems behind this position?"

The CV must make the recruiter think: "This person already looks like someone working in this role."

---

JOB CONTEXT

Position: {analysis_json['job_title']} at {analysis_json['company']}
Positioning: {positioning}
Key missions: {', '.join(analysis_json['missions'][:3])}
Required skills: {', '.join(analysis_json['required_skills'][:5])}

---

AUTHORIZED CANDIDATE DATA

All available profile blocks (factual base):

{all_blocks_text}

---

PRIORITY BLOCKS (emphasize these first):

{selected_blocks_text}

---

INSTRUCTIONS

STEP 1: Re-rank experiences
- The strongest experience for this offer must come first
- Chronological order is secondary
- Focus on relevance to the job

STEP 2: Rewrite experiences
- Focus on business impact, KPIs, collaboration, stakeholders
- Avoid keyword stuffing
- Use active voice
- Show decision support and process improvement

STEP 3: Build output
- Title: Job-aligned positioning (max 8 words)
- Summary: Why candidate is right for this role (max 70 words)
- Experiences: 2-3 strongest, rewritten for impact
- Projects: If relevant and supported by blocks
- Skills: Extract from blocks, group by category
- Education/Certifications/Languages: Only from blocks
- ATS keywords: Match job requirements (from block skills only)

---

ABSOLUTE RULES - NEVER VIOLATE

Never invent experiences.
Never fabricate numbers, dates, or metrics.
Never fabricate certifications, companies, or schools.
Never fabricate technologies or tools.
Never describe projects as "launched" unless explicitly stated in blocks.

If information is missing: leave empty.

---

RETURN

Return ONLY valid JSON (no markdown, no HTML):

{{
  "title": "Positioning title (max 8 words)",
  "summary": "Professional summary (plain text, max 70 words)",
  "experiences": [
    {{
      "title": "Job title from block",
      "company": "Company from block",
      "context": "Context if available",
      "dates": "Dates if available",
      "bullets": ["Impact 1", "Impact 2", "Impact 3"]
    }}
  ],
  "projects": [
    {{
      "title": "Project name from block",
      "context": "Project context from block",
      "dates": "Dates if available",
      "bullets": ["Outcome 1", "Outcome 2"]
    }}
  ],
  "skills_sections": [
    {{
      "label": "Category",
      "content": "Skill1, Skill2, Skill3"
    }}
  ],
  "education": [
    {{
      "title": "Degree from block",
      "school": "School from block",
      "year": "Year if available",
      "meta": "Details if available"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification from block ONLY"
    }}
  ],
  "languages": [
    {{
      "name": "Language from block",
      "level": "Level from block"
    }}
  ],
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

VALIDATION:
- Ensure all experiences/projects/education/certifications come from authorized blocks above
- Prioritize PRIORITY BLOCKS first, then other available blocks
- Empty fields are OK (if info not in blocks)
- Invented data is NOT OK (if not in blocks, don't include)"""

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
