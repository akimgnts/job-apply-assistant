"""Add Job Market Radar MVP tables: companies, job_offers, company_contacts.

Revision ID: 009
Revises: 008
Create Date: 2026-09-02

Phase 1: Core tables for job offer scraping, company aggregation, and lead discovery.

- companies: employer aggregation by name + website
- job_offers: scraped job postings linked to companies
- company_contacts: hiring contacts (manual verification for MVP)

All tables support Phase 1 MVP; design for future extensibility.
No ENUM types for status; use string validation in application layer.
"""
from alembic import op
import sqlalchemy as sa


revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create three new tables for Job Market Radar MVP."""

    # Create 'companies' table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('job_count_this_week', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skill_frequency', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'website', name='uq_company_name_website')
    )

    # Create 'job_offers' table
    op.create_table(
        'job_offers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('job_title', sa.String(255), nullable=False),
        sa.Column('job_url', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('required_skills', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('last_scraped_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.UniqueConstraint('job_url', name='uq_job_url')
    )

    # Create 'company_contacts' table
    op.create_table(
        'company_contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=False),
        sa.Column('role_raw', sa.String(255), nullable=False),
        sa.Column('role_category', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('source_url', sa.String(500), nullable=False),
        sa.Column('data_source', sa.String(50), nullable=False),
        sa.Column('verification_status', sa.String(20), nullable=False, server_default='verified'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], )
    )

    # Create indexes for query performance
    op.create_index('idx_job_offers_company_id', 'job_offers', ['company_id'])
    op.create_index('idx_job_offers_status', 'job_offers', ['status'])
    op.create_index('idx_company_contacts_company_id', 'company_contacts', ['company_id'])


def downgrade() -> None:
    """Drop Job Market Radar MVP tables in reverse order."""

    # Drop indexes
    op.drop_index('idx_company_contacts_company_id', 'company_contacts')
    op.drop_index('idx_job_offers_status', 'job_offers')
    op.drop_index('idx_job_offers_company_id', 'job_offers')

    # Drop tables (order matters: foreign keys first)
    op.drop_table('company_contacts')
    op.drop_table('job_offers')
    op.drop_table('companies')
