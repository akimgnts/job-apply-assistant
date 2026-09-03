"""Add job_offer_id FK to job_analyses for Phase 3 JobOffer analysis.

Revision ID: 010
Revises: 009
Create Date: 2026-09-03

Phase 3: Link JobAnalysis to JobOffer (not just Application).

- Add job_offer_id nullable FK to job_offers.id
- Keep application_id (legacy support for Application-based analyses)
- Either job_offer_id or application_id must be set (enforced at app layer)
- skill_evidence_map stored in analysis_json (single source of truth)
- Add index on job_offer_id for query performance
"""
from alembic import op
import sqlalchemy as sa


revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add job_offer_id FK to job_analyses table."""

    # Add job_offer_id FK column
    op.add_column(
        'job_analyses',
        sa.Column('job_offer_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_job_analyses_job_offer_id',
        'job_analyses',
        'job_offers',
        ['job_offer_id'],
        ['id']
    )

    # Add index for query performance
    op.create_index(
        'ix_job_analyses_job_offer_id',
        'job_analyses',
        ['job_offer_id']
    )


def downgrade() -> None:
    """Revert job_offer_id column and related constraints."""

    # Drop index
    op.drop_index('ix_job_analyses_job_offer_id', table_name='job_analyses')

    # Drop foreign key
    op.drop_constraint(
        'fk_job_analyses_job_offer_id',
        'job_analyses',
        type_='foreignkey'
    )

    # Drop column
    op.drop_column('job_analyses', 'job_offer_id')
