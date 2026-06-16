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
- Emphasize relevant bullets by rewriting
- Select and reorder projects by relevance
- Mention ATS keywords from the job

You may NEVER:
- Reorder experiences (order is FIXED: Sidel→MadeByAkim→Vassard)
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
- DO NOT REORDER experiences
- Order is FIXED: [0, 1, 2]
- Always return: "experience_order": [0, 1, 2]
- 0 = Sidel (strongest professional role)
- 1 = MadeByAkim (freelance projects)
- 2 = Vassard (business development)

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
    "0": ["Adapted Sidel bullet 1", "Adapted Sidel bullet 2"],
    "1": ["Adapted MadeByAkim bullet 1", "Adapted MadeByAkim bullet 2"],
    "2": ["Adapted Vassard bullet 1"]
  }},
  "project_order": [0, 1, 2, 3],
  "project_bullets": {{
    "0": ["Elevia description"],
    "1": ["Job Apply Assistant description"],
    "2": ["VIE Matcher description"],
    "3": ["SkillMap description"]
  }},
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

---

CRITICAL RULES

- experience_order MUST ALWAYS be [0, 1, 2] — NEVER reorder
- experience_order: [0, 1, 2] = Sidel, MadeByAkim, Vassard (immutable)
- All 3 experiences required: no deletions
- Ensure experience_bullets has entries for all 3 (0, 1, 2)
- All bullets come from Master CV (may be reworded)
- No new companies, schools, certifications, or projects invented
- project_order can be reordered, but all 4 must be present
- Numbers, dates, company names NEVER change
- All section headers remain
"""
