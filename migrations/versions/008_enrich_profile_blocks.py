"""Enrich ProfileBlock with structured metadata for claim validation.

Revision ID: 008
Revises: 007
Create Date: 2026-06-29

Add new fields for:
- Proficiency level (skills mastery: 0-3)
- Status (project state: completed/deployed/exploratory/etc)
- Metrics (structured measurements)
- Technologies (tools used)
- Job families (relevant roles)
- Company context
- Dates (start/end)
- Forbidden claims (validation guards)
- Source reference (traceability)

All new fields are nullable for backward compatibility with existing blocks.
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums for new fields
    proficiency_enum = sa.Enum('learning', 'beginner', 'intermediate', 'expert', name='proficiencylevel')
    status_enum = sa.Enum('completed', 'deployed', 'in_progress', 'exploratory', 'not_deployed', name='blockstatus')

    proficiency_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns to profile_blocks
    op.add_column('profile_blocks',
        sa.Column('proficiency_level', proficiency_enum, nullable=True)
    )
    op.add_column('profile_blocks',
        sa.Column('status', status_enum, nullable=True)
    )
    op.add_column('profile_blocks',
        sa.Column('metrics', sa.JSON(), nullable=False, server_default='{}')
    )
    op.add_column('profile_blocks',
        sa.Column('technologies', sa.JSON(), nullable=False, server_default='[]')
    )
    op.add_column('profile_blocks',
        sa.Column('job_families', sa.JSON(), nullable=False, server_default='[]')
    )
    op.add_column('profile_blocks',
        sa.Column('company', sa.String(255), nullable=True)
    )
    op.add_column('profile_blocks',
        sa.Column('start_date', sa.String(50), nullable=True)
    )
    op.add_column('profile_blocks',
        sa.Column('end_date', sa.String(50), nullable=True)
    )
    op.add_column('profile_blocks',
        sa.Column('forbidden_claims', sa.JSON(), nullable=False, server_default='[]')
    )
    op.add_column('profile_blocks',
        sa.Column('source_ref', sa.String(255), nullable=True)
    )

    # Update truth_level enum to new values (verified, declared, learning)
    # Note: We'll keep the old values and add new ones for compatibility
    # The application will handle the mapping


def downgrade() -> None:
    op.drop_column('profile_blocks', 'source_ref')
    op.drop_column('profile_blocks', 'forbidden_claims')
    op.drop_column('profile_blocks', 'end_date')
    op.drop_column('profile_blocks', 'start_date')
    op.drop_column('profile_blocks', 'company')
    op.drop_column('profile_blocks', 'job_families')
    op.drop_column('profile_blocks', 'technologies')
    op.drop_column('profile_blocks', 'metrics')
    op.drop_column('profile_blocks', 'status')
    op.drop_column('profile_blocks', 'proficiency_level')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS blockstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS proficiencylevel CASCADE')
