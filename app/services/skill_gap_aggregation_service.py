import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import SkillGapEvent, ApplicationStatusEnum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SkillGapAggregationService:
    """Aggregate and analyze skill gap events."""

    @staticmethod
    def record_skill_gap(
        db: Session,
        telegram_user_id: str,
        application_id: int,
        offer_title: str,
        company: str,
        role_family: str,
        positioning: str,
        skill_name: str,
        skill_category: str,
        required: bool,
        present: bool,
        importance_score: int = 5,
        confidence: int = 8,
    ) -> SkillGapEvent:
        """Record a single skill gap event."""
        gap = 1 if (required and not present) else 0

        event = SkillGapEvent(
            telegram_user_id=telegram_user_id,
            application_id=application_id,
            offer_title=offer_title,
            company=company,
            role_family=role_family,
            positioning=positioning,
            skill_name=skill_name,
            skill_category=skill_category,
            required=1 if required else 0,
            present=1 if present else 0,
            gap=gap,
            importance_score=importance_score,
            confidence=confidence,
        )
        db.add(event)
        db.commit()
        return event

    @staticmethod
    def get_top_requested_skills(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get most frequently requested skills across all analyzed offers."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            SkillGapEvent.skill_name,
            func.count(SkillGapEvent.id).label("count"),
            func.avg(SkillGapEvent.importance_score).label("avg_importance"),
        ).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.required == 1,
            SkillGapEvent.created_at >= cutoff_date,
        ).group_by(
            SkillGapEvent.skill_name
        ).order_by(
            func.count(SkillGapEvent.id).desc()
        ).limit(limit).all()

        total_offers = db.query(func.count(func.distinct(SkillGapEvent.application_id))).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.created_at >= cutoff_date,
        ).scalar() or 1

        return [
            {
                "skill": skill,
                "frequency": count,
                "percentage": round((count / total_offers) * 100, 1),
                "avg_importance": round(avg_importance or 0, 1),
            }
            for skill, count, avg_importance in results
        ]

    @staticmethod
    def get_most_frequent_gaps(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get most frequently missing skills."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            SkillGapEvent.skill_name,
            func.count(SkillGapEvent.id).label("gap_count"),
            func.avg(SkillGapEvent.importance_score).label("avg_importance"),
        ).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.gap == 1,
            SkillGapEvent.created_at >= cutoff_date,
        ).group_by(
            SkillGapEvent.skill_name
        ).order_by(
            func.count(SkillGapEvent.id).desc()
        ).limit(limit).all()

        total_offers = db.query(func.count(func.distinct(SkillGapEvent.application_id))).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.created_at >= cutoff_date,
        ).scalar() or 1

        return [
            {
                "skill": skill,
                "frequency": gap_count,
                "percentage": round((gap_count / total_offers) * 100, 1),
                "avg_importance": round(avg_importance or 0, 1),
            }
            for skill, gap_count, avg_importance in results
        ]

    @staticmethod
    def get_strongest_skills(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get skills that are present in most offers."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            SkillGapEvent.skill_name,
            func.count(SkillGapEvent.id).label("present_count"),
            func.avg(SkillGapEvent.importance_score).label("avg_importance"),
        ).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.present == 1,
            SkillGapEvent.created_at >= cutoff_date,
        ).group_by(
            SkillGapEvent.skill_name
        ).order_by(
            func.count(SkillGapEvent.id).desc()
        ).limit(limit).all()

        total_offers = db.query(func.count(func.distinct(SkillGapEvent.application_id))).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.created_at >= cutoff_date,
        ).scalar() or 1

        return [
            {
                "skill": skill,
                "frequency": present_count,
                "percentage": round((present_count / total_offers) * 100, 1),
                "avg_importance": round(avg_importance or 0, 1),
            }
            for skill, present_count, avg_importance in results
        ]

    @staticmethod
    def calculate_critical_gaps(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Calculate critical gaps based on:
        - frequency of gap
        - importance score
        - confidence level
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            SkillGapEvent.skill_name,
            func.count(SkillGapEvent.id).label("gap_frequency"),
            func.avg(SkillGapEvent.importance_score).label("avg_importance"),
            func.avg(SkillGapEvent.confidence).label("avg_confidence"),
        ).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.gap == 1,
            SkillGapEvent.created_at >= cutoff_date,
        ).group_by(
            SkillGapEvent.skill_name
        ).all()

        # Calculate gap score for each skill
        scored_gaps = []
        for skill, frequency, avg_importance, avg_confidence in results:
            gap_score = (frequency * (avg_importance or 5) * (avg_confidence or 8)) / 100
            scored_gaps.append({
                "skill": skill,
                "frequency": frequency,
                "importance": round(avg_importance or 0, 1),
                "confidence": round(avg_confidence or 0, 1),
                "critical_gap_score": round(gap_score, 2),
            })

        # Sort by critical gap score
        scored_gaps.sort(key=lambda x: x["critical_gap_score"], reverse=True)
        return scored_gaps[:limit]

    @staticmethod
    def get_role_family_strengths(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
    ) -> Dict[str, Any]:
        """Analyze match scores by role family."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all gap events grouped by role family
        results = db.query(
            SkillGapEvent.role_family,
            func.count(SkillGapEvent.id).label("total_skills"),
            func.sum(SkillGapEvent.gap).label("total_gaps"),
            func.avg(SkillGapEvent.importance_score).label("avg_importance"),
        ).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.created_at >= cutoff_date,
        ).group_by(
            SkillGapEvent.role_family
        ).all()

        role_scores = {}
        for role_family, total_skills, total_gaps, avg_importance in results:
            if not role_family or total_skills == 0:
                continue

            # Match score: (skills_present / total_skills) * 100
            skills_present = total_skills - (total_gaps or 0)
            match_score = (skills_present / total_skills) * 100 if total_skills > 0 else 0

            role_scores[role_family] = {
                "match_score": round(match_score, 1),
                "total_skills": total_skills,
                "skills_present": skills_present,
                "gaps": total_gaps or 0,
                "avg_importance": round(avg_importance or 0, 1),
            }

        return role_scores

    @staticmethod
    def get_career_intelligence_summary(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
    ) -> Dict[str, Any]:
        """Get complete career intelligence summary."""
        total_offers = db.query(func.count(func.distinct(SkillGapEvent.application_id))).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id,
            SkillGapEvent.created_at >= (datetime.utcnow() - timedelta(days=days)),
        ).scalar() or 0

        top_requested = SkillGapAggregationService.get_top_requested_skills(
            db, telegram_user_id, days=days, limit=10
        )
        most_frequent_gaps = SkillGapAggregationService.get_most_frequent_gaps(
            db, telegram_user_id, days=days, limit=10
        )
        strongest_skills = SkillGapAggregationService.get_strongest_skills(
            db, telegram_user_id, days=days, limit=10
        )
        critical_gaps = SkillGapAggregationService.calculate_critical_gaps(
            db, telegram_user_id, days=days, limit=10
        )
        role_strengths = SkillGapAggregationService.get_role_family_strengths(
            db, telegram_user_id, days=days
        )

        return {
            "total_offers_analyzed": total_offers,
            "top_requested_skills": top_requested,
            "strongest_skills": strongest_skills,
            "frequent_gaps": most_frequent_gaps,
            "critical_gaps": critical_gaps,
            "role_family_analysis": role_strengths,
        }
