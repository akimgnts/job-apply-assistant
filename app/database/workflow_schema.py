"""Additive workflow schema guard for local workspaces without migrations."""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.database.db import Base
from app.database import models  # noqa: F401 - ensure workflow tables are registered


def _type_for(engine, logical: str) -> str:
    if engine.dialect.name == "postgresql":
        return {
            "integer": "INTEGER",
            "datetime": "TIMESTAMP",
            "string": "VARCHAR(255)",
        }[logical]
    return {
        "integer": "INTEGER",
        "datetime": "DATETIME",
        "string": "VARCHAR(255)",
    }[logical]


def _add_column(conn, table: str, column: str, definition: str) -> None:
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def _ensure_application_status_enum(engine) -> None:
    """Add workflow statuses to the PostgreSQL enum used by applications.status."""
    if engine.dialect.name != "postgresql":
        return
    statuses = ["saved", "analyzed", "generated", "applied", "received", "replied", "interview", "rejected", "archived"]
    with engine.begin() as conn:
        enum_exists = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'applicationstatusenum'")).scalar()
        if not enum_exists:
            return
        for status in statuses:
            conn.execute(text(f"ALTER TYPE applicationstatusenum ADD VALUE IF NOT EXISTS '{status}'"))


def ensure_workflow_schema(engine) -> None:
    """Create missing workflow tables and add new columns without touching data."""
    _ensure_application_status_enum(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    Base.metadata.create_all(
        bind=engine,
        tables=[
            models.EmailEvent.__table__,
            models.GmailSyncState.__table__,
            models.ApplicationEvent.__table__,
        ],
    )
    tables = set(inspector.get_table_names()) | {
        "email_events",
        "gmail_sync_states",
        "application_events",
    }
    if "applications" not in tables:
        Base.metadata.create_all(bind=engine, tables=[models.Application.__table__])
        return

    existing = {column["name"] for column in inspect(engine).get_columns("applications")}
    with engine.begin() as conn:
        if "plane_work_item_id" not in existing:
            _add_column(conn, "applications", "plane_work_item_id", _type_for(engine, "string"))
        if "job_offer_id" not in existing:
            _add_column(conn, "applications", "job_offer_id", _type_for(engine, "integer"))
        if "applied_at" not in existing:
            _add_column(conn, "applications", "applied_at", _type_for(engine, "datetime"))
        if "status_updated_at" not in existing:
            _add_column(conn, "applications", "status_updated_at", _type_for(engine, "datetime"))

    email_columns = {column["name"] for column in inspect(engine).get_columns("email_events")}
    with engine.begin() as conn:
        if "match_confidence" not in email_columns:
            _add_column(conn, "email_events", "match_confidence", _type_for(engine, "integer"))
