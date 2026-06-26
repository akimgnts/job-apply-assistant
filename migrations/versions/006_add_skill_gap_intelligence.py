"""Add skill gap intelligence models

Revision ID: 006
Revises: 005
Create Date: 2024-06-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add relationship to user_sessions
    with op.batch_alter_table('user_sessions', schema=None) as batch_op:
        pass  # No changes needed to user_sessions itself

    # Create skill_gap_events table
    op.create_table(
        'skill_gap_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=255), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('user_session_id', sa.Integer(), nullable=True),
        sa.Column('offer_title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('role_family', sa.String(length=100), nullable=True),
        sa.Column('positioning', sa.String(length=100), nullable=True),
        sa.Column('skill_name', sa.String(length=100), nullable=False),
        sa.Column('skill_category', sa.String(length=50), nullable=True),
        sa.Column('required', sa.Integer(), nullable=True),
        sa.Column('present', sa.Integer(), nullable=True),
        sa.Column('gap', sa.Integer(), nullable=True),
        sa.Column('importance_score', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['user_session_id'], ['user_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create career_intelligence_snapshots table
    op.create_table(
        'career_intelligence_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=255), nullable=False),
        sa.Column('total_offers_analyzed', sa.Integer(), nullable=True),
        sa.Column('top_strengths', sa.JSON(), nullable=True),
        sa.Column('frequent_gaps', sa.JSON(), nullable=True),
        sa.Column('critical_gaps', sa.JSON(), nullable=True),
        sa.Column('recommended_projects', sa.JSON(), nullable=True),
        sa.Column('role_family_strengths', sa.JSON(), nullable=True),
        sa.Column('role_family_weaknesses', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index(
        'ix_skill_gap_events_telegram_user_id',
        'skill_gap_events',
        ['telegram_user_id']
    )
    op.create_index(
        'ix_skill_gap_events_application_id',
        'skill_gap_events',
        ['application_id']
    )
    op.create_index(
        'ix_skill_gap_events_skill_name',
        'skill_gap_events',
        ['skill_name']
    )


def downgrade() -> None:
    op.drop_index('ix_skill_gap_events_skill_name', table_name='skill_gap_events')
    op.drop_index('ix_skill_gap_events_application_id', table_name='skill_gap_events')
    op.drop_index('ix_skill_gap_events_telegram_user_id', table_name='skill_gap_events')
    op.drop_table('career_intelligence_snapshots')
    op.drop_table('skill_gap_events')
