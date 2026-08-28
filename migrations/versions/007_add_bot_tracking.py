"""Add bot instance tracking and conversation history

Revision ID: 007
Revises: 006
Create Date: 2026-06-28

Track bot lifecycle (singleton management) and record all user interactions.
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bot_instances table for singleton management
    op.create_table(
        'bot_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pid', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create conversation_history table for audit trail
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for query performance
    op.create_index('ix_conversation_history_user_id', 'conversation_history', ['user_id'])
    op.create_index('ix_conversation_history_timestamp', 'conversation_history', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_conversation_history_timestamp', table_name='conversation_history')
    op.drop_index('ix_conversation_history_user_id', table_name='conversation_history')
    op.drop_table('conversation_history')
    op.drop_table('bot_instances')
