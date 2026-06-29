"""Add bot instance and conversation history tracking tables.

Revision ID: 007
Revises: 006
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bot_instances table
    op.create_table(
        'bot_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pid', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create conversation_history table with indexes
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for faster queries
    op.create_index('ix_conversation_history_user_id', 'conversation_history', ['user_id'])
    op.create_index('ix_conversation_history_timestamp', 'conversation_history', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_conversation_history_timestamp', 'conversation_history')
    op.drop_index('ix_conversation_history_user_id', 'conversation_history')
    op.drop_table('conversation_history')
    op.drop_table('bot_instances')
