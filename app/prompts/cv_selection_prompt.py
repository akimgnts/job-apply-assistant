"""Selection prompt for CV adaptation.

CRITICAL: This prompt NEVER asks OpenAI to rewrite content.

Purpose:
1. Score each Master CV section for relevance to the job
2. Recommend which sections to show/hide
3. Suggest ordering by relevance

OpenAI returns ONLY metadata (scores, order), never text.
Actual CV text comes directly from Master CV source.
"""


def get_cv_selection_prompt(analysis: dict, positioning: str, master_cv: dict) -> str:
    """Prompt for selecting and ordering Master CV sections by relevance.

    Args:
        analysis: Job offer analysis (company, missions, skills, etc.)
        positioning: Selected positioning angle (e.g., "Data Analyst | Business Intelligence")
        master_cv: Master CV structure with locked content

    Returns:
        Prompt string for OpenAI to score sections
    """

    # Format Master CV for analysis
    experiences_list = []
    for i, exp in enumerate(master_cv.get("experiences", [])):
        exp_str = f"Experience #{i}: {exp['title']} @ {exp['company']} ({exp['dates']})"
        exp_str += f"\n    Context: {exp.get('context', 'N/A')}"
        exp_str += f"\n    Bullet count: {len(exp.get('bullets', []))}"
        if exp.get('bullets'):
            exp_str += f"\n    Topics: {', '.join(b[:50] + '...' if len(b) > 50 else b for b in exp.get('bullets', [])[:2])}"
        experiences_list.append(exp_str)

    projects_list = []
    for i, proj in enumerate(master_cv.get("projects", [])):
        proj_str = f"Project #{i}: {proj['title']}"
        proj_str += f"\n    Stack: {proj.get('stack', 'N/A')}"
        proj_str += f"\n    Bullet count: {len(proj.get('bullets', []))}"
        if proj.get('bullets'):
            proj_str += f"\n    Topics: {', '.join(b[:50] + '...' if len(b) > 50 else b for b in proj.get('bullets', [])[:1])}"
        projects_list.append(proj_str)

    skills_list = []
    for i, skill in enumerate(master_cv.get("skills", [])):
        skill_str = f"Skill #{i}: {skill.get('label', 'N/A')}"
        skill_str += f"\n    Depth: {skill.get('content', 'N/A')[:60]}..."
        skills_list.append(skill_str)

    return f"""TASK: Score and select Master CV sections by relevance to job offer.

CRITICAL CONSTRAINTS:
- You NEVER rewrite experience/project/skill text
- You NEVER invent metrics or achievements
- You ONLY score relevance and suggest order
- Actual CV text comes directly from Master CV (you don't generate it)
- Your output ONLY contains: scores, section IDs, and order suggestions

---

JOB CONTEXT

Position: {analysis.get('job_title', 'N/A')} @ {analysis.get('company', 'N/A')}
Positioning: {positioning}

Key Missions:
{chr(10).join('- ' + m for m in analysis.get('missions', [])[:5])}

Required Skills:
{chr(10).join('- ' + s for s in analysis.get('required_skills', [])[:8])}

---

MASTER CV CONTENT (source of truth - DO NOT MODIFY)

Experiences:
{chr(10).join(experiences_list)}

Projects:
{chr(10).join(projects_list)}

Skills:
{chr(10).join(skills_list)}

---

TASK

For each experience, project, and skill section:

1. Score relevance to this job (0.0 to 1.0)
   - 0.9-1.0: Directly relevant, strong match
   - 0.7-0.8: Related, useful context
   - 0.5-0.6: Tangentially relevant
   - 0.3-0.4: Weak connection
   - 0.0-0.2: Not relevant, could hide

2. Recommend show/hide:
   - show: true  (include in adaptation)
   - show: false (hide in adaptation, but keep in source)

3. Suggest order within shown sections:
   - 1, 2, 3... (most relevant first)

Return JSON ONLY (no explanations):

{{
  "experiences": [
    {{"id": 0, "relevance": 0.95, "show": true, "order": 1, "reason": "Direct match: Sidel → analytical role, BI, dashboards"}},
    {{"id": 1, "relevance": 0.75, "show": true, "order": 2, "reason": "Automation and API work relevant"}},
    {{"id": 2, "relevance": 0.4, "show": false, "order": 3, "reason": "Sales-focused, less relevant"}}
  ],
  "projects": [
    {{"id": 0, "relevance": 0.8, "show": true, "order": 1, "reason": "Data + AI project, relevant"}},
    {{"id": 1, "relevance": 0.85, "show": true, "order": 2, "reason": "Job application + Telegram, automation focus"}},
    {{"id": 2, "relevance": 0.6, "show": true, "order": 3, "reason": "Matching engine, less central"}}
  ],
  "skills": [
    {{"id": 0, "relevance": 0.95, "show": true, "order": 1}},
    {{"id": 1, "relevance": 0.85, "show": true, "order": 2}},
    {{"id": 2, "relevance": 0.7, "show": true, "order": 3}},
    {{"id": 3, "relevance": 0.4, "show": false, "order": 4}},
    {{"id": 4, "relevance": 0.3, "show": false, "order": 5}},
    {{"id": 5, "relevance": 0.6, "show": true, "order": 4}}
  ]
}}

CONSTRAINTS:
- Always score ALL sections (don't skip any)
- Keep Sidel as primary (relevance > 0.8)
- Keep MadeByAkim if automation/API/BI skills match
- Never invent text or metrics
- Score is metadata only; actual CV text is from Master CV
"""
