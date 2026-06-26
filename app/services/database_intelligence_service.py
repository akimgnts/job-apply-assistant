"""Database Intelligence Service - Local application and skills analysis."""

import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import Application, JobAnalysis, ProfileBlock, CategoryEnum

logger = logging.getLogger(__name__)


class DatabaseIntelligenceService:
    """Service for analyzing local application data and skill gaps."""

    @staticmethod
    def get_application_summary(db: Session, user_id: str) -> Dict[str, Any]:
        """Get summary statistics of user's applications."""
        apps = db.query(Application).filter(Application.telegram_user_id == user_id).all()

        if not apps:
            return {
                "total_applications": 0,
                "avg_match_score": 0,
                "max_match_score": 0,
                "top_skills": [],
            }

        match_scores = [app.match_score or 0 for app in apps]
        avg_score = sum(match_scores) / len(match_scores) if match_scores else 0
        max_score = max(match_scores) if match_scores else 0

        # Get top skills from analyses
        top_skills = DatabaseIntelligenceService.get_top_skills_required(db, user_id, limit=5)

        return {
            "total_applications": len(apps),
            "avg_match_score": round(avg_score, 1),
            "max_match_score": max_score,
            "top_skills": top_skills,
        }

    @staticmethod
    def get_top_skills_required(db: Session, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Get most frequently required skills across analyzed offers."""
        analyses = db.query(JobAnalysis).join(
            Application, JobAnalysis.application_id == Application.id
        ).filter(Application.telegram_user_id == user_id).all()

        skill_counts = {}
        for analysis in analyses:
            if analysis.required_skills:
                skills = analysis.required_skills if isinstance(analysis.required_skills, list) else []
                for skill in skills:
                    skill_lower = skill.lower() if isinstance(skill, str) else str(skill).lower()
                    skill_counts[skill_lower] = skill_counts.get(skill_lower, 0) + 1

        # Sort by frequency
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"skill": skill, "frequency": count} for skill, count in sorted_skills]

    @staticmethod
    def get_skill_gaps(db: Session, user_id: str, candidate_skills: List[str]) -> Dict[str, Any]:
        """Identify skills required in offers but missing from candidate profile."""
        candidate_skills_lower = [s.lower() for s in candidate_skills]

        # Get all required skills from user's applications
        all_required = DatabaseIntelligenceService.get_top_skills_required(db, user_id, limit=1000)

        gaps = []
        for skill_data in all_required:
            skill_lower = skill_data["skill"].lower()
            if skill_lower not in candidate_skills_lower:
                gaps.append({
                    "skill": skill_data["skill"],
                    "frequency": skill_data["frequency"],
                })

        return {
            "gaps": gaps,
            "gaps_count": len(gaps),
            "total_unique_skills_required": len(all_required),
        }

    @staticmethod
    def get_offers_by_company(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Group offers by company with statistics."""
        apps = db.query(Application).filter(Application.telegram_user_id == user_id).all()

        companies = {}
        for app in apps:
            company = app.company or "Unknown"
            if company not in companies:
                companies[company] = {
                    "company": company,
                    "offers": 0,
                    "match_scores": [],
                }
            companies[company]["offers"] += 1
            if app.match_score:
                companies[company]["match_scores"].append(app.match_score)

        # Calculate average match score
        result = []
        for company_data in companies.values():
            avg_score = (
                sum(company_data["match_scores"]) / len(company_data["match_scores"])
                if company_data["match_scores"]
                else 0
            )
            result.append({
                "company": company_data["company"],
                "offers": company_data["offers"],
                "avg_match_score": round(avg_score, 1),
            })

        return sorted(result, key=lambda x: x["offers"], reverse=True)

    @staticmethod
    def get_best_matching_offers(db: Session, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get highest matching applications."""
        apps = db.query(Application).filter(
            Application.telegram_user_id == user_id
        ).order_by(Application.match_score.desc()).limit(limit).all()

        return [
            {
                "id": app.id,
                "company": app.company,
                "job_title": app.job_title,
                "match_score": app.match_score or 0,
                "source": getattr(app, 'source_url', ''),
            }
            for app in apps
        ]

    @staticmethod
    def format_insight_message(insight_type: str, data: Dict[str, Any]) -> str:
        """Format insight data as Telegram message."""
        if insight_type == "summary":
            msg = f"""📊 <b>Résumé de tes candidatures</b>

Total d'offres analysées: <b>{data.get('total_applications', 0)}</b>
Match moyen: <b>{data.get('avg_match_score', 0)}/100</b>
Meilleur match: <b>{data.get('max_match_score', 0)}/100</b>

<b>Top compétences demandées:</b>
"""
            for i, skill in enumerate(data.get('top_skills', [])[:5], 1):
                msg += f"\n{i}. {skill['skill'].title()} ({skill['frequency']}×)"

            return msg

        return "Insight non disponible"
