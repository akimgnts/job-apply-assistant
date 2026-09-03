"""Add outreach_drafts table for Phase 6

Revision ID: 011_outreach
Revises: 010
Create Date: 2026-09-03 17:30:00+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '011_outreach'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create outreach_drafts table for Phase 6 message generation."""
    op.create_table(
        'outreach_drafts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('job_offer_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=50), nullable=False, server_default='email'),
        sa.Column('subject_line', sa.String(length=200), nullable=True),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('evidence_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('grounding_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['contact_id'], ['company_contacts.id'], ),
        sa.ForeignKeyConstraint(['job_offer_id'], ['job_offers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_outreach_drafts_company_id',
        'outreach_drafts',
        ['company_id'],
        unique=False
    )
    op.create_index(
        'idx_outreach_drafts_contact_id',
        'outreach_drafts',
        ['contact_id'],
        unique=False
    )
    op.create_index(
        'idx_outreach_drafts_status',
        'outreach_drafts',
        ['status'],
        unique=False
    )


def downgrade() -> None:
    """Drop outreach_drafts table."""
    op.drop_index('idx_outreach_drafts_status', table_name='outreach_drafts')
    op.drop_index('idx_outreach_drafts_contact_id', table_name='outreach_drafts')
    op.drop_index('idx_outreach_drafts_company_id', table_name='outreach_drafts')
    op.drop_table('outreach_drafts')
