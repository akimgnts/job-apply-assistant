"""Fast deterministic scoring for job-offer radar triage."""
from __future__ import annotations
from datetime import datetime, timedelta
from app.database.models import JobOffer


class OfferSignalService:
    """Score offers without LLM calls so the radar can stay fast and cheap."""

    ROLE_KEYWORDS = {
        'Data / BI': ('data analyst', 'business analyst', 'bi analyst', 'power bi', 'sql', 'dashboard', 'analytics', 'crm'),
        'Automation / AI': ('automation', 'automatisation', 'ia', 'ai ', 'machine learning', 'workflow', 'python'),
        'Product / Ops': ('product owner', 'product analyst', 'sales ops', 'revenue ops', 'business operations'),
    }
    TOOL_KEYWORDS = ('sql', 'power bi', 'python', 'crm', 'dashboard', 'automation', 'analytics', 'excel', 'api')
    TARGET_CONTRACTS = ('vie', 'v.i.e', 'volontariat international')
    NEGATIVE_KEYWORDS = ('mechanical', 'mécanique', 'maintenance industrielle', 'production operator', 'juriste', 'comptable')
    SENIOR_KEYWORDS = ('senior', 'lead ', 'head of', 'manager', '10 ans', '10+ years', '8 ans')

    @classmethod
    def score(cls, offer: JobOffer) -> dict:
        text = cls._text(offer)
        score = 25
        reasons: list[str] = []
        role_family = 'Autre'

        for family, keywords in cls.ROLE_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in text]
            if hits:
                role_family = family
                score += min(35, 15 + len(hits) * 5)
                reasons.append(f'{family}: {", ".join(hits[:3])}')
                break

        tool_hits = [kw for kw in cls.TOOL_KEYWORDS if kw in text]
        if tool_hits:
            score += min(25, len(tool_hits) * 5)
            reasons.append(f'Compétences cible: {", ".join(tool_hits[:4])}')

        if any(token in text for token in cls.TARGET_CONTRACTS) or offer.source in ('business_france_vie', 'snapshot:business_france_vie'):
            score += 8
            reasons.append('Format VIE / source cible')

        recency = cls.recency_label(offer)
        if recency == 'new':
            score += 15
            reasons.append('Récente')
        elif recency == 'fresh':
            score += 8
            reasons.append('Encore fraîche')
        elif recency == 'stale':
            score -= 8
            reasons.append('Ancienne')

        negative_hits = [kw for kw in cls.NEGATIVE_KEYWORDS if kw in text]
        if negative_hits:
            score -= 35
            reasons.append(f'Signal hors cible: {", ".join(negative_hits[:2])}')

        senior_hits = [kw for kw in cls.SENIOR_KEYWORDS if kw in text]
        if senior_hits:
            score -= 18
            reasons.append('Seniorité probablement trop élevée')

        score = max(0, min(100, score))
        return {
            'score': score,
            'tier': cls.tier(score),
            'role_family': role_family,
            'recency': recency,
            'reasons': reasons[:5] or ['Pas assez de signaux exploitables'],
        }

    @classmethod
    def is_recent(cls, offer: JobOffer, days: int = 7) -> bool:
        date = offer.last_seen_at or offer.first_seen_at or offer.posted_date or offer.created_at
        return bool(date and date >= datetime.utcnow() - timedelta(days=days))

    @classmethod
    def recency_label(cls, offer: JobOffer) -> str:
        date = offer.last_seen_at or offer.first_seen_at or offer.posted_date or offer.created_at
        if not date:
            return 'unknown'
        age_days = (datetime.utcnow() - date).days
        if age_days <= 2:
            return 'new'
        if age_days <= 30:
            return 'fresh'
        return 'stale'

    @staticmethod
    def tier(score: int) -> str:
        if score >= 65:
            return 'priority'
        if score >= 45:
            return 'potential'
        return 'noise'

    @staticmethod
    def _text(offer: JobOffer) -> str:
        parts = [offer.job_title or '', offer.raw_text or '', offer.source or '']
        if offer.required_skills:
            parts.extend(str(skill) for skill in offer.required_skills)
        if offer.company:
            parts.append(offer.company.name or '')
        return ' '.join(parts).lower()
