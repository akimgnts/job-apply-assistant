"""Intelligence Agent - Conversational interface to analyze job offers and skill gaps."""

import json
from sqlalchemy.orm import Session
from app.services.openai_service import call_openai
from app.services.database_intelligence_service import DatabaseIntelligenceService
from app.services.elevia_intelligence_service import EleviaIntelligenceService
from app.database.models import ProfileBlock, CategoryEnum


class IntelligenceAgent:
    """Agent for conversational analysis of job market and skill gaps."""

    def __init__(self):
        self.elevia = EleviaIntelligenceService()

    @staticmethod
    async def analyze_user_question(
        db: Session,
        user_id: str,
        question: str,
        candidate_skills: list = None
    ) -> str:
        """Analyze user question using live market data + local database."""

        # Get candidate skills from profile blocks if not provided
        if not candidate_skills:
            blocks = db.query(ProfileBlock).filter(
                ProfileBlock.category.in_([CategoryEnum.skill, CategoryEnum.tool])
            ).all()
            candidate_skills = [block.title.lower() for block in blocks]

        # Initialize agent to access Elevia service
        agent = IntelligenceAgent()

        # Get live market data from Elevia
        market_data = await agent.elevia.analyze_market_insights()
        opportunities = await agent.elevia.discover_opportunities(db, user_id, candidate_skills, limit=5)

        # Get local application data for comparison
        summary = DatabaseIntelligenceService.get_application_summary(db, user_id)
        companies = DatabaseIntelligenceService.get_offers_by_company(db, user_id)
        best_offers = DatabaseIntelligenceService.get_best_matching_offers(db, user_id)
        gaps = DatabaseIntelligenceService.get_skill_gaps(db, user_id, candidate_skills)

        # Build comprehensive context
        context = f"""Tu es un assistant IA spécialisé dans l'analyse du marché de l'emploi et des compétences.
Tu as accès à:
1. Marché EN DIRECT (Elevia) - les offres actives du marché
2. Historique local - les candidatures de l'utilisateur

MARCHÉ EN DIRECT (Elevia):
- Offres actives totales: {market_data.get('total_offers', 0)}
- Top entreprises: {json.dumps([{'company': c[0], 'count': c[1]} for c in market_data.get('top_companies', [])[:5]], ensure_ascii=False)}
- Top pays: {json.dumps([{'country': c[0], 'count': c[1]} for c in market_data.get('top_countries', [])[:5]], ensure_ascii=False)}
- Types de contrats: {json.dumps(dict(market_data.get('contract_types', [])), ensure_ascii=False)}
- Opportunités pour le candidat: {json.dumps(opportunities[:3], ensure_ascii=False)}

HISTORIQUE LOCAL:
- Total d'offres analysées: {summary.get('total_applications', 0)}
- Match moyen: {summary.get('avg_match_score', 0)}/100
- Top compétences demandées: {', '.join([s['skill'] for s in summary.get('top_skills', [])[:5]])}
- Gaps identifiés: {gaps['gaps_count']} compétences manquantes
- Compétences du candidat: {', '.join(candidate_skills[:10])}

ANALYSE:
- Par entreprise: {json.dumps(companies[:5], ensure_ascii=False)}
- Meilleurs matches: {json.dumps(best_offers[:3], ensure_ascii=False)}

Compétences manquantes (skill gaps):
{json.dumps(gaps['gaps'][:5], ensure_ascii=False)}

Réponds à la question du candidat en utilisant PRIORITAIREMENT les données du marché en direct (Elevia).
Sois concis, utilise des emojis pour structurer, propose des actions si possible."""

        prompt = f"""{context}

Question du candidat: {question}

Réponds en français, de manière naturelle et utile. Référence le marché en direct si pertinent."""

        try:
            response = await call_openai(prompt)
            return response
        except Exception as e:
            return f"Erreur lors de l'analyse: {str(e)}"

    async def get_quick_insight(
        self,
        db: Session,
        user_id: str,
        insight_type: str
    ) -> str:
        """Get quick pre-formatted insights from local DB or live market."""

        # Local insights
        if insight_type == "summary":
            data = DatabaseIntelligenceService.get_application_summary(db, user_id)
            return DatabaseIntelligenceService.format_insight_message("summary", data)

        elif insight_type == "gaps":
            blocks = db.query(ProfileBlock).filter(
                ProfileBlock.category.in_([CategoryEnum.skill, CategoryEnum.tool])
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

        # Live market insights from Elevia
        elif insight_type == "market":
            market = await self.elevia.analyze_market_insights()
            return EleviaIntelligenceService.format_market_message(market)

        elif insight_type == "opportunities":
            blocks = db.query(ProfileBlock).filter(
                ProfileBlock.category.in_([CategoryEnum.skill, CategoryEnum.tool])
            ).all()
            candidate_skills = [block.title.lower() for block in blocks]
            opportunities = await self.elevia.discover_opportunities(db, user_id, candidate_skills, limit=5)
            return EleviaIntelligenceService.format_opportunities_message(opportunities)

        elif insight_type == "elevia_summary":
            summary = await self.elevia.get_intelligence_summary(db, user_id, [])
            return EleviaIntelligenceService.format_market_message(summary.get("market", {}))

        return "Insight non disponible"
