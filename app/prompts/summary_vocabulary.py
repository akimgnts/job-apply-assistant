"""Summary vocabulary guide: forbidden and preferred words.

Philosophy: Sound junior-to-mid level. Never exaggerate.
Focus on reality, not impression.
"""

# FORBIDDEN WORDS (sound expert/overqualified/exaggerated)
FORBIDDEN_WORDS = {
    "expert": "Background in, exposure to, skilled in",
    "extensive experience": "Experience across, worked on",
    "architected": "Designed, built, contributed to",
    "managed": "Coordinated, supported, collaborated with",
    "owned": "Responsible for, contributed to",
    "mentored": "Worked alongside, supported",
    "led": "Contributed to, worked on, participated in",
    "enterprise-grade": "Production-ready, reliable, stable",
    "robust and scalable": "Reliable, stable, handles multiple",
    "advanced expertise": "Experience with, familiarity with, worked on",
    "seasoned": "Experienced, skilled",
    "specialist in": "Background in, exposure to",
    "experienced in delivering": "Contributed to, worked on, helped deliver",
    "managing teams": "Coordinating with, working with, collaborating with",
    "proven track record": "Track record, experience with",
    "world-class": "High-quality, professional",
    "cutting-edge": "Modern, current, up-to-date",
    "driving": "Contributing to, supporting, enabling",
    "spearheaded": "Worked on, contributed to, initiated",
    "pioneer": "Early adopter, first to try",
    "visionary": "Forward-thinking, interested in",
}

# PREFERRED VOCABULARY (sounds authentic, junior-to-mid level)
PREFERRED_WORDS = [
    "background in",
    "exposure to",
    "worked on",
    "contributed to",
    "supported",
    "experience across",
    "business-oriented profile",
    "data-oriented profile",
    "combining",
    "focused on",
    "interested in",
    "collaborated with",
    "coordinated with",
    "helped deliver",
    "participated in",
    "involved in",
    "familiar with",
    "knowledgeable about",
    "skilled in",
    "proficient with",
    "experienced with",
    "hands-on experience",
    "practical experience",
    "working knowledge",
    "built",
    "designed",
    "developed",
    "created",
    "implemented",
    "enabled",
    "supported",
    "improved",
    "optimized",
    "automated",
    "integrated",
]

def check_forbidden_words(text: str) -> list:
    """Check if text contains forbidden words.

    Returns list of (word, suggestion) tuples.
    """
    issues = []
    text_lower = text.lower()

    for forbidden, suggestion in FORBIDDEN_WORDS.items():
        if forbidden in text_lower:
            issues.append((forbidden, suggestion))

    return issues

def get_vocabulary_guide() -> str:
    """Return guide for summary vocabulary."""
    return """
SUMMARY VOCABULARY GUIDE

SOUND: Junior-to-mid level, authentic, honest
DO NOT SOUND: Expert, overqualified, exaggerated

FORBIDDEN (if used, sound like a liar):
""" + "\n".join(f"  • {word}: use '{suggestion}' instead" for word, suggestion in FORBIDDEN_WORDS.items()) + """

PREFERRED (authentic, credible, junior-to-mid):
""" + "\n".join(f"  • {word}" for word in PREFERRED_WORDS[:20]) + """
  ... (see code for full list)

EXAMPLES:

❌ WRONG (sounds expert):
"Seasoned data expert with extensive experience architected enterprise-grade
data pipelines and drove advanced AI solutions for teams across Europe."

✅ RIGHT (sounds junior-mid):
"Data-oriented profile combining experience across data pipelines, reporting,
and automation. Worked on multi-source data consolidation and supported
stakeholder visibility across international teams."

KEY PRINCIPLE:
Tell the truth simply. Sound like someone who has done real work,
not someone trying to convince.
"""
