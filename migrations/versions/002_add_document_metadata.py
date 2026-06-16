"""Add metadata columns to generated_documents table

Revision ID: 002
Revises: 001
Create Date: 2026-06-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add columns to track document metadata and user context."""
    # Add telegram_user_id column (required for quick lookups)
    op.add_column(
        'generated_documents',
        sa.Column('telegram_user_id', sa.String(length=255), nullable=False, server_default='')
    )

    # Add positioning column (captures which positioning was used)
    op.add_column(
        'generated_documents',
        sa.Column('positioning', sa.String(length=255), nullable=True)
    )

    # Add skill_profile column (captures which skill profile was used)
    op.add_column(
        'generated_documents',
        sa.Column('skill_profile', sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    """Remove added columns."""
    op.drop_column('generated_documents', 'skill_profile')
    op.drop_column('generated_documents', 'positioning')
    op.drop_column('generated_documents', 'telegram_user_id')
