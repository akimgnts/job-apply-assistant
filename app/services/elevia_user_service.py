import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.database.models import UserSession

logger = logging.getLogger(__name__)


class EleviaUserService:
    """Manage Elevia profile association for Telegram users."""

    @staticmethod
    def get_elevia_profile_id(db: Session, telegram_user_id: str) -> Optional[str]:
        """Retrieve stored Elevia profile ID for a user."""
        try:
            session = db.query(UserSession).filter(
                UserSession.telegram_user_id == telegram_user_id
            ).first()
            if session and session.session_data:
                return session.session_data.get("elevia_profile_id")
            return None
        except Exception as e:
            logger.error(f"Failed to get Elevia profile ID: {e}")
            return None

    @staticmethod
    def set_elevia_profile_id(db: Session, telegram_user_id: str, profile_id: str) -> bool:
        """Store or update Elevia profile ID for a user."""
        try:
            session = db.query(UserSession).filter(
                UserSession.telegram_user_id == telegram_user_id
            ).first()

            if not session:
                session = UserSession(
                    telegram_user_id=telegram_user_id,
                    session_data={"elevia_profile_id": profile_id},
                )
                db.add(session)
            else:
                if session.session_data is None:
                    session.session_data = {}
                session.session_data["elevia_profile_id"] = profile_id

            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set Elevia profile ID: {e}")
            db.rollback()
            return False

    @staticmethod
    def clear_elevia_profile_id(db: Session, telegram_user_id: str) -> bool:
        """Clear stored Elevia profile ID (e.g., if profile no longer exists)."""
        try:
            session = db.query(UserSession).filter(
                UserSession.telegram_user_id == telegram_user_id
            ).first()

            if session and session.session_data:
                session.session_data.pop("elevia_profile_id", None)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clear Elevia profile ID: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_last_elevia_offer_id(db: Session, telegram_user_id: str) -> Optional[str]:
        """Retrieve last Elevia offer ID accessed by user."""
        try:
            session = db.query(UserSession).filter(
                UserSession.telegram_user_id == telegram_user_id
            ).first()
            if session and session.session_data:
                return session.session_data.get("last_elevia_offer_id")
            return None
        except Exception as e:
            logger.error(f"Failed to get last Elevia offer ID: {e}")
            return None

    @staticmethod
    def set_last_elevia_offer_id(db: Session, telegram_user_id: str, offer_id: str) -> bool:
        """Store last Elevia offer ID accessed by user."""
        try:
            session = db.query(UserSession).filter(
                UserSession.telegram_user_id == telegram_user_id
            ).first()

            if not session:
                session = UserSession(
                    telegram_user_id=telegram_user_id,
                    session_data={"last_elevia_offer_id": offer_id},
                )
                db.add(session)
            else:
                if session.session_data is None:
                    session.session_data = {}
                session.session_data["last_elevia_offer_id"] = offer_id

            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set last Elevia offer ID: {e}")
            db.rollback()
            return False
