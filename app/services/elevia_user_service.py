import logging
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime
from app.database.db import Base
from datetime import datetime

logger = logging.getLogger(__name__)


class EleviaUserProfile(Base):
    """Store user's Elevia profile ID mapping."""

    __tablename__ = "elevia_user_profiles"

    telegram_user_id = Column(String(255), primary_key=True)
    elevia_profile_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EleviaUserService:
    """Manage user's Elevia profile lifecycle."""

    @staticmethod
    def set_elevia_profile_id(
        db: Session,
        telegram_user_id: str,
        elevia_profile_id: str,
    ) -> None:
        """Store or update user's Elevia profile ID (upsert, race-safe)."""
        user_id = str(telegram_user_id)

        # Use merge for atomic upsert (race-safe for concurrent uploads)
        profile = EleviaUserProfile(
            telegram_user_id=user_id,
            elevia_profile_id=elevia_profile_id,
        )
        profile = db.merge(profile)
        db.commit()

        logger.info(
            "[ELEVIA_USER] Set profile for user %s: %s (merge/upsert)",
            user_id,
            elevia_profile_id,
        )

    @staticmethod
    def get_elevia_profile_id(db: Session, telegram_user_id: str) -> str:
        """Get user's Elevia profile ID."""
        user_id = str(telegram_user_id)

        profile = (
            db.query(EleviaUserProfile)
            .filter_by(telegram_user_id=user_id)
            .first()
        )

        if profile:
            logger.info(
                "[ELEVIA_USER] Found profile for user %s: %s",
                user_id,
                profile.elevia_profile_id,
            )
            return profile.elevia_profile_id

        logger.warning("[ELEVIA_USER] No profile found for user %s", user_id)
        return None

    @staticmethod
    def clear_elevia_profile_id(db: Session, telegram_user_id: str) -> None:
        """Clear user's Elevia profile ID (e.g., if 404 returned)."""
        user_id = str(telegram_user_id)

        db.query(EleviaUserProfile).filter_by(telegram_user_id=user_id).delete()
        db.commit()

        logger.info("[ELEVIA_USER] Cleared profile for user %s", user_id)

    @staticmethod
    def has_elevia_profile(db: Session, telegram_user_id: str) -> bool:
        """Check if user has Elevia profile."""
        return (
            db.query(EleviaUserProfile)
            .filter_by(telegram_user_id=str(telegram_user_id))
            .first()
            is not None
        )
