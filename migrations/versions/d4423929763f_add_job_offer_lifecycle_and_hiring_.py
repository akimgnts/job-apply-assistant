"""Add job offer lifecycle and hiring snapshots

Revision ID: d4423929763f
Revises: 014_phase2b
Create Date: 2026-09-05 02:57:24.414847+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd4423929763f'
down_revision = '014_phase2b'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add columns to job_offers for lifecycle tracking
    op.add_column('job_offers', sa.Column('first_seen_at', sa.DateTime(), nullable=True))
    op.add_column('job_offers', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    op.add_column('job_offers', sa.Column('closed_at', sa.DateTime(), nullable=True))
    op.add_column('job_offers', sa.Column('consecutive_misses', sa.Integer(), server_default='0', nullable=False))

    # Set first_seen_at and last_seen_at to created_at for existing offers
    op.execute('UPDATE job_offers SET first_seen_at = created_at, last_seen_at = created_at WHERE first_seen_at IS NULL')

    # Make first_seen_at and last_seen_at NOT NULL after populating
    op.alter_column('job_offers', 'first_seen_at', existing_type=sa.DateTime(), nullable=False)
    op.alter_column('job_offers', 'last_seen_at', existing_type=sa.DateTime(), nullable=False)

    # Create company_hiring_snapshots table
    op.create_table(
        'company_hiring_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.Column('active_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('new_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('closed_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('data_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('ai_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('automation_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('digital_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'source', 'captured_at', name='uq_company_hiring_snapshots')
    )
    op.create_index('ix_company_hiring_snapshots_company_id', 'company_hiring_snapshots', ['company_id'])
    op.create_index('ix_company_hiring_snapshots_source', 'company_hiring_snapshots', ['source'])
    op.create_index('ix_company_hiring_snapshots_captured_at', 'company_hiring_snapshots', ['captured_at'])

def downgrade() -> None:
    op.drop_index('ix_company_hiring_snapshots_captured_at', table_name='company_hiring_snapshots')
    op.drop_index('ix_company_hiring_snapshots_source', table_name='company_hiring_snapshots')
    op.drop_index('ix_company_hiring_snapshots_company_id', table_name='company_hiring_snapshots')
    op.drop_table('company_hiring_snapshots')

    op.drop_column('job_offers', 'consecutive_misses')
    op.drop_column('job_offers', 'closed_at')
    op.drop_column('job_offers', 'last_seen_at')
    op.drop_column('job_offers', 'first_seen_at')
