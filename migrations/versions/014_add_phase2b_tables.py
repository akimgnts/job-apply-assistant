"""Phase 2B: Add career site crawler tables.

Revision ID: 014_phase2b
Revises: 013_add_outreach_drafts_table
Create Date: 2026-09-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "014_phase2b"
down_revision = "011_outreach"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add career_site_url to companies
    op.add_column(
        "companies",
        sa.Column("career_site_url", sa.String(500), nullable=True),
    )

    # Create crawl_runs table
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(50), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("pages_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("job_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_extracted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_existing", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_closed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("urls_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_runs_created_at", "crawl_runs", ["created_at"])

    # Create career_crawl_urls table
    op.create_table(
        "career_crawl_urls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("discovered_url", sa.String(2000), nullable=False),
        sa.Column("normalized_url", sa.String(2000), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("page_title", sa.String(500), nullable=True),
        sa.Column("is_job_candidate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detection_signals", sa.JSON(), nullable=True),
        sa.Column("detection_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DISCOVERED"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("crawl_run_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_career_crawl_urls_company_id", "career_crawl_urls", ["company_id"])
    op.create_index("ix_career_crawl_urls_url_hash", "career_crawl_urls", ["url_hash"])
    op.create_index("ix_career_crawl_urls_created_at", "career_crawl_urls", ["created_at"])
    op.create_unique_constraint(
        "uq_company_normalized_url",
        "career_crawl_urls",
        ["company_id", "normalized_url"],
    )


def downgrade() -> None:
    # Drop career_crawl_urls table
    op.drop_constraint("uq_company_normalized_url", "career_crawl_urls", type_="unique")
    op.drop_index("ix_career_crawl_urls_created_at", "career_crawl_urls")
    op.drop_index("ix_career_crawl_urls_url_hash", "career_crawl_urls")
    op.drop_index("ix_career_crawl_urls_company_id", "career_crawl_urls")
    op.drop_table("career_crawl_urls")

    # Drop crawl_runs table
    op.drop_index("ix_crawl_runs_created_at", "crawl_runs")
    op.drop_table("crawl_runs")

    # Remove career_site_url from companies
    op.drop_column("companies", "career_site_url")
