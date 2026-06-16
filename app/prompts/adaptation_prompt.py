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
- Rewrite the summary for job relevance (max 70 words)
- Reorder project priority (which projects appear first)
- Mention ATS keywords from the job

You may NEVER:
- Reorder experiences (order is FIXED: Sidel→MadeByAkim→Vassard)
- Rewrite, edit, or shorten experience/project bullets
- Create new bullets
- Delete experience bullets
- Delete experiences
- Invent new experiences, companies, schools, certifications
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
- OPTIONAL: Rewrite for job relevance (or leave empty "")
- If writing: mention key areas: {', '.join(analysis.get('missions', [])[:3])}
- Keep factual (only from Master CV)
- Max 70 words
- For finance/business roles: leave empty (experience speaks for itself)

STEP 3: Experience Order
- DO NOT REORDER experiences
- Order is FIXED: [0, 1, 2]
- Always return: "experience_order": [0, 1, 2]
- 0 = Sidel (strongest professional role)
- 1 = MadeByAkim (freelance projects)
- 2 = Vassard (business development)

STEP 4: Experience Bullets
- DO NOT REWRITE or edit bullets
- Use ALL bullets from Master CV for each experience
- Arrange bullets in order of relevance to job
- Put most relevant bullets first
- Never create, edit, or shorten bullets
- Return all original bullets in relevance order

STEP 5: Project Order
- Default order: [0, 1, 2] (Elevia, Job Apply Assistant, V.I.E Matcher)
- These 3 projects ALWAYS required (never delete)
- SkillMap (project 3) only for AI/Product/Data Visualization/Automation roles
- For all other roles: return [0, 1, 2]
- Never rewrite project descriptions
- All project bullets unchanged
- Return as list of project indices

STEP 6: ATS Keywords
- Select 5-8 keywords matching job
- Use from: {', '.join(analysis.get('ats_keywords', []))}

---

RETURN

Return ONLY valid JSON (no markdown, no explanation):

{{
  "title": "Adapted positioning title (max 8 words)",
  "summary": "",
  "experience_order": [0, 1, 2],
  "experience_bullets": {{
    "0": ["Original Sidel bullet 1", "Original Sidel bullet 2", "Original Sidel bullet 3", "Original Sidel bullet 4", "Original Sidel bullet 5", "Original Sidel bullet 6", "Original Sidel bullet 7", "Original Sidel bullet 8"],
    "1": ["Original MadeByAkim bullet 1", "Original MadeByAkim bullet 2", "Original MadeByAkim bullet 3", "Original MadeByAkim bullet 4", "Original MadeByAkim bullet 5", "Original MadeByAkim bullet 6"],
    "2": ["Original Vassard bullet 1", "Original Vassard bullet 2", "Original Vassard bullet 3"]
  }},
  "project_order": [0, 1, 2],
  "project_bullets": {{
    "0": ["Original Elevia description"],
    "1": ["Original Job Apply Assistant description"],
    "2": ["Original VIE Matcher description"]
  }},
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

---

CRITICAL RULES

IMMUTABLE:
- experience_order MUST ALWAYS be [0, 1, 2] (Sidel, MadeByAkim, Vassard)
- All 3 experiences required: no deletions
- All original bullets must be included — NEVER delete, rewrite, or shorten
- Sidel: 8 bullets, all included
- MadeByAkim: 6 bullets, all included
- Vassard: 3 bullets, all included
- Projects [0, 1, 2] ALWAYS required (Elevia, Job Apply Assistant, V.I.E Matcher)
- Project 3 (SkillMap) only for AI/Product/Visualization/Automation roles
- Project descriptions and bullets NEVER rewritten
- Numbers, dates, company names NEVER change

ALLOWED CHANGES:
- Reorder bullets within each experience by relevance
- Reorder projects by relevance
- Adapt title
- Optional summary: leave empty "" for finance/business roles, or rewrite (max 70 words)

PHILOSOPHY:
95% Master CV content + 5% adaptation (title, optional summary, bullet priority, project priority)
"""
