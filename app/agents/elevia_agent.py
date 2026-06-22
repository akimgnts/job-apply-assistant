import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.elevia_gateway import EleviaGateway
from app.services.elevia_user_service import EleviaUserService
from app.services.elevia_offer_loader import EleviaOfferLoader
from app.agents.generation_agent import GenerationAgent
from app.database.db import SessionLocal

logger = logging.getLogger(__name__)


class EleviaAgent:
    """Orchestrate Elevia-powered job application workflow."""

    @staticmethod
    async def health_check() -> bool:
        """Check if Elevia API is available."""
        gateway = EleviaGateway()
        return await gateway.health_check()

    @staticmethod
    async def load_and_prepare_offer(
        db: Session,
        offer_id: str,
        telegram_user_id: str,
        generate_documents: bool = False,
        document_types: Optional[list] = None,
        positioning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Load Elevia offer and optionally generate documents.

        Returns:
        {
            "success": bool,
            "offer_context": EleviaOfferContext dict or None,
            "profile_id": str or None,
            "documents": dict if generate_documents=True,
            "error": str if not success
        }
        """
        logger.info(
            "[ELEVIA_AGENT] Loading offer %s for user %s, generate=%s",
            offer_id,
            telegram_user_id,
            generate_documents,
        )

        try:
            loader = EleviaOfferLoader()

            # Load offer with profile context
            result = await loader.load_offer_for_user(
                db,
                offer_id,
                telegram_user_id,
            )

            if not result or not result.get("success"):
                logger.error("[ELEVIA_AGENT] Failed to load offer")
                return {
                    "success": False,
                    "offer_context": None,
                    "profile_id": None,
                    "error": "Failed to load offer from Elevia",
                }

            offer_context = result["offer_context"]
            profile_id = result["profile_id"]

            # If no positioning provided, use offer title as default
            if not positioning:
                positioning = offer_context.get_job_title()

            logger.info(
                "[ELEVIA_AGENT] Offer loaded: %s @ %s",
                offer_context.get_job_title(),
                offer_context.get_company(),
            )

            # Generate documents if requested
            documents = {}
            if generate_documents and document_types:
                logger.info(
                    "[ELEVIA_AGENT] Generating documents: %s",
                    document_types,
                )

                # Build generation context
                generation_context = await loader.build_generation_context(
                    db,
                    offer_context,
                    positioning,
                )

                # Generate documents (with graceful degradation)
                gen_result = await GenerationAgent.generate_documents(
                    db,
                    application_id=0,  # Temporary ID for Elevia-only flow
                    analysis=generation_context,
                    positioning=positioning,
                    document_types=document_types,
                    telegram_user_id=str(telegram_user_id),
                )

                # Extract documents and errors
                documents = gen_result.get("documents", {})
                errors = gen_result.get("errors", {})

                logger.info(
                    "[ELEVIA_AGENT] Documents generated: status=%s, docs=%s, errors=%s",
                    gen_result.get("status"),
                    list(documents.keys()),
                    [k for k, v in errors.items() if v],
                )

            return {
                "success": True,
                "offer_context": offer_context.to_dict(),
                "profile_id": profile_id,
                "positioning": positioning,
                "documents": documents,
            }

        except Exception as e:
            logger.error(
                "[ELEVIA_AGENT] Error loading/preparing offer: %s",
                str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "offer_context": None,
                "profile_id": None,
                "error": f"Error: {str(e)[:100]}",
            }

    @staticmethod
    async def search_and_rank_offers(
        db: Session,
        telegram_user_id: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search offers and rank by profile match."""
        logger.info(
            "[ELEVIA_AGENT] Searching offers: query=%s, user=%s",
            query,
            telegram_user_id,
        )

        try:
            gateway = EleviaGateway()
            user_id = str(telegram_user_id)

            # Get user's profile ID
            profile_id = EleviaUserService.get_elevia_profile_id(db, user_id)

            if profile_id:
                # Use inbox for ranked results
                logger.info("[ELEVIA_AGENT] Loading ranked offers for profile %s", profile_id)
                offers = await gateway.get_ranked_offers(
                    profile_id=profile_id,
                    limit=limit,
                )
                ranking = "profile-ranked"
            else:
                # Fallback to catalog search
                logger.info("[ELEVIA_AGENT] No profile, using catalog search")
                offers = await gateway.search_offers(
                    query=query,
                    limit=limit,
                )
                ranking = "catalog"

            logger.info("[ELEVIA_AGENT] Found %d offers (%s)", len(offers), ranking)

            return {
                "success": True,
                "offers": offers,
                "ranking_mode": ranking,
                "profile_id": profile_id,
            }

        except Exception as e:
            logger.error("[ELEVIA_AGENT] Error searching offers: %s", str(e), exc_info=True)
            return {
                "success": False,
                "offers": [],
                "ranking_mode": None,
                "profile_id": None,
                "error": f"Error: {str(e)[:100]}",
            }
