"""Keep employer business sector separate from the job's functional domain."""
from __future__ import annotations

from typing import Any


SECTOR_KEYS = (
    "activitySectorName", "activitySectorLabel", "secteurActiviteLibelle",
    "libelleSecteurActivite", "activity_sector", "activitySector", "secteurActivite",
)


def _source_label(value: Any) -> str | None:
    if isinstance(value, str):
        label = value.strip()
        return label if label and not label.isdigit() else None
    if isinstance(value, dict):
        for key in ("label", "name", "libelle", "nameFr", "labelFr", "value"):
            result = _source_label(value.get(key))
            if result:
                return result
    if isinstance(value, list):
        labels = [label for item in value if (label := _source_label(item))]
        return " · ".join(dict.fromkeys(labels)) or None
    return None


def source_activity_sector(payload: dict | None) -> str | None:
    """Return an employer-sector label only when a source supplies a label."""
    if not isinstance(payload, dict):
        return None
    for key in SECTOR_KEYS:
        result = _source_label(payload.get(key))
        if result:
            return result[:255]
    return None


_DOMAIN_RULES = {
    "Data & BI": ("data analyst", "data analysis", "data analytics", "business intelligence", "power bi", "tableau de bord", "reporting", "analytics engineer", "data scientist", "data quality"),
    "IT & Software": ("software engineer", "software developer", "développeur", "developer", "backend", "frontend", "devops", "cloud engineer", "sre "),
    "Finance & Comptabilité": ("financial analyst", "finance", "accounting", "comptabilité", "comptable", "audit", "contrôle de gestion"),
    "Marketing & Communication": ("marketing", "communication", "social media", "content manager", "brand", "campaign"),
    "Commercial & Vente": ("sales", "commercial", "business development", "account executive", "account manager", "vente", "customer success"),
    "Supply Chain & Opérations": ("supply chain", "logistique", "operations", "opérations", "procurement", "achats", "production planning"),
    "Produit & Projet": ("product manager", "product owner", "chef de projet", "project manager", "pmo", "product analyst"),
    "Ressources humaines": ("human resources", "ressources humaines", "recruiter", "recruteur", "talent acquisition", "hr business partner"),
    "Juridique": ("legal counsel", "juriste", "avocat", "compliance officer", "droit des affaires"),
    "Ingénierie industrielle": ("mechanical engineer", "industrial engineer", "ingénieur mécanique", "automatisme industriel", "maintenance industrielle"),
    "Santé & Médical": ("nurse", "infirmier", "médecin", "medical doctor", "pharmacist", "pharmacien", "clinical research"),
}


def classify_activity_domain(title: str | None, description: str | None = None) -> tuple[str | None, str | None]:
    """Classify a job's functional domain; ambiguous and unknown remain null."""
    text = f"{title or ''} {description or ''}".casefold()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in _DOMAIN_RULES.items()
    }
    ranked = sorted(((score, domain) for domain, score in scores.items() if score), reverse=True)
    if not ranked:
        return None, None
    best_score, best_domain = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0
    if best_score == second_score:
        return None, "low"
    confidence = "high" if best_score >= 3 and best_score - second_score >= 2 else "medium" if best_score >= 2 and best_score > second_score else "low"
    if confidence == "low":
        return None, confidence
    return best_domain, confidence


