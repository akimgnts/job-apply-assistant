def get_quality_check_prompt(document_content: str, document_type: str, profile_blocks: list) -> str:
    profile_skills = set()
    profile_companies = set()
    profile_experiences = []

    for block in profile_blocks:
        if block['category'] == 'skill':
            profile_skills.update(block.get('tags', []))
        if block['category'] == 'experience':
            profile_companies.add(block['title'].split(' — ')[0])
            profile_experiences.append(block['title'])

    profile_text = "\n".join([f"- {exp}" for exp in profile_experiences])
    skills_text = ", ".join(profile_skills)

    return f"""Quality check for this {document_type}.

PROFILE BASELINE:
Experiences: {profile_text}
Skills: {skills_text}

DOCUMENT TO CHECK:
{document_content}

Verify:
1. Does document claim ANY skill not in the profile baseline? (List any)
2. Does document reference ANY experience not in profile? (List any)
3. Is document too generic/template-like? (yes/no)
4. Are there red flags for overclaiming? (List any)

Return a JSON with:
{{
  "has_invented_skills": boolean,
  "invented_skills": ["list"],
  "has_invented_experience": boolean,
  "invented_experiences": ["list"],
  "is_generic": boolean,
  "overclaiming_risks": ["list"],
  "quality_score": 0-10,
  "recommendation": "SAFE / REVIEW / REJECT"
}}"""
