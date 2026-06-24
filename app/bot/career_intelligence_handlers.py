import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.services.career_intelligence_service import CareerIntelligenceService
from app.services.skill_gap_aggregation_service import SkillGapAggregationService
from app.services.project_recommendation_engine import ProjectRecommendationEngine

logger = logging.getLogger(__name__)


async def career_intelligence_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display career intelligence summary."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        message = CareerIntelligenceService.get_intelligence_for_telegram(
            db, user_id, section="summary"
        )

        if not message:
            await update.message.reply_text(
                "❌ Pas assez de données. Analysez au moins 10 offres d'emploi."
            )
            return

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying career intelligence: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur lors de la génération de l'intelligence.")

    finally:
        db.close()


async def skill_gaps_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display detailed skill gaps analysis."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        message = CareerIntelligenceService.get_intelligence_for_telegram(
            db, user_id, section="gaps"
        )

        if not message:
            await update.message.reply_text(
                "❌ Pas assez de données. Analysez au moins 10 offres d'emploi."
            )
            return

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying skill gaps: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur lors de l'analyse des gaps.")

    finally:
        db.close()


async def project_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recommended portfolio projects."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        message = CareerIntelligenceService.get_intelligence_for_telegram(
            db, user_id, section="projects"
        )

        if not message or "Recommended" not in message:
            await update.message.reply_text(
                "❌ Pas assez de données. Analysez au moins 10 offres d'emploi."
            )
            return

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying projects: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur lors de la génération des projets.")

    finally:
        db.close()


async def role_family_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display role family analysis."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        message = CareerIntelligenceService.get_intelligence_for_telegram(
            db, user_id, section="roles"
        )

        if not message:
            await update.message.reply_text(
                "❌ Pas assez de données. Analysez au moins 10 offres d'emploi."
            )
            return

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying role analysis: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur lors de l'analyse des rôles.")

    finally:
        db.close()


async def top_requested_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display top requested skills across all analyzed offers."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        skills = SkillGapAggregationService.get_top_requested_skills(
            db, user_id, limit=15
        )

        if not skills:
            await update.message.reply_text("Aucune offre analysée.")
            return

        lines = ["📈 *Top Requested Skills*\n"]
        for i, skill in enumerate(skills, 1):
            lines.append(
                f"{i}. {skill['skill']}\n"
                f"   {skill['percentage']}% des offres | Importance: {skill['avg_importance']}/10"
            )

        message = "\n".join(lines)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying top skills: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur.")

    finally:
        db.close()


async def most_frequent_gaps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display most frequent skill gaps."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        gaps = SkillGapAggregationService.get_most_frequent_gaps(
            db, user_id, limit=15
        )

        if not gaps:
            await update.message.reply_text("Aucune offre analysée.")
            return

        lines = ["⚠️ *Most Frequent Gaps*\n"]
        for i, gap in enumerate(gaps, 1):
            lines.append(
                f"{i}. {gap['skill']}\n"
                f"   {gap['percentage']}% des offres | Importance: {gap['avg_importance']}/10"
            )

        message = "\n".join(lines)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying gaps: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur.")

    finally:
        db.close()


async def strongest_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display candidate's strongest skills."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        skills = SkillGapAggregationService.get_strongest_skills(
            db, user_id, limit=15
        )

        if not skills:
            await update.message.reply_text("Aucune offre analysée.")
            return

        lines = ["💪 *Your Strongest Skills*\n"]
        for i, skill in enumerate(skills, 1):
            lines.append(
                f"{i}. {skill['skill']}\n"
                f"   {skill['percentage']}% des offres | Importance: {skill['avg_importance']}/10"
            )

        message = "\n".join(lines)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error displaying strengths: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur.")

    finally:
        db.close()


async def save_intelligence_snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save current intelligence snapshot to database."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.chat.send_action("typing")

        intelligence = CareerIntelligenceService.generate_intelligence_snapshot(db, user_id)
        snapshot = CareerIntelligenceService.save_snapshot(db, user_id, intelligence)

        await update.message.reply_text(
            f"✅ Intelligence snapshot saved!\n"
            f"📊 {snapshot.total_offers_analyzed} offers analyzed\n"
            f"🏆 {len(snapshot.top_strengths)} top strengths\n"
            f"⚠️ {len(snapshot.critical_gaps)} critical gaps identified"
        )

    except Exception as e:
        logger.error(f"Error saving snapshot: {e}", exc_info=True)
        await update.message.reply_text("❌ Erreur lors de la sauvegarde.")

    finally:
        db.close()
