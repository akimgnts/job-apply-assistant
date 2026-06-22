import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.elevia_gateway import EleviaGateway, EleviaOfferContext
from app.services.elevia_user_service import EleviaUserService
from app.services.offer_enrichment_service import OfferEnrichmentService

logger = logging.getLogger(__name__)


class EleviaOfferLoader:
    """Unified offer loading with profile enrichment."""

    def __init__(self, gateway: Optional[EleviaGateway] = None):
        self.gateway = gateway or EleviaGateway()

    async def load_offer_for_user(
        self,
        db: Session,
        offer_id: str,
        telegram_user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load Elevia offer with user's profile context."""
        user_id = str(telegram_user_id)
        logger.info("[OFFER_LOADER] Loading offer %s for user %s", offer_id, user_id)

        # Get user's profile ID if available
        profile_id = EleviaUserService.get_elevia_profile_id(db, user_id)
        if profile_id:
            logger.info("[OFFER_LOADER] Using profile %s for user %s", profile_id, user_id)
        else:
            logger.info("[OFFER_LOADER] No profile for user %s, loading offer without matching", user_id)

        # Load offer with profile context
        try:
            offer_context = await self.gateway.get_offer_context(
                offer_id=offer_id,
                profile_id=profile_id,
            )

            if not offer_context:
                logger.error("[OFFER_LOADER] Failed to load offer %s", offer_id)
                return None

            logger.info(
                "[OFFER_LOADER] Loaded offer: %s @ %s",
                offer_context.get_job_title(),
                offer_context.get_company(),
            )

            return {
                "success": True,
                "offer_context": offer_context,
                "profile_id": profile_id,
            }

        except Exception as e:
            logger.error("[OFFER_LOADER] Error loading offer: %s", str(e), exc_info=True)
            return None

    async def build_generation_context(
        self,
        db: Session,
        offer_context: EleviaOfferContext,
        positioning: str,
        existing_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build complete context for CV/letter generation."""
        logger.info(
            "[OFFER_LOADER] Building generation context: %s @ %s, positioning=%s",
            offer_context.get_job_title(),
            offer_context.get_company(),
            positioning,
        )

        # Start with Elevia context
        context = {
            "source": "elevia",
            "source_offer_id": offer_context.source_offer_id,
            "source_type": offer_context.source_type,
            "job_title": offer_context.get_job_title(),
            "company": offer_context.get_company(),
            "location": offer_context.get_location(),
            "positioning": positioning,
            "required_skills": offer_context.get_required_skills(),
            "soft_skills": offer_context.get_soft_skills(),
            "missions": [],  # Would come from offer detail parsing
            "ats_keywords": offer_context.get_ats_keywords(),
        }

        # Merge with existing analysis if provided
        if existing_analysis:
            context = OfferEnrichmentService.enrich_analysis_with_elevia_context(
                existing_analysis,
                offer_context,
            )

        # Add matching context for personalization
        match_score = offer_context.get_match_score()
        if match_score is not None:
            context["elevia_match_score"] = match_score
            logger.info("[OFFER_LOADER] Match score: %.1f/10", match_score)

        matching_expl = offer_context.get_matching_explanation()
        if matching_expl:
            context["elevia_matching_explanation"] = matching_expl

        # Store full context for agents
        context["elevia_offer_context"] = offer_context.to_dict()

        logger.info(
            "[OFFER_LOADER] Generation context built: "
            "skills=%d, soft_skills=%d, ats_keywords=%d",
            len(context.get("required_skills", [])),
            len(context.get("soft_skills", [])),
            len(context.get("ats_keywords", [])),
        )

        return context
