import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import CareerIntelligenceSnapshot
from app.services.skill_gap_aggregation_service import SkillGapAggregationService
from app.services.project_recommendation_engine import ProjectRecommendationEngine

logger = logging.getLogger(__name__)


class CareerIntelligenceService:
    """Main service for career intelligence insights."""

    @staticmethod
    def generate_intelligence_snapshot(
        db: Session,
        telegram_user_id: str,
        days: int = 365,
    ) -> Dict[str, Any]:
        """
        Generate a complete career intelligence snapshot.
        """
        # Get aggregated insights
        summary = SkillGapAggregationService.get_career_intelligence_summary(
            db, telegram_user_id, days=days
        )

        # Get project recommendations
        projects = ProjectRecommendationEngine.get_recommendations(db, telegram_user_id, limit=5)

        # Get role family analysis
        role_strengths = summary.get("role_family_analysis", {})

        # Sort role families by match score
        best_roles = sorted(
            role_strengths.items(),
            key=lambda x: x[1].get("match_score", 0),
            reverse=True,
        )

        worst_roles = sorted(
            role_strengths.items(),
            key=lambda x: x[1].get("match_score", 0),
        )

        intelligence = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_offers_analyzed": summary.get("total_offers_analyzed", 0),
            "analysis_days": days,
            "strengths": summary.get("strongest_skills", []),
            "frequent_gaps": summary.get("frequent_gaps", []),
            "critical_gaps": summary.get("critical_gaps", []),
            "recommended_projects": projects,
            "best_matching_role_families": [
                {
                    "role_family": role,
                    **details
                }
                for role, details in best_roles[:5]
            ],
            "weakest_matching_role_families": [
                {
                    "role_family": role,
                    **details
                }
                for role, details in worst_roles[:5]
            ],
        }

        return intelligence

    @staticmethod
    def save_snapshot(
        db: Session,
        telegram_user_id: str,
        intelligence: Dict[str, Any],
    ) -> CareerIntelligenceSnapshot:
        """Save intelligence snapshot to database."""
        snapshot = CareerIntelligenceSnapshot(
            telegram_user_id=telegram_user_id,
            total_offers_analyzed=intelligence.get("total_offers_analyzed", 0),
            top_strengths=[s["skill"] for s in intelligence.get("strengths", [])],
            frequent_gaps=[
                {
                    "skill": g["skill"],
                    "frequency": g["frequency"],
                    "importance": g.get("avg_importance", 0),
                }
                for g in intelligence.get("frequent_gaps", [])
            ],
            critical_gaps=[
                {
                    "skill": g["skill"],
                    "frequency": g["frequency"],
                    "importance": g.get("importance", 0),
                    "critical_gap_score": g.get("critical_gap_score", 0),
                }
                for g in intelligence.get("critical_gaps", [])
            ],
            recommended_projects=[p.get("title") for p in intelligence.get("recommended_projects", [])],
            role_family_strengths={
                r["role_family"]: r.get("match_score", 0)
                for r in intelligence.get("best_matching_role_families", [])
            },
            role_family_weaknesses={
                r["role_family"]: r.get("match_score", 0)
                for r in intelligence.get("weakest_matching_role_families", [])
            },
        )
        db.add(snapshot)
        db.commit()
        return snapshot

    @staticmethod
    def get_latest_snapshot(
        db: Session,
        telegram_user_id: str,
    ) -> Dict[str, Any]:
        """Get the latest saved intelligence snapshot."""
        snapshot = db.query(CareerIntelligenceSnapshot).filter(
            CareerIntelligenceSnapshot.telegram_user_id == telegram_user_id
        ).order_by(CareerIntelligenceSnapshot.created_at.desc()).first()

        if not snapshot:
            return None

        return {
            "generated_at": snapshot.created_at.isoformat(),
            "total_offers_analyzed": snapshot.total_offers_analyzed,
            "strengths": snapshot.top_strengths,
            "frequent_gaps": snapshot.frequent_gaps,
            "critical_gaps": snapshot.critical_gaps,
            "recommended_projects": snapshot.recommended_projects,
            "role_family_strengths": snapshot.role_family_strengths,
            "role_family_weaknesses": snapshot.role_family_weaknesses,
        }

    @staticmethod
    def get_intelligence_for_telegram(
        db: Session,
        telegram_user_id: str,
        section: str = "summary",
    ) -> str:
        """Get career intelligence formatted for Telegram display."""
        intelligence = CareerIntelligenceService.generate_intelligence_snapshot(
            db, telegram_user_id
        )

        if section == "summary":
            return CareerIntelligenceService._format_summary(intelligence)
        elif section == "gaps":
            return CareerIntelligenceService._format_gaps(intelligence)
        elif section == "projects":
            return CareerIntelligenceService._format_projects(intelligence)
        elif section == "roles":
            return CareerIntelligenceService._format_roles(intelligence)
        else:
            return CareerIntelligenceService._format_full(intelligence)

    @staticmethod
    def _format_summary(intelligence: Dict[str, Any]) -> str:
        """Format summary view."""
        lines = [
            "🧠 *Career Intelligence Summary*\n",
            f"📊 Offers Analyzed: {intelligence['total_offers_analyzed']}\n",
        ]

        strengths = intelligence.get("strengths", [])
        if strengths:
            lines.append("💪 *Top Strengths:*")
            for s in strengths[:5]:
                lines.append(f"  • {s['skill']} ({s['percentage']}%)")

        gaps = intelligence.get("frequent_gaps", [])
        if gaps:
            lines.append("\n⚠️ *Frequent Gaps:*")
            for g in gaps[:5]:
                lines.append(f"  • {g['skill']} ({g['percentage']}%)")

        critical = intelligence.get("critical_gaps", [])
        if critical:
            lines.append("\n🔴 *Critical Gaps to Address:*")
            for g in critical[:3]:
                lines.append(f"  • {g['skill']} (score: {g['critical_gap_score']})")

        return "\n".join(lines)

    @staticmethod
    def _format_gaps(intelligence: Dict[str, Any]) -> str:
        """Format gaps view."""
        lines = ["🔍 *Skill Gaps Analysis*\n"]

        frequent = intelligence.get("frequent_gaps", [])
        lines.append("*Most Frequent Gaps:*")
        for i, g in enumerate(frequent[:10], 1):
            lines.append(f"{i}. {g['skill']} - {g['percentage']}% (importance: {g['avg_importance']}/10)")

        critical = intelligence.get("critical_gaps", [])
        lines.append("\n*Critical Gaps (by ROI):*")
        for i, g in enumerate(critical[:10], 1):
            lines.append(f"{i}. {g['skill']} (score: {g['critical_gap_score']})")

        return "\n".join(lines)

    @staticmethod
    def _format_projects(intelligence: Dict[str, Any]) -> str:
        """Format projects view."""
        lines = ["📋 *Recommended Portfolio Projects*\n"]

        projects = intelligence.get("recommended_projects", [])
        for project in projects[:5]:
            lines.append(f"*{project['rank']}. {project['title']}*")
            lines.append(f"  Solves: {', '.join(project['solved_gaps'])}")
            lines.append(f"  Impact: {project['impact']} | Difficulty: {project['difficulty']}")
            lines.append(f"  Hours: {project['estimated_hours']} | ROI Score: {project['roi_score']:.1f}\n")

        return "\n".join(lines)

    @staticmethod
    def _format_roles(intelligence: Dict[str, Any]) -> str:
        """Format role family analysis."""
        lines = ["👔 *Role Family Analysis*\n"]

        best = intelligence.get("best_matching_role_families", [])
        lines.append("*Best Matching Roles:*")
        for r in best:
            lines.append(f"  • {r['role_family']}: {r['match_score']}% match")

        worst = intelligence.get("weakest_matching_role_families", [])
        lines.append("\n*Need Most Development:*")
        for r in worst[:3]:
            lines.append(f"  • {r['role_family']}: {r['match_score']}% match")

        return "\n".join(lines)

    @staticmethod
    def _format_full(intelligence: Dict[str, Any]) -> str:
        """Format full view."""
        parts = [
            CareerIntelligenceService._format_summary(intelligence),
            "\n" + "="*40 + "\n",
            CareerIntelligenceService._format_gaps(intelligence),
            "\n" + "="*40 + "\n",
            CareerIntelligenceService._format_projects(intelligence),
            "\n" + "="*40 + "\n",
            CareerIntelligenceService._format_roles(intelligence),
        ]
        return "\n".join(parts)
