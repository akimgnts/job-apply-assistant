"""Fast deterministic scoring for job-offer radar triage."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import re
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


    PARIS_IDF_LOCATION_KEYWORDS = (
        'paris', 'ile-de-france', 'île-de-france', 'idf', 'la defense', 'la défense',
        '75', '77', '78', '91', '92', '93', '94', '95',
        'hauts-de-seine', 'seine-saint-denis', 'val-de-marne', "val-d'oise",
        'yvelines', 'essonne', 'seine-et-marne', 'boulogne', 'neuilly',
    )

    @classmethod
    def location_text(cls, offer: JobOffer) -> str:
        for line in (offer.raw_text or '').splitlines():
            if re.match(r'\s*(lieu|location|localisation)\s*:', line, re.I):
                return line.split(':', 1)[1].strip()
        return ''

    @classmethod
    def is_action_geo_match(cls, offer: JobOffer, geo: str | None = None) -> bool:
        if geo != 'paris_idf' or offer.source != 'apec':
            return True
        location = cls.location_text(offer)
        if not location:
            return False
        normalized = location.lower().replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('î', 'i')
        return any(keyword in normalized for keyword in cls.PARIS_IDF_LOCATION_KEYWORDS)

    @classmethod
    def score(cls, offer: JobOffer) -> dict:
        return cls._score_text(
            text=cls._text(offer),
            source=offer.source,
            recency=cls.recency_label(offer),
            title=offer.job_title or '',
            description=offer.raw_text or '',
        )

    @classmethod
    def analyze_application(cls, application: Application) -> dict:
        signal = cls._score_text(
            text=' '.join([application.job_title or '', application.company or '', application.raw_offer or '', application.source_url or '']).lower(),
            source=application.source_url or '',
            recency='unknown',
            title=application.job_title or '',
            description=application.raw_offer or '',
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

    ROLE_TITLES = {
        'Data / BI': ('data analyst', 'business analyst', 'bi analyst', 'bi consultant', 'consultant bi', 'analyste données', 'analyste data', 'analytics', 'crm'),
        'Automation / AI': ('automation', 'automatisation', 'data scientist', 'intelligence artificielle'),
        'Product / Ops': ('product owner', 'product analyst', 'sales ops', 'revenue ops', 'business operations'),
    }

    @staticmethod
    def contains(text: str, keyword: str) -> bool:
        return bool(re.search(r'(?<!\w)' + re.escape(keyword.strip()) + r'(?!\w)', text, re.I))

    @classmethod
    def _score_text(cls, text: str, source: str | None = None, recency: str = 'unknown', title: str = '', description: str = '') -> dict:
        # Relevance and freshness are independent. No date or source-only match bonus.
        score = 0
        reasons: list[str] = []
        role_family = 'Autre'
        for family, keywords in cls.ROLE_TITLES.items():
            hits = [kw for kw in keywords if cls.contains(title, kw)]
            if hits:
                role_family = family
                score = 48 if family == 'Data / BI' else 36
                reasons.append(f'{family} : intitulé {", ".join(hits[:2])}')
                break
        tool_hits = cls.keyword_hits(text)
        weights = {'sql': 10, 'power bi': 12, 'python': 8, 'crm': 9, 'dashboard': 7, 'automation': 6, 'analytics': 6, 'excel': 4, 'api': 5}
        score += min(42, sum(weights[k] for k in tool_hits))
        if tool_hits:
            reasons.append(f'Compétences cible : {", ".join(tool_hits[:5])}')
        if role_family == 'Autre' and len(tool_hits) >= 2:
            role_family = 'Compétences transversales'
        if cls.contains(title, 'junior') or cls.contains(title, 'débutant'):
            score += 6
            reasons.append('Intitulé ouvert à un profil junior')
        negative_hits = [kw for kw in cls.NEGATIVE_KEYWORDS if cls.contains(text, kw)]
        if negative_hits:
            score -= 35
            reasons.append(f'Signal hors cible : {", ".join(negative_hits[:2])}')
        if any(cls.contains(title, kw) for kw in cls.SENIOR_KEYWORDS if kw != 'manager') or re.search(r'\b(?:[8-9]|1[0-9])\+?\s*(?:ans|years)\b', text):
            score -= 22
            reasons.append('Seniorité probablement trop élevée')
        # Metadata-only archive rows cannot support a full matching assessment.
        content = re.sub(r'(?im)^(?:company|location|id):.*$', '', description).strip()
        confidence = 'medium' if len(content) >= 120 else 'low'
        if confidence == 'low':
            reasons.append('Description incomplète : pertinence à confirmer')
        if recency == 'new':
            reasons.append('Récente : publiée ou repérée depuis moins de 48 h')
        score = max(0, min(100, score))
        return {'score': score, 'tier': cls.tier(score), 'role_family': role_family,
                'recency': recency, 'confidence': confidence, 'reasons': reasons,
                'method': 'rules', 'skills': tool_hits}

    @staticmethod
    def reference_date(offer: JobOffer) -> datetime | None:
        value = offer.posted_date
        if value and value.tzinfo:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @classmethod
    def is_recent(cls, offer: JobOffer, days: float = 7) -> bool:
        date = cls.reference_date(offer)
        return bool(date and timedelta(0) <= datetime.utcnow() - date <= timedelta(days=days))

    @classmethod
    def recency_label(cls, offer: JobOffer) -> str:
        date = cls.reference_date(offer)
        if not date or date > datetime.utcnow():
            return 'unknown'
        age = datetime.utcnow() - date
        if age <= timedelta(hours=48):
            return 'new'
        if age <= timedelta(days=30):
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
        return [keyword for keyword in cls.TOOL_KEYWORDS if cls.contains(lowered, keyword)]

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
        return ' '.join(parts).lower()
