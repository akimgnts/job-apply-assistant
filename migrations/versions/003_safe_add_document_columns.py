"""Safely add missing document metadata columns (idempotent)

Revision ID: 003
Revises: 002
Create Date: 2026-06-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns. Skip if already exist."""
    # Get current table columns
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('generated_documents')]

    # Add telegram_user_id if missing
    if 'telegram_user_id' not in columns:
        op.add_column(
            'generated_documents',
            sa.Column('telegram_user_id', sa.String(length=255), server_default='', nullable=False)
        )

    # Add positioning if missing
    if 'positioning' not in columns:
        op.add_column(
            'generated_documents',
            sa.Column('positioning', sa.String(length=255), nullable=True)
        )

    # Add skill_profile if missing
    if 'skill_profile' not in columns:
        op.add_column(
            'generated_documents',
            sa.Column('skill_profile', sa.String(length=255), nullable=True)
        )


def downgrade() -> None:
    """Remove added columns (reverse operation)."""
    # Only try to drop if they exist
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('generated_documents')]

    if 'skill_profile' in columns:
        op.drop_column('generated_documents', 'skill_profile')
    if 'positioning' in columns:
        op.drop_column('generated_documents', 'positioning')
    if 'telegram_user_id' in columns:
        op.drop_column('generated_documents', 'telegram_user_id')
