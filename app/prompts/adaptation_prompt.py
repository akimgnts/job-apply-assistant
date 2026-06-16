def get_cv_adaptation_prompt(analysis: dict, positioning: str, master_cv: dict) -> str:
    """Prompt to adapt existing Master CV to job offer.

    CRITICAL: Only adapt, never invent.
    Never delete sections or experiences.
    Never add new companies, schools, certifications, projects.
    """

    # Format master CV content for reference
    experiences_text = "\n".join(
        [
            f"#{i} {e['title']} @ {e['company']} ({e['dates']})\n"
            f"  Bullets: {e['bullets'][:3]}"
            for i, e in enumerate(master_cv.get("experiences", []))
        ]
    )

    projects_text = "\n".join(
        [
            f"#{i} {p['title']}\n  Stack: {p.get('stack', 'N/A')}"
            for i, p in enumerate(master_cv.get("projects", []))
        ]
    )

    skills_text = "\n".join(
        [
            f"• {s['label']}: {s['content']}"
            for s in master_cv.get("skills", [])
        ]
    )

    return f"""ROLE

You are a CV adaptation specialist.

Your task is NOT to create a new CV.

Your task is to ADAPT an existing Master CV to a specific job offer.

You may only:
- Change the title to match positioning
- Rewrite the summary for job relevance
- Reorder experiences by relevance
- Emphasize relevant bullets
- Select and order projects by relevance
- Mention ATS keywords from the job

You may NEVER:
- Invent new experiences
- Invent new companies or schools
- Invent new certifications or projects
- Delete any section or experience
- Add new tools/technologies not in Master CV
- Fabricate dates or metrics

---

JOB CONTEXT

Position: {analysis['job_title']} @ {analysis['company']}
Positioning: {positioning}
Key missions: {', '.join(analysis.get('missions', [])[:3])}
Required skills: {', '.join(analysis.get('required_skills', [])[:5])}
ATS keywords: {', '.join(analysis.get('ats_keywords', [])[:8])}

---

MASTER CV CONTENT (source of truth)

Experiences:
{experiences_text}

Projects:
{projects_text}

Skills:
{skills_text}

---

ADAPTATION TASK

STEP 1: Title
- Adapt positioning to match job
- Max 8 words
- Must be professional and relevant

STEP 2: Summary
- Rewrite for job relevance
- Mention key areas: {', '.join(analysis.get('missions', [])[:3])}
- Keep factual (only from Master CV)
- Max 70 words

STEP 3: Experience Order
- Rank experiences by relevance to job
- Put strongest first
- ALL experiences remain (don't delete)
- Return as list of experience indices

STEP 4: Experience Bullets
- For each experience in final order
- Select and reword 2-4 most relevant bullets
- Focus on: {', '.join(analysis.get('missions', [])[:2])}
- Never invent metrics or responsibilities

STEP 5: Project Order
- Rank projects by relevance
- Keep only most relevant
- ALL remaining projects keep all bullets
- Return as list of project indices

STEP 6: ATS Keywords
- Select 5-8 keywords matching job
- Use from: {', '.join(analysis.get('ats_keywords', []))}

---

RETURN

Return ONLY valid JSON (no markdown, no explanation):

{{
  "title": "Adapted positioning title (max 8 words)",
  "summary": "Rewritten summary (max 70 words, plain text)",
  "experience_order": [0, 1, 2],
  "experience_bullets": {{
    "0": ["Adapted bullet 1", "Adapted bullet 2"],
    "1": ["Adapted bullet 1", "Adapted bullet 2"]
  }},
  "project_order": [0, 1],
  "project_bullets": {{
    "0": ["Description line 1", "Description line 2"],
    "1": ["Description line 1"]
  }},
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

---

CRITICAL RULES

- Ensure experience_order includes all experience IDs from Master CV
- Ensure experience_bullets matches experience_order
- All bullets come from Master CV (may be reworded)
- No deleted experiences
- No new companies invented
- No new projects invented
- Numbers and dates unchanged
- All section headers remain
"""
