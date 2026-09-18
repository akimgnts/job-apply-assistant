"""Add run_id to company_hiring_snapshots for unique constraint

Revision ID: 107133a6b922
Revises: d4423929763f
Create Date: 2026-09-05 15:49:37.070384+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '107133a6b922'
down_revision = 'd4423929763f'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add run_id column (nullable initially to populate existing rows)
    op.add_column('company_hiring_snapshots', sa.Column('run_id', sa.String(36), nullable=True))

    # Populate existing rows with a default run_id
    op.execute("UPDATE company_hiring_snapshots SET run_id = 'legacy-run-001' WHERE run_id IS NULL")

    # Make run_id NOT NULL
    op.alter_column('company_hiring_snapshots', 'run_id', existing_type=sa.String(36), nullable=False)

    # Drop old unique constraint if it exists
    op.drop_constraint('uq_company_hiring_snapshots', table_name='company_hiring_snapshots', type_='unique')

    # Create new unique constraint on (company_id, source, run_id)
    op.create_unique_constraint(
        'uq_company_hiring_snapshots_run',
        'company_hiring_snapshots',
        ['company_id', 'source', 'run_id']
    )

    # Add index on run_id
    op.create_index('ix_company_hiring_snapshots_run_id', 'company_hiring_snapshots', ['run_id'])

def downgrade() -> None:
    op.drop_index('ix_company_hiring_snapshots_run_id', table_name='company_hiring_snapshots')
    op.drop_constraint('uq_company_hiring_snapshots_run', table_name='company_hiring_snapshots', type_='unique')
    op.drop_column('company_hiring_snapshots', 'run_id')
