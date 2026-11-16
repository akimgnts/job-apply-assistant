"""Backfill confident role-domain labels for the existing market dataset."""
from alembic import op
import sqlalchemy as sa

from app.services.activity_taxonomy_service import classify_activity_domain


revision = "taxonomy_backfill_20261116"
down_revision = "market_taxonomy_20261116"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    offers = sa.table(
        "job_offers",
        sa.column("id", sa.Integer),
        sa.column("job_title", sa.String),
        sa.column("raw_text", sa.Text),
        sa.column("activity_domain", sa.String),
        sa.column("activity_domain_confidence", sa.String),
    )
    rows = connection.execute(
        sa.select(offers.c.id, offers.c.job_title, offers.c.raw_text)
        .where(offers.c.activity_domain.is_(None))
    ).mappings()
    updates = []
    for row in rows:
        domain, confidence = classify_activity_domain(row["job_title"], row["raw_text"])
        if domain:
            updates.append({"_offer_id": row["id"], "activity_domain": domain,
                            "activity_domain_confidence": confidence})
    if updates:
        connection.execute(
            offers.update().where(offers.c.id == sa.bindparam("_offer_id")), updates
        )


def downgrade() -> None:
    # Keep labels already saved by the live collectors; the migration is additive.
    pass
