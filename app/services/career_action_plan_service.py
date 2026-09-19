"""Action-oriented career intelligence built from analyzed offers and gap events."""
from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any
from sqlalchemy.orm import Session
from app.database.models import Application, JobAnalysis, JobOffer, ProfileBlock, SkillGapEvent
from app.services.project_recommendation_engine import ProjectRecommendationEngine


class CareerActionPlanService:
    """Turn market/application data into gap priorities and concrete actions."""

    SKILL_KEYWORDS = {
        'SQL': ('sql', 'postgres', 'mysql'),
        'Power BI': ('power bi', 'powerbi'),
        'Python': ('python',),
        'dbt': ('dbt',),
        'Airflow': ('airflow',),
        'Tableau': ('tableau',),
        'CRM analytics': ('crm', 'salesforce', 'hubspot'),
        'Data modeling': ('data modeling', 'modélisation', 'modelisation'),
        'Excel': ('excel',),
        'Automation': ('automation', 'automatisation', 'workflow'),
        'Machine learning': ('machine learning', 'ml ', ' ia ', ' ai '),
        'API': (' api', 'rest api'),
    }

    @staticmethod
    def build(db: Session, user_id: str, limit: int = 10) -> dict[str, Any]:
        latest = CareerActionPlanService._latest_analyses(db, user_id)
        requested_counter: Counter[str] = Counter()
        gap_counter: Counter[str] = Counter()
        strength_counter: Counter[str] = Counter()
        role_scores: dict[str, list[float]] = defaultdict(list)

        for analysis in latest.values():
            data = analysis.analysis_json or {}
            analysis_gaps = CareerActionPlanService._clean_list(analysis.missing_points)
            analysis_strengths = CareerActionPlanService._clean_list(analysis.strengths)
            requested_counter.update(analysis_gaps + analysis_strengths)
            gap_counter.update(analysis_gaps)
            strength_counter.update(analysis_strengths)
            role = CareerActionPlanService._role_family(data)
            score = data.get('match_score')
            if role and isinstance(score, (int, float)):
                role_scores[role].append(float(score))

        source = 'llm_analyses'
        market_sample_size = len(latest)
        if not latest:
            source = 'stored_offers'
            market_sample_size = CareerActionPlanService._apply_offer_market_sample(db, requested_counter, gap_counter, strength_counter)

        gap_events = db.query(SkillGapEvent).filter(SkillGapEvent.telegram_user_id == user_id).all()
        event_gap_scores = CareerActionPlanService._score_gap_events(gap_events)
        for skill, payload in event_gap_scores.items():
            if skill not in gap_counter:
                gap_counter[skill] = payload['frequency']

        gap_priorities = CareerActionPlanService._gap_priorities(gap_counter, event_gap_scores, market_sample_size, limit)
        top_strength_items = sorted(strength_counter.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]
        top_strengths = [
            {'skill': skill, 'frequency': count, 'percentage': CareerActionPlanService._percentage(count, market_sample_size)}
            for skill, count in top_strength_items
        ]
        action_plan = [CareerActionPlanService._action_for_gap(item, index + 1) for index, item in enumerate(gap_priorities[:5])]
        if not action_plan:
            action_plan = [CareerActionPlanService._action_for_strength(item, index + 1) for index, item in enumerate(top_strengths[:5])]
        projects = ProjectRecommendationEngine.get_recommendations(db, user_id, limit=5)

        return {
            'total_offers_analyzed': market_sample_size,
            'learning_memory': {
                'applications_analyzed': len(latest),
                'source': source,
                'gap_events_recorded': len(gap_events),
                'signals_used': len(requested_counter) + len(gap_counter) + len(strength_counter),
            },
            'market_signals': {
                'top_requested_skills': [
                    {'skill': skill, 'frequency': count, 'percentage': CareerActionPlanService._percentage(count, market_sample_size)}
                    for skill, count in sorted(requested_counter.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]
                ],
                'top_strengths': top_strengths,
            },
            'frequent_gaps': [
                {'skill': item['skill'], 'frequency': item['frequency'], 'importance': item['importance']}
                for item in gap_priorities
            ],
            'top_strengths': [item['skill'] for item in top_strengths],
            'gap_priorities': gap_priorities,
            'action_plan': action_plan,
            'recommended_projects': projects,
            'positioning_insights': {
                'best_role_families': CareerActionPlanService._best_roles(role_scores),
                'message': CareerActionPlanService._positioning_message(top_strengths, gap_priorities),
            },
        }

    @staticmethod
    def _apply_offer_market_sample(db: Session, requested_counter: Counter[str], gap_counter: Counter[str], strength_counter: Counter[str]) -> int:
        offers = db.query(JobOffer).order_by(JobOffer.created_at.desc(), JobOffer.id.desc()).limit(300).all()
        profile_text = ' '.join(
            f"{block.title or ''} {block.content or ''} {' '.join(block.technologies or [])}"
            for block in db.query(ProfileBlock).all()
        ).lower()
        profile_skills = {skill for skill, tokens in CareerActionPlanService.SKILL_KEYWORDS.items() if any(token in profile_text for token in tokens)}
        for offer in offers:
            text = f"{offer.job_title or ''} {offer.raw_text or ''} {' '.join(offer.required_skills or [])}".lower()
            for skill, tokens in CareerActionPlanService.SKILL_KEYWORDS.items():
                if any(token in text for token in tokens):
                    requested_counter[skill] += 1
                    if skill in profile_skills:
                        strength_counter[skill] += 1
                    else:
                        gap_counter[skill] += 1
        return len(offers)

    @staticmethod
    def _latest_analyses(db: Session, user_id: str) -> dict[int, JobAnalysis]:
        rows = (
            db.query(JobAnalysis)
            .join(Application)
            .filter(Application.telegram_user_id == user_id)
            .order_by(JobAnalysis.id.desc())
            .all()
        )
        latest: dict[int, JobAnalysis] = {}
        for row in rows:
            if row.application_id is not None:
                latest.setdefault(row.application_id, row)
        return latest

    @staticmethod
    def _clean_list(values: Any) -> list[str]:
        if not values:
            return []
        return [str(value).strip() for value in values if str(value).strip()]

    @staticmethod
    def _role_family(data: dict[str, Any]) -> str | None:
        role = data.get('role_family') or data.get('job_family')
        if not role and isinstance(data.get('positioning'), dict):
            role = data['positioning'].get('skill_profile')
        return str(role).replace('_', ' ').strip() if role else None

    @staticmethod
    def _score_gap_events(events: list[SkillGapEvent]) -> dict[str, dict[str, float]]:
        grouped: dict[str, dict[str, float]] = defaultdict(lambda: {'frequency': 0, 'importance_total': 0, 'confidence_total': 0})
        for event in events:
            if not event.gap:
                continue
            skill = str(event.skill_name or '').strip()
            if not skill:
                continue
            grouped[skill]['frequency'] += 1
            grouped[skill]['importance_total'] += float(event.importance_score or 5)
            grouped[skill]['confidence_total'] += float(event.confidence or 8)
        result = {}
        for skill, data in grouped.items():
            frequency = data['frequency'] or 1
            result[skill] = {
                'frequency': int(frequency),
                'importance': round(data['importance_total'] / frequency, 1),
                'confidence': round(data['confidence_total'] / frequency, 1),
            }
        return result

    @staticmethod
    def _gap_priorities(gaps: Counter[str], event_scores: dict[str, dict[str, float]], total: int, limit: int) -> list[dict[str, Any]]:
        priorities = []
        for skill, frequency in gaps.items():
            scored = event_scores.get(skill, {})
            importance = float(scored.get('importance', 6 if frequency > 1 else 5))
            confidence = float(scored.get('confidence', 7))
            impact_score = round(float(frequency) * importance * confidence / 10, 1)
            priorities.append({
                'skill': skill,
                'frequency': int(frequency),
                'percentage': CareerActionPlanService._percentage(frequency, total),
                'importance': importance,
                'confidence': confidence,
                'impact_score': impact_score,
                'priority': 'high' if impact_score >= 10 or frequency >= 2 else 'medium',
                'recommendation_type': CareerActionPlanService._recommendation_type(skill),
            })
        priorities.sort(key=lambda item: (item['impact_score'], item['frequency'], item['importance']), reverse=True)
        return priorities[:limit]

    @staticmethod
    def _action_for_strength(strength: dict[str, Any], rank: int) -> dict[str, Any]:
        skill = strength['skill']
        return {
            'rank': rank,
            'skill': skill,
            'priority': 'leverage',
            'action': f"Renforcer la preuve autour de {skill} : sélectionner les meilleurs exemples du Master CV, les rendre visibles dans les CV ciblés et préparer une formulation entretien.",
            'estimated_effort': '2-4h',
            'why_now': f"Compétence déjà prouvée et détectée dans {strength['frequency']} offre(s) du marché analysé.",
        }

    @staticmethod
    def _recommendation_type(skill: str) -> str:
        s = skill.lower()
        if any(token in s for token in ('dbt', 'sql', 'airflow', 'python', 'power bi', 'tableau')):
            return 'portfolio_project'
        if any(token in s for token in ('anglais', 'communication', 'stakeholder', 'management')):
            return 'positioning_or_practice'
        return 'targeted_learning'

    @staticmethod
    def _action_for_gap(gap: dict[str, Any], rank: int) -> dict[str, Any]:
        skill = gap['skill']
        if gap['recommendation_type'] == 'portfolio_project':
            action = f"Projet court à construire autour de {skill}, avec une preuve visible dans le portfolio et réutilisable dans les CV."
            effort = '10-25h'
        elif gap['recommendation_type'] == 'positioning_or_practice':
            action = f"Travailler le discours et les exemples autour de {skill}, puis l'intégrer dans les réponses d’entretien."
            effort = '3-6h'
        else:
            action = f"Apprentissage ciblé sur {skill}, puis ajout d’une preuve concrète dans le Master CV si le niveau devient défendable."
            effort = '5-15h'
        return {
            'rank': rank,
            'skill': skill,
            'priority': gap['priority'],
            'action': action,
            'estimated_effort': effort,
            'why_now': f"Signal présent dans {gap['frequency']} offre(s) analysée(s), impact {gap['impact_score']}.",
        }

    @staticmethod
    def _best_roles(role_scores: dict[str, list[float]]) -> list[dict[str, Any]]:
        rows = [
            {'role_family': role, 'average_match_score': round(sum(scores) / len(scores), 1), 'sample_size': len(scores)}
            for role, scores in role_scores.items() if scores
        ]
        rows.sort(key=lambda row: (row['average_match_score'], row['sample_size']), reverse=True)
        return rows[:5]

    @staticmethod
    def _positioning_message(strengths: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> str:
        top_strength = strengths[0]['skill'] if strengths else 'tes preuves existantes'
        top_gap = gaps[0]['skill'] if gaps else 'aucun gap critique'
        return f"Positionnement actuel : capitaliser sur {top_strength}, puis traiter en priorité {top_gap} si ce signal continue à revenir dans les offres qui matchent."

    @staticmethod
    def _percentage(count: int, total: int) -> float:
        return round((count / total) * 100, 1) if total else 0.0
