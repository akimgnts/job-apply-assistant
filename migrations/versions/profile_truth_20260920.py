"""Bring the PostgreSQL truth enum in line with the existing profile model."""
from alembic import op

revision = 'profile_truth_20260920'
down_revision = 'opportunities_20260919'
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        # PostgreSQL requires new enum values to be committed before their use.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE truthlevelenum ADD VALUE IF NOT EXISTS 'declared'")
        op.execute("UPDATE profile_blocks SET truth_level = 'declared' WHERE truth_level::text IN ('project', 'in_progress')")


def downgrade():
    # Removing an enum value would invalidate preserved candidate records.
    pass
