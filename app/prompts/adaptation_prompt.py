def get_cv_adaptation_prompt(analysis: dict, positioning: str, master_cv: dict) -> str:
    """Prompt to adapt Master CV to job offer.

    Philosophy: Truth is immutable. Narrative is flexible.

    CRITICAL:
    - No fabricated facts (companies, dates, technologies, metrics)
    - No invented experiences or certifications
    - Preserve underlying facts
    - Flexible wording to match role relevance
    - Eliminate weak/irrelevant bullets
    - Amplify strong/relevant ones
    """

    # Format master CV content for reference
    experiences_text = "\n".join(
        [
            f"#{i} {e['title']} @ {e['company']} ({e['dates']})\n"
            f"  Context: {e.get('context', '')}\n"
            f"  Bullets:\n"
            + "\n".join(f"    - {b}" for b in e.get('bullets', []))
            for i, e in enumerate(master_cv.get("experiences", []))
        ]
    )

    projects_text = "\n".join(
        [
            f"#{i} {p['title']}\n  Stack: {p.get('stack', 'N/A')}\n  Bullets: {p.get('bullets', [])}"
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

You are a premium CV positioning specialist.

Your task: Adapt Master CV to position the candidate for THIS role.

Philosophy: Truth is immutable. Narrative is flexible.

PRESERVE:
- Facts (companies, dates, technologies, responsibilities, achievements)
- Experience sequence (Sidel → MadeByAkim → Vassard)
- Underlying capabilities and accomplishments

TRANSFORM:
- Wording (adapt for industry/role relevance)
- Emphasis (highlight relevant facts, downplay irrelevant ones)
- Narrative angle (focus on what matters for THIS role)
- Language tone (match business/finance/technical context)

ALLOWED:
- Rewrite bullets to clarify and emphasize relevance
- Remove weak or irrelevant bullets
- Amplify strong bullets that support the positioning
- Reorganize facts within a bullet for clarity
- Simplify jargon or technical language
- Adapt vocabulary to match role domain (e.g., BI → analytics, automation → workflow)
- Use different tool names if technically equivalent (e.g., "data warehouse" vs "SQL")

FORBIDDEN:
- Invent companies, dates, or achievements
- Create new experiences or roles
- Add technologies not mentioned in Master CV
- Fabricate metrics or percentages
- Delete entire experiences (can remove weak bullets, not the job itself)
- Reorder experiences
- Invent certifications or education
- Claim credit for work not done by candidate

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
- PRESERVE FACTS, REWRITE NARRATIVE
- Select bullets that support the positioning for THIS role
- Remove weak or irrelevant bullets
- Rewrite bullets for clarity and relevance
- Amplify strong bullets that strengthen the positioning
- Style guide:
  * Clarity over buzzwords
  * Relevance over completeness
  * Signal over noise
  * Business impact over tool lists
- Avoid: generic language, keyword stuffing, ChatGPT tone
- Use: confidence, simplicity, clarity
- Return: rewritten bullets ordered by relevance

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
  "summary": "" or "Short summary explaining role fit (max 70 words)",
  "experience_order": [0, 1, 2],
  "experience_bullets": {{
    "0": ["Rewritten Sidel bullet 1 (fact-based, role-relevant)", "Rewritten Sidel bullet 2", "Rewritten Sidel bullet 3"],
    "1": ["Rewritten MadeByAkim bullet 1", "Rewritten MadeByAkim bullet 2"],
    "2": ["Rewritten Vassard bullet 1"]
  }},
  "project_order": [0, 1, 2],
  "project_bullets": {{
    "0": ["Rewritten Elevia description (fact-based)"],
    "1": ["Rewritten Job Apply Assistant description"],
    "2": ["Rewritten V.I.E Matcher description"]
  }},
  "ats_keywords": ["Keyword1", "Keyword2"]
}}

---

CRITICAL RULES

TRUTH IS IMMUTABLE:
- Companies, dates, roles NEVER fabricated
- Technologies mentioned must exist in Master CV
- Achievements must be real and provable
- No invented metrics or percentages
- No false claims of responsibility
- experience_order: [0, 1, 2] (sequence immutable)

NARRATIVE IS FLEXIBLE:
- Bullets can be rewritten for clarity and relevance
- Weak bullets can be removed if irrelevant to role
- Strong bullets can be amplified
- Vocabulary can adapt to match role domain
- Tone can shift (technical → business, ops → finance)
- Focus: signal over noise, relevance over completeness

STYLE GUIDELINES:
- Clarity beats complexity
- Relevance beats exhaustiveness
- Signal beats noise
- Credibility beats keyword stuffing
- Simple + clear beats buzzword-heavy
- Avoid: ChatGPT tone, generic language, keyword stuffing
- Use: confidence, simplicity, clarity, directness

FINAL TEST:
Would a founder, recruiter, or hiring manager understand in 30 seconds:
1. Who this person is?
2. What value they bring?
3. Why they fit this role?

If not: SIMPLIFY. Clarity beats everything.

PHILOSOPHY:
100% truthful source material. Flexible wording. Flexible emphasis. Flexible narrative.
No fabricated facts. No invented metrics. No invented technologies.
"""
