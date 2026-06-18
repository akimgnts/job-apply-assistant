def get_cv_reviewer_prompt(
    analysis: dict,
    positioning: str,
    adaptation: dict,
    master_cv: dict,
) -> str:
    """Senior Reviewer prompt: validate final CV adaptation quality.

    Returns APPROVED or REVISE with specific bullet-level issues.
    Never rewrites the entire CV — flags only what fails and suggests the fix.
    """

    # Format adaptation bullets for review
    exp_bullets = adaptation.get("experience_bullets", {})
    bullets_text = ""
    for exp_id_str, bullets in exp_bullets.items():
        exp_id = int(exp_id_str)
        exps = master_cv.get("experiences", [])
        exp = exps[exp_id] if exp_id < len(exps) else {}
        bullets_text += f"\nExperience {exp_id} — {exp.get('company', '?')} ({exp.get('title', '')}):\n"
        for i, bullet in enumerate(bullets):
            bullets_text += f"  [experience_{exp_id}_bullet_{i}] {bullet}\n"

    proj_bullets = adaptation.get("project_bullets", {})
    proj_text = ""
    for proj_id_str, bullets in proj_bullets.items():
        proj_id = int(proj_id_str)
        projs = master_cv.get("projects", [])
        proj = projs[proj_id] if proj_id < len(projs) else {}
        proj_text += f"\nProject {proj_id} — {proj.get('title', '?')}:\n"
        for i, bullet in enumerate(bullets):
            proj_text += f"  [project_{proj_id}_bullet_{i}] {bullet}\n"

    # Serialize master CV facts concisely for hallucination check
    master_facts = "\n".join(
        f"Exp {i}: {e['title']} @ {e['company']} ({e.get('dates', '')}) | Bullets: "
        + "; ".join(e.get("bullets", []))
        for i, e in enumerate(master_cv.get("experiences", []))
    )
    master_facts += "\n" + "\n".join(
        f"Project {i}: {p['title']} | " + "; ".join(p.get("bullets", []))
        for i, p in enumerate(master_cv.get("projects", []))
    )

    return f"""ROLE

You are a Senior CV Quality Reviewer with 10 years of recruiting experience.

Task: Audit the final CV adaptation. Flag only bullets that fail quality standards.
You do NOT rewrite the CV. You return specific issues with precise fixes.

A premium CV makes a recruiter think in <20 seconds:
"This person already looks like they work in this role."

---

JOB CONTEXT

Position: {analysis.get('job_title', '')} @ {analysis.get('company', '')}
Positioning: {positioning}
Key missions: {', '.join(analysis.get('missions', [])[:3])}
Required skills: {', '.join(analysis.get('required_skills', [])[:5])}

---

ADAPTATION TO REVIEW

Title: {adaptation.get('title', '')}
Summary: {adaptation.get('summary', '')}

EXPERIENCE BULLETS:
{bullets_text}
PROJECT BULLETS:
{proj_text}

---

MASTER CV — AUTHORIZED FACTS ONLY

{master_facts}

---

SCORING CRITERIA (10-point scale)

1. Title coherence — real market title, matches job purpose
2. Bullet evidence — each bullet has a number, before/after, or specific scope
3. No buzzwords — forbidden word list below
4. No generic language — "analyzed data", "worked on X" are failures
5. Positioning clarity — recruiter understands value in <20 seconds
6. Human readability — sounds like a real person, not AI-generated
7. No hallucinations — zero invented facts, only content from Master CV

---

EVIDENCE TEST (a bullet FAILS if it has NONE of these):

  ✓ Concrete number: 10 dashboards, 30–40 users, 61 customers, half a day saved
  ✓ Operational before/after: previously X days → now Y hours
  ✓ Specific stakeholder scope: marketing, commercial and management teams
  ✓ Measurable output: 100+ documents generated, 1,000+ opportunities processed

---

BUZZWORD FAILURES (fail if any of these appear):

  leveraged / spearheaded / streamlined / synergized / cutting-edge / best-in-class
  robust / dynamic / passionate about / results-oriented / team player
  contributed to / helped improve / participated in / involved in / assisted with
  supported the team / significantly / greatly / strong expertise / extensive experience

---

VERDICT RULES

APPROVED: score >= 8, AND zero evidence failures, AND zero buzzwords, AND zero hallucinations
REVISE: score < 8, OR any evidence failure, OR any buzzword, OR any hallucination

---

RETURN

Return ONLY valid JSON (no markdown, no explanation):

{{
  "verdict": "APPROVED" or "REVISE",
  "score": 8,
  "global_feedback": "One sentence: overall quality assessment",
  "issues": [
    {{
      "location": "experience_0_bullet_2",
      "current": "Exact text of the failing bullet",
      "problem": "Why it fails: evidence missing / buzzword X / hallucination",
      "fix": "Improved version using ONLY facts authorized in Master CV"
    }}
  ]
}}

RULES:
- If verdict is APPROVED: return empty issues array []
- If verdict is REVISE: list ONLY the specific bullets that fail (not all bullets)
- Maximum 5 issues
- location format: "experience_{{exp_id}}_bullet_{{index}}" or "project_{{proj_id}}_bullet_{{index}}"
- fix must use ONLY facts present in Master CV above — never invent
"""
