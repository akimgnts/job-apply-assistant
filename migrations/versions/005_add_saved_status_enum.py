"""Add 'saved' status to ApplicationStatusEnum

Revision ID: 005
Revises: 004
Create Date: 2026-06-17 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 'saved' to ApplicationStatusEnum."""
    # PostgreSQL: ALTER TYPE to add new enum value
    op.execute("ALTER TYPE applicationstatusenum ADD VALUE 'saved' AFTER 'generated'")


def downgrade() -> None:
    """Remove 'saved' from ApplicationStatusEnum."""
    # Note: PostgreSQL doesn't support removing enum values easily
    # This is a limitation of PostgreSQL enums. For downgrade, would need
    # to recreate the type. For now, this is a no-op.
    pass
