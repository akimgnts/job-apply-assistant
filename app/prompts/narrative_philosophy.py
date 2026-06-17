"""Premium Narrative Engine V2 Philosophy.

Core principles for CV adaptation and positioning.
Centralizes philosophy, rules, and guardrails.
"""

# TRUTH PHILOSOPHY
TRUTH_IMMUTABLE = """
Truth is immutable. Narrative is flexible.

Never invent:
- Companies, dates, certifications
- Tools, technologies, metrics
- Responsibilities, achievements

Different wording: OK.
Different emphasis: OK.
Different vocabulary: OK.

Underlying reality: NEVER CHANGES.
"""

# POSITIONING PHILOSOPHY
POSITIONING_RULES = """
Do not infer role from isolated responsibilities.
Infer from business purpose of position.

Distinguish:
1. Primary role (real market title)
2. Secondary domains (dimensions, not titles)
3. Tools (supporting evidence)

Example:
Primary: Marketing Project Manager
Secondary: CRM, Customer Experience, Analytics
Tools: Power BI, Excel

Never invent titles.
Use real market titles.
CRM is not a job title. It's a dimension.
"""

# SIGNAL VS NOISE
SIGNAL_RULES = """
Remove noise. Keep signal.
Do NOT optimize for brevity.
Optimize for: clarity, credibility, positioning, relevance.

Prefer strong stories over long tool lists.
Candidate must sound like a real person.
Not a collection of keywords.

Avoid:
- ATS language
- Buzzwords
- Generic corporate language
- ChatGPT tone
"""

# SKILLS STRATEGY
SKILLS_RULES = """
Skills are not equally important.
Purpose is NOT to show everything.
Purpose IS to make target-role fit obvious.

Use skill_profile to:
- Prioritize relevant skills
- Reduce technical noise
- Place tools in supporting role, not lead role

Business understanding > keyword density.
"""

# BULLET WRITING
BULLET_RULES = """
Every bullet = evidence, not keyword.

Structure:
ACTION + PURPOSE + STAKEHOLDERS + CONTEXT

Bad:
- Analyzed data.
- Developed dashboards.
- Monitored KPIs.

Better:
- Consolidated and analyzed multi-source business data to
  improve visibility on customer and market performance
  across international stakeholders.

- Developed reporting structures and monitored KPIs using
  Power BI and Excel to support business decisions and
  marketing initiatives.

- Collaborated with sales, marketing and communication teams
  to support projects and improve stakeholder alignment.

Tools only when they add value.
"""

# BULLET DENSITY
BULLET_DENSITY = {
    "premium": (6, 7),      # 6-7 bullets
    "standard": (4, 5),     # 4-5 bullets
    "minimal": (2, 3),      # 2-3 bullets
}

EXPERIENCE_DENSITY = {
    "sidel": "premium",      # Flagship: 6-7 bullets
    "madebyakim": "standard", # Projects: 4-5 bullets
    "vassard": "minimal",    # Business dev: 2-3 bullets
}

# FLAGSHIP EXPERIENCE RULES
FLAGSHIP_RULES = """
Strongest experience = calling card.

Never compress excessively.
Represent 40-50% of experience section.

Preserve:
- Business context
- Stakeholders
- Responsibilities
- Breadth

Reader understands in <20 seconds why this matters.

MINIMUM 5 bullets.
Use PREMIUM bullet density (6-7).
"""

# SUMMARY RULES
SUMMARY_RULES = """
Summary should NOT explain the past.
Summary SHOULD explain why profile makes sense.

Max: 70 words.

Avoid:
- Results-driven professional
- Passionate about
- Dynamic and motivated
- Fast learner

Sound human. Sound premium. Sound natural.
"""

# EXPERIENCE PHILOSOPHY
EXPERIENCE_PHILOSOPHY = """
Experiences are NOT chronological stories.
Experiences ARE evidence.

Question:
"Why does this experience make the candidate relevant for this role?"

Not:
"What has the candidate done?"

Weak bullets may disappear.
Strong bullets should be amplified.
Weak bullets never become strong bullets—they disappear.
"""

# PROJECTS PHILOSOPHY
PROJECTS_PHILOSOPHY = """
Projects = supporting evidence, not center of gravity.

Keep:
- Elevia
- Job Apply Assistant
- V.I.E Matcher

Adjust ORDER depending on target role.
Do NOT overexpose technical projects for non-technical positions.
"""

# FINAL TEST
FINAL_TEST = """
Ask yourself:

Would a founder, recruiter or hiring manager understand
in less than 30 seconds:

1. Who is this person?
2. What value do they bring?
3. Why do they fit the role?

If not: SIMPLIFY.

Clarity > Complexity.
Credibility > Optimization.
Positioning > Keyword stuffing.
Signal > Noise.
Truth > Everything.
Substance > Brevity.
"""

# PREMIUM LANGUAGE GUIDE
LANGUAGE_GUIDE = {
    "avoid": [
        "analyzed",
        "developed",
        "monitored",
        "supported",
        "responsible for",
        "managed",
        "handled",
        "worked on",
        "involved in",
    ],
    "prefer_structure": "ACTION + PURPOSE + CONTEXT + STAKEHOLDERS",
    "examples": {
        "bad": "Analyzed customer data and developed dashboards.",
        "good": "Consolidated and analyzed multi-source customer data to support business decisions and improve visibility for stakeholders.",
    }
}

# COMMON ERRORS TO AVOID
ANTI_PATTERNS = [
    "Keyword stuffing",
    "Tool-heavy language",
    "Generic corporate speak",
    "ChatGPT-tone adjectives",
    "Exaggerated achievements",
    "Invented metrics",
    "Weak linking words",
    "Bullets that don't land",
    "Overcompressing flagship experience",
    "Synthetic job titles",
]
