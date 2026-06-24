"""Database Intelligence Service - Query and analyze job offers and skill gaps."""

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.database.models import Application, JobAnalysis
import json


class DatabaseIntelligenceService:
    """Service to query and analyze application data."""

    @staticmethod
    def get_statistics(db: Session, user_id: str) -> dict:
        """Get basic statistics about user's applications."""
        total = db.query(Application).filter(
            Application.telegram_user_id == user_id
        ).count()

        if total == 0:
            return {
                "total_applications": 0,
                "message": "Aucune candidature pour le moment. Commence à analyser des offres!"
            }

        avg_score = db.query(func.avg(Application.match_score)).filter(
            Application.telegram_user_id == user_id
        ).scalar() or 0

        return {
            "total_applications": total,
            "avg_match_score": round(avg_score, 1),
            "max_score": db.query(func.max(Application.match_score)).filter(
                Application.telegram_user_id == user_id
            ).scalar() or 0,
        }

    @staticmethod
    def get_top_skills_required(db: Session, user_id: str, limit: int = 10) -> list:
        """Get most frequently required skills from analyzed offers."""
        apps = db.query(Application, JobAnalysis).join(
            JobAnalysis, JobAnalysis.application_id == Application.id
        ).filter(Application.telegram_user_id == user_id).all()

        if not apps:
            return []

        skill_frequency = {}
        for app, analysis in apps:
            if analysis.required_skills:
                skills = analysis.required_skills
                if isinstance(skills, str):
                    skills = json.loads(skills)
                for skill in skills:
                    skill_lower = skill.lower() if isinstance(skill, str) else ""
                    skill_frequency[skill_lower] = skill_frequency.get(skill_lower, 0) + 1

        sorted_skills = sorted(skill_frequency.items(), key=lambda x: x[1], reverse=True)
        return [{"skill": s[0], "frequency": s[1]} for s in sorted_skills[:limit]]

    @staticmethod
    def get_application_summary(db: Session, user_id: str) -> dict:
        """Get summary of user's applications."""
        stats = DatabaseIntelligenceService.get_statistics(db, user_id)
        top_skills = DatabaseIntelligenceService.get_top_skills_required(db, user_id)

        return {
            **stats,
            "top_skills": top_skills,
        }

    @staticmethod
    def search_applications(db: Session, user_id: str, query: str) -> list:
        """Search applications by company or job title."""
        results = db.query(Application).filter(
            Application.telegram_user_id == user_id,
            (Application.company.ilike(f"%{query}%")) |
            (Application.job_title.ilike(f"%{query}%"))
        ).all()

        return [
            {
                "id": app.id,
                "company": app.company,
                "job_title": app.job_title,
                "match_score": app.match_score,
                "status": app.status,
            }
            for app in results
        ]

    @staticmethod
    def get_skill_gaps(db: Session, user_id: str, candidate_skills: list = None) -> dict:
        """Analyze skill gaps from applications."""
        apps = db.query(Application, JobAnalysis).join(
            JobAnalysis, JobAnalysis.application_id == Application.id
        ).filter(Application.telegram_user_id == user_id).all()

        if not apps:
            return {"gaps": [], "message": "Pas assez de données pour analyser les gaps"}

        # Get all required skills
        all_required_skills = {}
        for app, analysis in apps:
            if analysis.required_skills:
                skills = analysis.required_skills
                if isinstance(skills, str):
                    skills = json.loads(skills)
                for skill in skills:
                    skill_lower = skill.lower() if isinstance(skill, str) else ""
                    all_required_skills[skill_lower] = all_required_skills.get(skill_lower, 0) + 1

        # If candidate_skills provided, identify gaps
        candidate_skills_lower = [s.lower() for s in (candidate_skills or [])]
        gaps = {}
        for skill, frequency in all_required_skills.items():
            if skill not in candidate_skills_lower:
                gaps[skill] = frequency

        sorted_gaps = sorted(gaps.items(), key=lambda x: x[1], reverse=True)
        return {
            "gaps": [{"skill": g[0], "frequency": g[1]} for g in sorted_gaps[:10]],
            "total_unique_skills_required": len(all_required_skills),
            "gaps_count": len(gaps),
        }

    @staticmethod
    def get_offers_by_company(db: Session, user_id: str) -> list:
        """Get offers grouped by company."""
        results = db.query(
            Application.company,
            func.count(Application.id).label("count"),
            func.avg(Application.match_score).label("avg_score")
        ).filter(
            Application.telegram_user_id == user_id
        ).group_by(Application.company).all()

        return [
            {
                "company": r[0] or "Unknown",
                "offers": r[1],
                "avg_match_score": round(r[2], 1) if r[2] else 0,
            }
            for r in results if r[0]
        ]

    @staticmethod
    def get_best_matching_offers(db: Session, user_id: str, limit: int = 5) -> list:
        """Get best matching offers."""
        results = db.query(Application).filter(
            Application.telegram_user_id == user_id
        ).order_by(Application.match_score.desc()).limit(limit).all()

        return [
            {
                "id": app.id,
                "company": app.company,
                "job_title": app.job_title,
                "match_score": app.match_score,
            }
            for app in results
        ]

    @staticmethod
    def format_insight_message(key: str, data: dict, candidate_skills: list = None) -> str:
        """Format database insights into readable messages."""
        if key == "summary":
            msg = f"""📊 <b>Résumé de tes candidatures</b>

Total: <b>{data['total_applications']}</b> offres analysées
Match moyen: <b>{data['avg_match_score']}/100</b>
Meilleur match: <b>{data['max_score']}/100</b>

<b>Top 5 compétences demandées:</b>
"""
            for i, skill in enumerate(data.get("top_skills", [])[:5], 1):
                msg += f"\n{i}. {skill['skill'].title()} ({skill['frequency']}×)"
            return msg

        elif key == "gaps":
            gaps_data = DatabaseIntelligenceService.get_skill_gaps(None, None, candidate_skills)
            msg = f"""🔍 <b>Tes skill gaps</b>

Compétences uniques demandées: <b>{gaps_data['total_unique_skills_required']}</b>
Gaps identifiés: <b>{gaps_data['gaps_count']}</b>

<b>Top gaps à combler:</b>
"""
            for i, gap in enumerate(gaps_data['gaps'][:5], 1):
                msg += f"\n{i}. {gap['skill'].title()} (dans {gap['frequency']} offres)"
            return msg

        elif key == "companies":
            msg = "<b>📍 Offres par entreprise:</b>\n\n"
            for company in data[:5]:
                msg += f"• {company['company']}: {company['offers']} offres (match: {company['avg_match_score']}/100)\n"
            return msg

        elif key == "best":
            msg = "<b>🏆 Tes meilleurs matches:</b>\n\n"
            for i, offer in enumerate(data[:5], 1):
                msg += f"{i}. {offer['company']} - {offer['job_title']}\n   Match: {offer['match_score']}/100\n\n"
            return msg

        return "Données non disponibles"
