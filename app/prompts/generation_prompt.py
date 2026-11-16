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

WRITING STANDARD — MEMORABLE CANDIDATE

Every bullet must follow this structure: Action verb → concrete result → business impact.

GOOD: "Automated weekly Excel reporting from 5–6 hours to about 1 hour, including result checks"
GOOD: "Designed 6+ Power BI dashboards used weekly by dozens of business stakeholders"
BAD: "Contributed to improving reporting efficiency through automation"

FORBIDDEN words and phrases (never use):
leveraged, synergized, spearheaded, streamlined, cutting-edge, state-of-the-art,
value-added, best-in-class, robust, dynamic, proactively, strong communication skills,
team player, results-oriented, passionate about, contributed to, helped improve,
participated in, involved in, assisted with.

RULES:
- Use concrete numbers when they exist in the profile blocks (users, dashboards, customers, time saved, %)
- Prefer "designed 6+ Power BI dashboards used weekly by dozens of business stakeholders" over "created reporting tools"
- Prefer the verified weekly reporting result (5–6 hours to about 1 hour) over an unsupported time-saving claim
- Never soften real impact with vague qualifiers — state it directly
- Active voice only: "Built", "Automated", "Analyzed", "Delivered", "Led", "Designed"

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
- Every bullet = Action verb + concrete result + business impact
- Use only exact numbers and scales supported by Master CV V4 (6+ dashboards, dozens of users, 61 accounts, 5–6h/week to about 1h/week, etc.)
- No buzzwords — direct language only
- Active voice: "Built", "Automated", "Analyzed", "Delivered", "Led"
- Show what changed because of this person's work (before → after when data exists)
- 3 bullets max per experience, each one must stand alone as a proof point

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
    language = "French" if analysis_json.get("source_language") == "fr" else "English"
    attachments = analysis_json.get("available_documents") or []
    has_letter = "letter" in attachments
    has_cv = "cv" in attachments
    attachment_guidance = (
        "The generated packet includes " + " and ".join(
            label for key, label in (("letter", "the motivation letter"), ("cv", "the CV")) if key in attachments
        ) + ". Mention only those documents."
        if attachments else
        "No attachments are confirmed for this email. Do not claim or imply that a letter or CV is attached."
    )
    letter_guidance = (
        f"Core argument from the generated letter (use only to create a short invitation, do not repeat it): {analysis_json.get('letter_argument', '')}"
        if has_letter else "Do not refer to a generated letter unless the workflow supplies one."
    )
    reading_step = (
        "Invite the recruiter to read the attached motivation letter for the candidate's role-specific view."
        if has_letter else "Keep the opening focused on this role and propose a simple exchange."
    )
    cv_step = "Mention the CV as the evidence for the experience, if it is included." if has_cv else "Do not claim a CV is attached unless it is included."
    return f"""Write only the body of a short professional application email (max 120 words, plain text).

JOB: {analysis_json['job_title']} at {analysis_json['company']}
POSITIONING: {positioning}

Write in {language}. Tone: direct, professional, natural (not robotic).

Purpose: make the email a natural opening to the documents, so the letter carries the
role-specific argument and the CV provides evidence. Give one concrete, offer-specific
reason; do not retell the letter or summarize the CV. {attachment_guidance} {letter_guidance}

Structure:
1. A direct, human opening tied to this exact role
2. {reading_step}
3. {cv_step} Add a simple invitation to exchange.

CRITICAL: Return the body only. Do not include a subject line, greeting, salutation,
recipient placeholder, signature, or contact details. Keep it short, personal and factual."""

