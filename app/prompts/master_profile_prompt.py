def get_master_profile_prompt(profile_blocks: list) -> str:
    """Generate a polished master profile narrative from all profile blocks.

    This prompt is job-agnostic: it produces a complete, honest profile
    document that can be used as a baseline for any application.
    """
    blocks_text = "\n\n".join(
        f"[{block['category'].upper()} | priority={block['priority']} | {block['truth_level']}]\n"
        f"Title: {block['title']}\n"
        f"Content: {block['content']}\n"
        f"Tags: {', '.join(block['tags']) if block['tags'] else 'none'}"
        for block in profile_blocks
    )

    return f"""You are a senior career strategist writing a MASTER PROFILE document.

A master profile is a complete, honest, job-agnostic narrative of a candidate's
background. It is not a CV and not tailored to any specific offer.
It is the source of truth from which targeted CVs are derived.

RULES:
- Use ONLY the authorized profile blocks below. Never invent anything.
- Blocks marked "in_progress" or "project" are real but ongoing — present them as such.
- Higher priority = more prominent narrative space.
- Do NOT add skills, results, or experiences not present in the blocks.
- Write in clear, professional French.
- Do not use buzzwords or inflate seniority.

---

AUTHORIZED PROFILE BLOCKS:

{blocks_text}

---

DELIVERABLE — Master Profile structured as follows:

## Identité professionnelle
2-3 sentences. Who is this person, what is their core value, what type of role they target.

## Expériences
For each experience block: role, context, concrete missions, skills demonstrated.

## Projets
For each project block: objective, what was built, current status, technologies used.

## Formation
Degree, school, domain.

## Compétences
Grouped by domain. Only what is explicitly listed in the blocks.

## Positionnements possibles
Based on the profile, list 2-3 realistic job titles this candidate can credibly apply for.

---

CRITICAL: Do not invent. Do not inflate. Present what exists, clearly.
"""
