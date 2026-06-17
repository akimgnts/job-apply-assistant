"""Add document format column (html/pdf/txt)

Revision ID: 004
Revises: 003
Create Date: 2026-06-17 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add format column to track document delivery format."""
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('generated_documents')]

    # Add format if missing
    if 'format' not in columns:
        op.add_column(
            'generated_documents',
            sa.Column('format', sa.String(length=10), server_default='html', nullable=False)
        )


def downgrade() -> None:
    """Remove format column."""
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('generated_documents')]

    if 'format' in columns:
        op.drop_column('generated_documents', 'format')
