import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.services.skill_gap_capture_service import SkillGapCaptureService
from app.database.models import Application

logger = logging.getLogger(__name__)


class SkillGapIntegrationService:
    """Integration hook for skill gap capture into existing pipeline."""

    @staticmethod
    def capture_gaps_from_application(
        db: Session,
        telegram_user_id: str,
        application: Application,
        analysis: Dict[str, Any],
        positioning: str,
        role_family: str = None,
    ) -> bool:
        """
        Capture skill gaps from an analyzed application.
        This should be called after AnalysisAgent.analyze() and PositioningAgent.choose_angle().
        """
        try:
            if not application or not analysis:
                return False

            # Get role family from positioning if not provided
            if not role_family:
                role_family = positioning or "Unknown"

            # Capture all skill gaps
            event_count = SkillGapCaptureService.capture_gaps_from_analysis(
                db=db,
                telegram_user_id=telegram_user_id,
                application_id=application.id,
                offer_title=application.job_title or "Unknown",
                company=application.company or "Unknown",
                role_family=role_family,
                positioning=positioning,
                analysis=analysis,
            )

            if event_count > 0:
                logger.info(
                    f"Captured {event_count} skill gap events for "
                    f"application {application.id} (user {telegram_user_id})"
                )
                return True
            else:
                logger.warning(f"No skill gaps captured for application {application.id}")
                return False

        except Exception as e:
            logger.error(
                f"Error capturing skill gaps for application {application.id}: {e}",
                exc_info=True
            )
            # Don't raise - this is optional enrichment, don't break main flow
            return False

    @staticmethod
    def get_capture_status(db: Session, telegram_user_id: str) -> Dict[str, Any]:
        """Get status of skill gap capture for a user."""
        from app.database.models import SkillGapEvent

        total_events = db.query(SkillGapEvent).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id
        ).count()

        total_offers = db.query(SkillGapEvent.application_id).filter(
            SkillGapEvent.telegram_user_id == telegram_user_id
        ).distinct().count()

        return {
            "total_events": total_events,
            "total_offers": total_offers,
            "avg_events_per_offer": total_events / total_offers if total_offers > 0 else 0,
            "ready_for_intelligence": total_offers >= 10,
        }
