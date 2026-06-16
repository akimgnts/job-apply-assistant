"""Skill profile definitions for CV adaptation.

Maps positioning angles to skill emphasis rules.
Skill profiles tell the Narrative Engine which skills to highlight,
reduce, or reorder based on the target role.

Architecture:
- positioning angle → skill_profile (many-to-one mapping)
- skill_profile → skill_section_order + skill_section_emphasis
- CVAdaptationAgent uses these to reorder and emphasize skill sections
"""

SKILL_PROFILES = {
    "marketing_crm": {
        "description": "Marketing, CRM, Customer Experience, Campaign roles",
        "prioritize": [
            "Business Systems",
            "Data & Analytics",
            "Creative & Delivery",
        ],
        "reduce": [
            "Backend & Data Systems",
            "AI & LLM Workflows",
        ],
        "skill_section_order": [
            "Business Systems",
            "Data & Analytics",
            "Creative & Delivery",
            "Automation & APIs",
            "AI & LLM Workflows",
            "Backend & Data Systems",
        ],
        "skill_section_emphasis": {
            "Business Systems": "high",
            "Data & Analytics": "normal",
            "Creative & Delivery": "normal",
            "Automation & APIs": "normal",
            "AI & LLM Workflows": "low",
            "Backend & Data Systems": "low",
        }
    },

    "data_bi": {
        "description": "Business Intelligence, BI, Analytics, Reporting, Dashboards",
        "prioritize": [
            "Data & Analytics",
            "Business Systems",
            "Automation & APIs",
        ],
        "reduce": [
            "Creative & Delivery",
            "AI & LLM Workflows",
        ],
        "skill_section_order": [
            "Data & Analytics",
            "Business Systems",
            "Automation & APIs",
            "Backend & Data Systems",
            "AI & LLM Workflows",
            "Creative & Delivery",
        ],
        "skill_section_emphasis": {
            "Data & Analytics": "high",
            "Business Systems": "normal",
            "Automation & APIs": "normal",
            "Backend & Data Systems": "normal",
            "AI & LLM Workflows": "low",
            "Creative & Delivery": "low",
        }
    },

    "finance_reporting": {
        "description": "Finance, Reporting, Business Analysis, KPI, Decision Support",
        "prioritize": [
            "Data & Analytics",
            "Business Systems",
            "Automation & APIs",
        ],
        "reduce": [
            "AI & LLM Workflows",
            "Creative & Delivery",
            "Backend & Data Systems",
        ],
        "skill_section_order": [
            "Data & Analytics",
            "Business Systems",
            "Automation & APIs",
            "Backend & Data Systems",
            "AI & LLM Workflows",
            "Creative & Delivery",
        ],
        "skill_section_emphasis": {
            "Data & Analytics": "high",
            "Business Systems": "high",
            "Automation & APIs": "normal",
            "Backend & Data Systems": "low",
            "AI & LLM Workflows": "low",
            "Creative & Delivery": "low",
        }
    },

    "data_ai": {
        "description": "AI, LLM, Automation, Python, Data Engineering, ML workflows",
        "prioritize": [
            "AI & LLM Workflows",
            "Backend & Data Systems",
            "Data & Analytics",
            "Automation & APIs",
        ],
        "reduce": [
            "Creative & Delivery",
        ],
        "skill_section_order": [
            "AI & LLM Workflows",
            "Backend & Data Systems",
            "Data & Analytics",
            "Automation & APIs",
            "Business Systems",
            "Creative & Delivery",
        ],
        "skill_section_emphasis": {
            "AI & LLM Workflows": "high",
            "Backend & Data Systems": "high",
            "Data & Analytics": "normal",
            "Automation & APIs": "normal",
            "Business Systems": "normal",
            "Creative & Delivery": "low",
        }
    },

    "automation_ops": {
        "description": "Automation, Workflow, Operations, Integration, Process Improvement",
        "prioritize": [
            "Automation & APIs",
            "Business Systems",
            "Data & Analytics",
        ],
        "reduce": [
            "AI & LLM Workflows",
            "Creative & Delivery",
        ],
        "skill_section_order": [
            "Automation & APIs",
            "Business Systems",
            "Data & Analytics",
            "Backend & Data Systems",
            "AI & LLM Workflows",
            "Creative & Delivery",
        ],
        "skill_section_emphasis": {
            "Automation & APIs": "high",
            "Business Systems": "high",
            "Data & Analytics": "normal",
            "Backend & Data Systems": "normal",
            "AI & LLM Workflows": "low",
            "Creative & Delivery": "low",
        }
    },

    "creative_marketing": {
        "description": "Creative, Design, Content, Adobe, Social Media, Branding",
        "prioritize": [
            "Creative & Delivery",
            "Business Systems",
            "Data & Analytics",
        ],
        "reduce": [
            "Backend & Data Systems",
            "AI & LLM Workflows",
        ],
        "skill_section_order": [
            "Creative & Delivery",
            "Business Systems",
            "Data & Analytics",
            "Automation & APIs",
            "AI & LLM Workflows",
            "Backend & Data Systems",
        ],
        "skill_section_emphasis": {
            "Creative & Delivery": "high",
            "Business Systems": "normal",
            "Data & Analytics": "normal",
            "Automation & APIs": "normal",
            "AI & LLM Workflows": "low",
            "Backend & Data Systems": "low",
        }
    },

    "general_business_data": {
        "description": "Default: Business Analysis, Reporting, Data, General roles",
        "prioritize": [
            "Data & Analytics",
            "Business Systems",
            "Automation & APIs",
        ],
        "reduce": [],
        "skill_section_order": [
            "Data & Analytics",
            "Business Systems",
            "Automation & APIs",
            "Backend & Data Systems",
            "AI & LLM Workflows",
            "Creative & Delivery",
        ],
        "skill_section_emphasis": {
            "Data & Analytics": "normal",
            "Business Systems": "normal",
            "Automation & APIs": "normal",
            "Backend & Data Systems": "normal",
            "AI & LLM Workflows": "normal",
            "Creative & Delivery": "normal",
        }
    }
}


def get_skill_profile(profile_key: str) -> dict:
    """Get skill profile definition by key.

    Falls back to general_business_data if invalid.
    """
    return SKILL_PROFILES.get(profile_key, SKILL_PROFILES["general_business_data"])


def validate_skill_profile(profile_key: str) -> bool:
    """Check if skill profile key is valid."""
    return profile_key in SKILL_PROFILES
