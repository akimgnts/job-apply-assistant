"""Intelligence Agent - Conversational interface to analyze job offers and skill gaps."""

import json
from sqlalchemy.orm import Session
from app.services.openai_service import call_openai
from app.services.database_intelligence_service import DatabaseIntelligenceService
from app.database.models import ProfileBlock, BlockCategoryEnum


class IntelligenceAgent:
    """Agent for conversational analysis of job market and skill gaps."""

    @staticmethod
    async def analyze_user_question(
        db: Session,
        user_id: str,
        question: str,
        candidate_skills: list = None
    ) -> str:
        """Analyze user question and return relevant insights from database."""

        # Get candidate skills from profile blocks if not provided
        if not candidate_skills:
            blocks = db.query(ProfileBlock).filter(
                ProfileBlock.category.in_([BlockCategoryEnum.skill, BlockCategoryEnum.tool])
            ).all()
            candidate_skills = [block.title.lower() for block in blocks]

        # Get all relevant data from database
        summary = DatabaseIntelligenceService.get_application_summary(db, user_id)
        companies = DatabaseIntelligenceService.get_offers_by_company(db, user_id)
        best_offers = DatabaseIntelligenceService.get_best_matching_offers(db, user_id)
        gaps = DatabaseIntelligenceService.get_skill_gaps(db, user_id, candidate_skills)

        # Context for the AI
        context = f"""Tu es un assistant IA spécialisé dans l'analyse du marché de l'emploi et des compétences.

Données du candidat:
- Total d'offres analysées: {summary.get('total_applications', 0)}
- Match moyen: {summary.get('avg_match_score', 0)}/100
- Top compétences demandées: {', '.join([s['skill'] for s in summary.get('top_skills', [])[:5]])}
- Gaps identifiés: {gaps['gaps_count']} compétences manquantes
- Compétences du candidat: {', '.join(candidate_skills[:10])}

Offres analysées:
- Par entreprise: {json.dumps(companies[:5], ensure_ascii=False)}
- Meilleurs matches: {json.dumps(best_offers[:3], ensure_ascii=False)}

Compétences manquantes (skill gaps):
{json.dumps(gaps['gaps'][:5], ensure_ascii=False)}

Réponds à la question du candidat de manière constructive et actionnable.
Sois concis, utilise des emojis pour structurer, propose des actions si possible."""

        prompt = f"""{context}

Question du candidat: {question}

Réponds en français, de manière naturelle et utile."""

        try:
            response = await call_openai(prompt)
            return response
        except Exception as e:
            return f"Erreur lors de l'analyse: {str(e)}"

    @staticmethod
    async def get_quick_insight(
        db: Session,
        user_id: str,
        insight_type: str
    ) -> str:
        """Get quick pre-formatted insights."""

        if insight_type == "summary":
            data = DatabaseIntelligenceService.get_application_summary(db, user_id)
            return DatabaseIntelligenceService.format_insight_message("summary", data)

        elif insight_type == "gaps":
            blocks = db.query(ProfileBlock).filter(
                ProfileBlock.category.in_([BlockCategoryEnum.skill, BlockCategoryEnum.tool])
            ).all()
            candidate_skills = [block.title.lower() for block in blocks]
            gaps = DatabaseIntelligenceService.get_skill_gaps(db, user_id, candidate_skills)

            if gaps['gaps_count'] == 0:
                return "✅ Félicitations! Tu as toutes les compétences demandées dans les offres analysées!"

            msg = f"""🔍 <b>Tes skill gaps</b>

Compétences uniques demandées: <b>{gaps['total_unique_skills_required']}</b>
Gaps identifiés: <b>{gaps['gaps_count']}</b>

<b>Top 10 gaps à combler:</b>
"""
            for i, gap in enumerate(gaps['gaps'][:10], 1):
                msg += f"\n{i}. <b>{gap['skill'].title()}</b> (dans {gap['frequency']} offres)"
            return msg

        elif insight_type == "companies":
            companies = DatabaseIntelligenceService.get_offers_by_company(db, user_id)
            if not companies:
                return "Pas d'offres analysées pour le moment."

            msg = "<b>📍 Offres par entreprise:</b>\n\n"
            for i, company in enumerate(companies[:10], 1):
                msg += f"{i}. <b>{company['company']}</b>\n"
                msg += f"   {company['offers']} offre(s) | Match moyen: {company['avg_match_score']}/100\n\n"
            return msg

        elif insight_type == "best":
            offers = DatabaseIntelligenceService.get_best_matching_offers(db, user_id)
            if not offers:
                return "Pas d'offres analysées pour le moment."

            msg = "<b>🏆 Tes meilleurs matches:</b>\n\n"
            for i, offer in enumerate(offers[:10], 1):
                msg += f"{i}. <b>{offer['company']}</b>\n"
                msg += f"   {offer['job_title']}\n"
                msg += f"   Match: {offer['match_score']}/100\n\n"
            return msg

        elif insight_type == "skills":
            skills = DatabaseIntelligenceService.get_top_skills_required(db, user_id, limit=15)
            if not skills:
                return "Pas de données de compétences pour le moment."

            msg = "<b>📊 Top 15 compétences demandées:</b>\n\n"
            for i, skill in enumerate(skills, 1):
                msg += f"{i}. <b>{skill['skill'].title()}</b> ({skill['frequency']}×)\n"
            return msg

        return "Insight non disponible"
