"""Retain source metadata and separate employer sector from role domain."""
from alembic import op
import sqlalchemy as sa


revision = "market_taxonomy_20261116"
down_revision = "profile_truth_20260920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_offers", sa.Column("source_payload", sa.JSON(), nullable=True))
    op.add_column("job_offers", sa.Column("activity_sector", sa.String(length=255), nullable=True))
    op.add_column("job_offers", sa.Column("activity_sector_source", sa.String(length=50), nullable=True))
    op.add_column("job_offers", sa.Column("activity_domain", sa.String(length=100), nullable=True))
    op.add_column("job_offers", sa.Column("activity_domain_confidence", sa.String(length=16), nullable=True))
    op.create_index("idx_job_offers_activity_sector", "job_offers", ["activity_sector"])
    op.create_index("idx_job_offers_activity_domain", "job_offers", ["activity_domain"])


def downgrade() -> None:
    op.drop_index("idx_job_offers_activity_domain", table_name="job_offers")
    op.drop_index("idx_job_offers_activity_sector", table_name="job_offers")
    op.drop_column("job_offers", "activity_domain_confidence")
    op.drop_column("job_offers", "activity_domain")
    op.drop_column("job_offers", "activity_sector_source")
    op.drop_column("job_offers", "activity_sector")
    op.drop_column("job_offers", "source_payload")

