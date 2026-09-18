"""Add OutreachTracking table for response tracking

Revision ID: 286eaab2cdae
Revises: 4d1e52641df7
Create Date: 2026-09-14 21:24:40.082578+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'web_outreach_20260917'
down_revision = '107133a6b922'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'outreach_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('contact_id', sa.Integer(), nullable=True),
        sa.Column('job_offer_id', sa.Integer(), nullable=True),
        sa.Column('outreach_type', sa.String(length=50), nullable=True, server_default='email'),
        sa.Column('outreach_date', sa.DateTime(), nullable=True),
        sa.Column('outreach_message', sa.Text(), nullable=True),
        sa.Column('response_received', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('response_date', sa.DateTime(), nullable=True),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('response_sentiment', sa.String(length=20), nullable=True),
        sa.Column('last_follow_up', sa.DateTime(), nullable=True),
        sa.Column('reminder_interval_days', sa.Integer(), nullable=True, server_default='7'),
        sa.Column('next_follow_up', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['contact_id'], ['company_contacts.id'], ),
        sa.ForeignKeyConstraint(['job_offer_id'], ['job_offers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_outreach_tracking_application_id', 'outreach_tracking', ['application_id'])
    op.create_index('ix_outreach_tracking_contact_id', 'outreach_tracking', ['contact_id'])
    op.create_index('ix_outreach_tracking_job_offer_id', 'outreach_tracking', ['job_offer_id'])
    op.create_index('ix_outreach_tracking_outreach_date', 'outreach_tracking', ['outreach_date'])
    op.create_index('ix_outreach_tracking_response_date', 'outreach_tracking', ['response_date'])
    op.create_index('ix_outreach_tracking_next_follow_up', 'outreach_tracking', ['next_follow_up'])
    op.create_index('ix_outreach_tracking_created_at', 'outreach_tracking', ['created_at'])

def downgrade() -> None:
    op.drop_index('ix_outreach_tracking_created_at', table_name='outreach_tracking')
    op.drop_index('ix_outreach_tracking_next_follow_up', table_name='outreach_tracking')
    op.drop_index('ix_outreach_tracking_response_date', table_name='outreach_tracking')
    op.drop_index('ix_outreach_tracking_outreach_date', table_name='outreach_tracking')
    op.drop_index('ix_outreach_tracking_job_offer_id', table_name='outreach_tracking')
    op.drop_index('ix_outreach_tracking_contact_id', table_name='outreach_tracking')
    op.drop_index('ix_outreach_tracking_application_id', table_name='outreach_tracking')
    op.drop_table('outreach_tracking')
