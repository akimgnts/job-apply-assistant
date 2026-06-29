"""Conversation history service - records all user interactions."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import ConversationHistory

logger = logging.getLogger(__name__)


class ConversationHistoryService:
    """Service to record all Telegram conversations for audit/replay."""

    @staticmethod
    def record_message(
        db: Session,
        user_id: str,
        message_type: str,  # 'user_message', 'bot_reply', 'callback', 'error'
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationHistory]:
        """
        Record a conversation message/event.

        Args:
            db: Database session
            user_id: Telegram user ID
            message_type: Type of message (user_message, bot_reply, callback, error)
            content: Message content
            metadata: Additional JSON data (command, button_pressed, etc)
        """
        try:
            history = ConversationHistory(
                user_id=user_id,
                message_type=message_type,
                content=content,
                metadata=metadata or {},
                timestamp=datetime.utcnow(),
            )
            db.add(history)
            db.commit()
            return history
        except Exception as e:
            logger.error(f"Failed to record conversation history: {e}")
            try:
                db.rollback()
            except:
                pass
            return None

    @staticmethod
    def record_user_message(
        db: Session,
        user_id: str,
        text: str,
        command: Optional[str] = None,
    ) -> None:
        """Record user message."""
        metadata = {"command": command} if command else {}
        ConversationHistoryService.record_message(
            db, user_id, "user_message", text, metadata
        )

    @staticmethod
    def record_bot_reply(
        db: Session,
        user_id: str,
        text: str,
        buttons: Optional[list] = None,
    ) -> None:
        """Record bot reply."""
        metadata = {"buttons": buttons} if buttons else {}
        ConversationHistoryService.record_message(
            db, user_id, "bot_reply", text, metadata
        )

    @staticmethod
    def record_callback(
        db: Session,
        user_id: str,
        callback_data: str,
        response: Optional[str] = None,
    ) -> None:
        """Record button callback."""
        metadata = {"callback_data": callback_data, "response": response}
        ConversationHistoryService.record_message(
            db, user_id, "callback", f"Button pressed: {callback_data}", metadata
        )

    @staticmethod
    def record_error(
        db: Session,
        user_id: str,
        error_message: str,
        error_type: str = "unknown",
        context: Optional[Dict] = None,
    ) -> None:
        """Record error during conversation."""
        metadata = {"error_type": error_type, "context": context or {}}
        ConversationHistoryService.record_message(
            db, user_id, "error", error_message, metadata
        )

    @staticmethod
    def get_user_history(
        db: Session,
        user_id: str,
        limit: int = 50,
        message_type: Optional[str] = None,
    ) -> list:
        """Get conversation history for a user."""
        try:
            query = db.query(ConversationHistory).filter(
                ConversationHistory.user_id == user_id
            )
            if message_type:
                query = query.filter(ConversationHistory.message_type == message_type)
            return query.order_by(ConversationHistory.timestamp.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    @staticmethod
    def get_conversation_flow(
        db: Session,
        user_id: str,
        limit: int = 20,
    ) -> str:
        """Get formatted conversation flow for display."""
        history = ConversationHistoryService.get_user_history(db, user_id, limit)
        if not history:
            return "No conversation history found."

        lines = [f"📋 Conversation History for User {user_id}\n"]
        for msg in reversed(history):
            time_str = msg.timestamp.strftime("%H:%M:%S")
            icon = {
                "user_message": "👤",
                "bot_reply": "🤖",
                "callback": "🔘",
                "error": "❌",
            }.get(msg.message_type, "📝")

            lines.append(f"{icon} [{time_str}] {msg.message_type}")
            lines.append(f"   {msg.content[:100]}")

        return "\n".join(lines)
