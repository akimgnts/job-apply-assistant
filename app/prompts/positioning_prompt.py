def get_positioning_prompt(analysis_json: dict) -> str:
    return f"""Based on this job analysis, choose the BEST positioning angle from this list:
- Data Analyst BI
- Marketing Data Analyst
- Data & AI Project Analyst
- Automation / AI Workflow Analyst
- Data Steward / Data Quality
- Business Analyst orienté data
- Product / Ops Analyst

Analysis context:
Company: {analysis_json['company']}
Job Title: {analysis_json['job_title']}
Required Skills: {', '.join(analysis_json['required_skills'])}
Missions: {', '.join(analysis_json['missions'])}

Return ONLY the chosen angle name."""
