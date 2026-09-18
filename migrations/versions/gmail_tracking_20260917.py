"""Add isolated Gmail events and sync cursors after the current tracking schema.

The unpublished Gmail 009 migration is intentionally not copied: Radar owns 009.
"""
from alembic import op
import sqlalchemy as sa

revision = 'gmail_tracking_20260917'
down_revision = 'web_outreach_20260917'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('email_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.String(255), nullable=False),
        sa.Column('mailbox', sa.String(255), nullable=False),
        sa.Column('gmail_message_id', sa.String(255), nullable=False),
        sa.Column('thread_id', sa.String(255)),
        sa.Column('sender_email', sa.String(320)), sa.Column('sender_name', sa.String(255)),
        sa.Column('recipients', sa.JSON()), sa.Column('subject', sa.String(500)),
        sa.Column('snippet', sa.Text()), sa.Column('body_text', sa.Text()),
        sa.Column('received_at', sa.DateTime()), sa.Column('labels', sa.JSON()),
        sa.Column('detected_type', sa.String(50)), sa.Column('classification_reason', sa.Text()),
        sa.Column('confirmed_type', sa.String(50)), sa.Column('status', sa.String(30)),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id')),
        sa.Column('link_method', sa.String(30)), sa.Column('created_at', sa.DateTime()), sa.Column('updated_at', sa.DateTime()),
        sa.UniqueConstraint('owner_id','mailbox','gmail_message_id',name='uq_email_owner_mailbox_message'))
    for column in ('owner_id','thread_id','received_at','status','application_id'):
        op.create_index(f'ix_email_events_{column}', 'email_events', [column])
    op.create_table('gmail_sync_states', sa.Column('owner_id',sa.String(255),primary_key=True),
        sa.Column('mailbox',sa.String(255)), sa.Column('query',sa.Text()), sa.Column('next_page_token',sa.Text()),
        sa.Column('last_synced_at',sa.DateTime()), sa.Column('last_error',sa.Text()))


def downgrade():
    op.drop_table('gmail_sync_states')
    op.drop_table('email_events')
