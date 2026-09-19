"""Fast deterministic scoring for job-offer radar triage."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
from app.database.models import Application, JobOffer


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
        return cls._score_text(
            text=cls._text(offer),
            source=offer.source,
            recency=cls.recency_label(offer),
        )

    @classmethod
    def analyze_application(cls, application: Application) -> dict:
        signal = cls._score_text(
            text=' '.join([application.job_title or '', application.company or '', application.raw_offer or '', application.source_url or '']).lower(),
            source=application.source_url or '',
            recency='unknown',
        )
        tool_hits = cls.keyword_hits(application.raw_offer or '')
        match_score = max(1, min(10, round(signal['score'] / 10)))
        strengths = signal['reasons'][:]
        if tool_hits:
            strengths.append(f"Compétences détectées: {', '.join(tool_hits[:5])}")
        missing_points = []
        if signal['tier'] == 'noise':
            missing_points.append('Signal faible: vérifier que le poste correspond bien au profil cible avant de postuler.')
        elif not tool_hits:
            missing_points.append('Peu de compétences explicites détectées: relire l’offre ou lancer l’analyse IA complète quand elle sera configurée.')
        return {
            'analysis_mode': 'deterministic',
            'company': application.company,
            'job_title': application.job_title,
            'match_score': match_score,
            'missions': cls._extract_short_lines(application.raw_offer, fallback=application.job_title or 'Offre à qualifier'),
            'required_skills': tool_hits,
            'soft_skills': [],
            'ats_keywords': tool_hits,
            'missing_points': missing_points,
            'strengths': strengths[:6] or ['Première qualification disponible sans appel IA.'],
            'profile_blocks_to_use': [],
            'positioning': {
                'positioning': cls.positioning_from_signal(signal),
                'skill_profile': signal['role_family'].lower().replace(' / ', '_').replace(' ', '_'),
            },
            'signal': signal,
        }

    @classmethod
    def _score_text(cls, text: str, source: str | None = None, recency: str = 'unknown') -> dict:
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

        if any(token in text for token in cls.TARGET_CONTRACTS) or source in ('business_france_vie', 'snapshot:business_france_vie'):
            score += 8
            reasons.append('Format VIE / source cible')

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


    @classmethod
    def keyword_hits(cls, text: str) -> list[str]:
        lowered = (text or '').lower()
        return [keyword for keyword in cls.TOOL_KEYWORDS if keyword in lowered]

    @classmethod
    def positioning_from_signal(cls, signal: dict[str, Any]) -> str:
        family = signal.get('role_family') or 'le poste'
        reasons = signal.get('reasons') or []
        if signal.get('tier') == 'priority':
            return f"Candidature prioritaire: positionner Akim sur {family} avec {', '.join(reasons[:2]).lower()}."
        if signal.get('tier') == 'potential':
            return f"Candidature à qualifier: vérifier les attentes clés puis cadrer Akim sur {family}."
        return 'Opportunité à faible signal: ne pas investir de temps sans validation manuelle.'

    @staticmethod
    def _extract_short_lines(text: str | None, fallback: str) -> list[str]:
        chunks = [line.strip(' -•	') for line in (text or '').splitlines() if len(line.strip()) >= 12]
        if not chunks and text:
            chunks = [part.strip() for part in text.split('.') if len(part.strip()) >= 20]
        return (chunks[:4] or [fallback])

    @staticmethod
    def _text(offer: JobOffer) -> str:
        parts = [offer.job_title or '', offer.raw_text or '', offer.source or '']
        if offer.required_skills:
            parts.extend(str(skill) for skill in offer.required_skills)
        if offer.company:
            parts.append(offer.company.name or '')
        return ' '.join(parts).lower()
