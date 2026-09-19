"""Add canonical opportunities and timeline links."""
from alembic import op
import sqlalchemy as sa

revision = 'opportunities_20260919'
down_revision = 'gmail_tracking_20260917'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('opportunities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255)),
        sa.Column('job_title', sa.String(255)),
        sa.Column('canonical_key', sa.String(500), nullable=False),
        sa.Column('status', sa.String(50)),
        sa.Column('priority', sa.Integer()),
        sa.Column('source_primary', sa.String(50)),
        sa.Column('created_from', sa.String(50)),
        sa.Column('last_activity_at', sa.DateTime()),
        sa.Column('next_action', sa.String(255)),
        sa.Column('next_action_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.UniqueConstraint('owner_id', 'canonical_key', name='uq_opportunity_owner_key'))
    for column in ('owner_id', 'company', 'job_title', 'status', 'last_activity_at', 'next_action_at', 'created_at'):
        op.create_index(f'ix_opportunities_{column}', 'opportunities', [column])

    op.create_table('opportunity_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Integer()),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('source_type', 'source_id', name='uq_opportunity_source_link'))
    for column in ('opportunity_id', 'source_type', 'source_id'):
        op.create_index(f'ix_opportunity_links_{column}', 'opportunity_links', [column])

    op.create_table('opportunity_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('summary', sa.String(500)),
        sa.Column('occurred_at', sa.DateTime()),
        sa.Column('confidence', sa.Integer()),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('opportunity_id', 'event_type', 'source_type', 'source_id', name='uq_opportunity_event_source'))
    for column in ('opportunity_id', 'event_type', 'occurred_at'):
        op.create_index(f'ix_opportunity_events_{column}', 'opportunity_events', [column])


def downgrade():
    op.drop_table('opportunity_events')
    op.drop_table('opportunity_links')
    op.drop_table('opportunities')
