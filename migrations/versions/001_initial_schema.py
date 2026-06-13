"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'profile_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('experience', 'skill', 'project', 'education', 'certification', 'tool', 'language', name='categoryenum'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('truth_level', sa.Enum('verified', 'project', 'in_progress', 'learning', name='truthlevelenum'), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('raw_offer', sa.Text(), nullable=False),
        sa.Column('recommended_angle', sa.String(length=255), nullable=True),
        sa.Column('match_score', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('analyzed', 'generated', 'archived', name='applicationstatusenum'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'job_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('analysis_json', sa.JSON(), nullable=False),
        sa.Column('missions', sa.JSON(), nullable=True),
        sa.Column('required_skills', sa.JSON(), nullable=True),
        sa.Column('soft_skills', sa.JSON(), nullable=True),
        sa.Column('ats_keywords', sa.JSON(), nullable=True),
        sa.Column('missing_points', sa.JSON(), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'generated_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.Enum('cv', 'letter', 'mail', name='documenttypeenum'), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=255), nullable=False),
        sa.Column('last_application_id', sa.Integer(), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('session_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['last_application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id')
    )

def downgrade() -> None:
    op.drop_table('user_sessions')
    op.drop_table('generated_documents')
    op.drop_table('job_analyses')
    op.drop_table('applications')
    op.drop_table('profile_blocks')
