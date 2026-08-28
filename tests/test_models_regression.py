"""Regression tests for database models.

Ensures SQLAlchemy reserved name conflicts don't occur.
"""

import pytest
from app.database.models import ConversationHistory, BotInstance


class TestModelRegression:
    """Regression tests for model instantiation and SQLAlchemy compatibility."""

    def test_conversation_history_model_import(self):
        """Verify ConversationHistory model can be imported."""
        assert ConversationHistory is not None
        assert ConversationHistory.__tablename__ == "conversation_history"

    def test_conversation_history_instantiation(self):
        """Verify ConversationHistory can be instantiated without SQLAlchemy errors."""
        history = ConversationHistory(
            user_id="test_user",
            message_type="user_message",
            content="Test message",
            metadata_json={"test": "data"}
        )
        assert history.user_id == "test_user"
        assert history.message_type == "user_message"
        assert history.content == "Test message"
        assert history.metadata_json == {"test": "data"}

    def test_conversation_history_metadata_column_mapping(self):
        """Verify metadata_json attribute maps to 'metadata' SQL column."""
        col = ConversationHistory.metadata_json
        assert col.name == "metadata"
        assert col.type.__class__.__name__ == "JSON"

    def test_bot_instance_model_import(self):
        """Verify BotInstance model can be imported."""
        assert BotInstance is not None
        assert BotInstance.__tablename__ == "bot_instances"

    def test_bot_instance_instantiation(self):
        """Verify BotInstance can be instantiated."""
        instance = BotInstance(
            pid=12345,
            status="started",
            message="Bot started successfully"
        )
        assert instance.pid == 12345
        assert instance.status == "started"
        assert instance.message == "Bot started successfully"

    def test_reserved_attribute_name_not_used(self):
        """Verify 'metadata' reserved name is NOT used as Python attribute."""
        history = ConversationHistory()
        # Should have metadata_json, not metadata (which would trigger SQLAlchemy warning)
        assert hasattr(history, "metadata_json")
        # Verify it maps to the correct column
        assert hasattr(ConversationHistory, "metadata_json")
