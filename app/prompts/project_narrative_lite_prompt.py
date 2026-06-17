def get_project_narrative_lite_prompt(
    projects: list,
    positioning: str,
    skill_profile: str,
) -> str:
    """Project Narrative Engine Lite: Make projects credible without bloating CV.

    Philosophy:
    - Projects are SUPPORT, not main narrative
    - Sidel is the anchor (6-7 bullets)
    - Projects are evidence (max 5 bullets total)
    - Never fake impact
    - Never "startup" wording for side projects
    - Every bullet must support target role

    Rules:
    - Elevia: max 2 bullets
    - Job Apply Assistant: max 2 bullets
    - V.I.E Matcher: max 1 bullet
    - Total project bullets: max 5

    Purpose:
    Stop under-selling without creating 3-page CV.
    """

    projects_context = "\n\n".join(
        f"PROJECT #{i}: {p.get('title', '')}\n"
        f"Stack: {p.get('stack', 'N/A')}\n"
        f"Current bullets: {p.get('bullets', [])}"
        for i, p in enumerate(projects)
    )

    return f"""PROJECT NARRATIVE ENGINE LITE

=== PHILOSOPHY ===

Projects are NOT your main story. Sidel is.
Projects are EVIDENCE that you've built things.

Goal: Make projects credible without inflating.

Rules:
- Elevia (project 0): max 2 bullets
- Job Apply Assistant (project 1): max 2 bullets
- V.I.E Matcher (project 2): max 1 bullet
- Total project bullets across all: max 5

Each bullet must:
✓ Be truthful (no made-up impact)
✓ Support positioning (relevant to target role)
✓ Show capability (what you actually built)
✗ Don't use "startup" language
✗ Don't fake scale ("reached 1M users")
✗ Don't claim credit not held
✗ Don't be technical dumping

=== POSITIONING ===

Target: {positioning}
Skill Profile: {skill_profile}

Adapt project bullets to emphasize what matters for THIS role.

=== PROJECT CONTEXT ===

{projects_context}

=== TASK ===

For each project:
1. Keep max bullets (Elevia 2, JAA 2, VIE 1)
2. Rewrite to be more credible/relevant
3. Remove weak bullets if necessary
4. Add substantive detail (without fake impact)
5. Support the target positioning

Examples of WRONG:
- "Built a MVP that reached 1000 users" (fake scale for hobby project)
- "Led a startup-style data platform" (not a startup, side project)
- "Architected ML pipeline" (if just implemented, didn't design)
- "Open-source solution powering teams" (too much hype for side project)

Examples of RIGHT:
- "Document canonicalization + scoring system for job matching"
- "Telegram bot integrating OpenAI for CV generation and job analysis"
- "Automated matching algorithm coordinating 500+ VIE applications"

=== CRITICAL ===

ELEVIA (project 0):
Max 2 bullets.
Currently weak. Needs credibility boost.
Core: matching algorithm, data extraction, scoring, document generation.
NOT: "startup", "scaled", "optimized"
YES: "built", "implemented", "coordinated"

JOB APPLY ASSISTANT (project 1):
Max 2 bullets.
Core: Telegram bot, job analysis, CV generation, OpenAI integration.
NOT: "powered millions", "enterprise-grade"
YES: "built", "integrated", "generated"

V.I.E MATCHER (project 2):
Max 1 bullet.
Core: matching automation, Google Sheets integration, Telegram.
NOT: "scaled", "led"
YES: "automated", "coordinated"

=== RETURN ===

Return ONLY valid JSON:

{{
  "projects": [
    {{
      "id": 0,
      "title": "Elevia",
      "bullets": [
        "Bullet 1 (credible, role-relevant)",
        "Bullet 2 (credible, role-relevant)"
      ]
    }},
    {{
      "id": 1,
      "title": "Job Apply Assistant",
      "bullets": [
        "Bullet 1 (credible, role-relevant)",
        "Bullet 2 (credible, role-relevant)"
      ]
    }},
    {{
      "id": 2,
      "title": "V.I.E Matcher",
      "bullets": [
        "Bullet 1 (credible, role-relevant)"
      ]
    }}
  ],
  "total_project_bullets": 5,
  "notes": "How bullets support positioning"
}}

=== CONSTRAINT ===

Sum(all project bullets) ≤ 5

If any project has more bullets than allowed, TRUNCATE to max.
"""
