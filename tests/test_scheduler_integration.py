"""Integration tests for ATS scheduler safety (real PostgreSQL fixture, mocked network)."""

import json
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest

from app.scheduler.ats_scheduler import run_collection, acquisition_lock
from app.database.models import JobOffer, Company


@pytest.fixture
def mock_registry_file(tmp_path):
    registry = {"companies": [{
        "company_name": "TestCorp",
        "ats_type": "lever",
        "company_slug": "testcorp",
        "enabled": True,
    }]}
    path = tmp_path / "ats_registry.json"
    path.write_text(json.dumps(registry))
    return path


def test_scheduler_lock_mechanism(tmp_path):
    import app.scheduler.ats_scheduler as scheduler
    original = scheduler.LOCK_FILE
    scheduler.LOCK_FILE = tmp_path / "test.lock"
    try:
        with acquisition_lock(timeout_secs=1):
            assert scheduler.LOCK_FILE.exists()
        assert not scheduler.LOCK_FILE.exists()
    finally:
        scheduler.LOCK_FILE = original


def test_waiting_process_never_deletes_foreign_lock(tmp_path):
    """Regression: a waiter timing out must not unlink another process' lock."""
    import app.scheduler.ats_scheduler as scheduler
    original = scheduler.LOCK_FILE
    scheduler.LOCK_FILE = tmp_path / "test.lock"
    scheduler.LOCK_FILE.write_text("99999\n")
    try:
        with pytest.raises(RuntimeError, match="Lock timeout"):
            with acquisition_lock(timeout_secs=0):
                pass
        assert scheduler.LOCK_FILE.exists()
        assert scheduler.LOCK_FILE.read_text() == "99999\n"
    finally:
        scheduler.LOCK_FILE.unlink(missing_ok=True)
        scheduler.LOCK_FILE = original


def test_scheduler_empty_success_is_valid(test_db, tmp_path, mock_registry_file):
    """Zero new offers is a successful complete collection, not an error."""
    import app.scheduler.ats_scheduler as scheduler
    original_registry = scheduler.REGISTRY_PATH
    try:
        scheduler.REGISTRY_PATH = mock_registry_file
        mock_adapter = AsyncMock()
        mock_adapter.discover_jobs = AsyncMock(return_value=[])
        mock_adapter.close = AsyncMock()
        with patch('app.scheduler.ats_scheduler.LeverAdapter', return_value=mock_adapter), \
             patch('app.scheduler.ats_scheduler.SessionLocal', return_value=test_db), \
             patch('app.scheduler.ats_scheduler.Path') as mock_path:
            mock_path.side_effect = lambda p: Path(str(p).replace("exports", str(tmp_path / "exports")))
            result = run_collection()
        assert result["results"]["TestCorp"]["status"] == "success"
        assert result["total_after"] == result["total_before"]
    finally:
        scheduler.REGISTRY_PATH = original_registry


def test_incomplete_source_does_not_close_jobs(test_db, tmp_path, mock_registry_file):
    """Extraction failure makes the source incomplete; lifecycle misses stay unchanged."""
    import app.scheduler.ats_scheduler as scheduler
    company = Company(name="TestCorp")
    test_db.add(company)
    test_db.flush()
    old = JobOffer(
        company_id=company.id,
        job_title="Existing",
        job_url="https://example.test/existing",
        source="lever",
        raw_text="",
        status="active",
        consecutive_misses=0,
    )
    test_db.add(old)
    test_db.commit()

    original_registry = scheduler.REGISTRY_PATH
    try:
        scheduler.REGISTRY_PATH = mock_registry_file
        with patch('app.scheduler.ats_scheduler.ingest_ats', new=AsyncMock(return_value=([object()], [], False))), \
             patch('app.scheduler.ats_scheduler.SessionLocal', return_value=test_db), \
             patch('app.scheduler.ats_scheduler.Path') as mock_path:
            mock_path.side_effect = lambda p: Path(str(p).replace("exports", str(tmp_path / "exports")))
            run_collection()
        test_db.refresh(old)
        assert old.consecutive_misses == 0
        assert old.status == "active"
    finally:
        scheduler.REGISTRY_PATH = original_registry


def test_source_error_rolls_back_and_skips_closures(test_db, tmp_path, mock_registry_file):
    import app.scheduler.ats_scheduler as scheduler
    company = Company(name="TestCorp")
    test_db.add(company)
    test_db.flush()
    old = JobOffer(
        company_id=company.id,
        job_title="Existing",
        job_url="https://example.test/existing",
        source="lever",
        raw_text="",
        status="active",
        consecutive_misses=0,
    )
    test_db.add(old)
    test_db.commit()

    original_registry = scheduler.REGISTRY_PATH
    try:
        scheduler.REGISTRY_PATH = mock_registry_file
        with patch('app.scheduler.ats_scheduler.ingest_ats', new=AsyncMock(side_effect=RuntimeError("source down"))), \
             patch('app.scheduler.ats_scheduler.SessionLocal', return_value=test_db), \
             patch('app.scheduler.ats_scheduler.Path') as mock_path:
            mock_path.side_effect = lambda p: Path(str(p).replace("exports", str(tmp_path / "exports")))
            result = run_collection()
        test_db.refresh(old)
        assert result["results"]["TestCorp"]["status"] == "error"
        assert old.consecutive_misses == 0
        assert old.status == "active"
    finally:
        scheduler.REGISTRY_PATH = original_registry
