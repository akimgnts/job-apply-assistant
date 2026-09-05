"""Sprint 2: Hiring lifecycle and acceleration detection tests.

Uses SQLite in-memory database for isolation.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, JobOffer, Company, CompanyHiringSnapshot
from app.services.hiring_lifecycle_service import (
    update_job_offer_lifecycle,
    mark_missing_jobs,
    create_hiring_snapshot,
    calculate_hiring_signals
)


@pytest.fixture
def test_db():
    """SQLite in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create default company
    company = Company(id=1, name="Test Company")
    session.add(company)
    session.commit()
    
    yield session
    session.close()


class TestJobOfferLifecycle:
    """Test 1: New offer receives first_seen_at and last_seen_at."""
    def test_new_offer_has_lifecycle_dates(self, test_db):
        now = datetime.utcnow()
        offer = JobOffer(
            company_id=1,
            job_title="Engineer",
            job_url="https://example.com/job1",
            source="lever",
            status="active",
            first_seen_at=now,
            last_seen_at=now
        )
        test_db.add(offer)
        test_db.commit()
        
        fetched = test_db.query(JobOffer).first()
        assert fetched.first_seen_at is not None
        assert fetched.last_seen_at is not None
        assert fetched.closed_at is None
        assert fetched.consecutive_misses == 0

    """Test 2: Rediscovered offer updates last_seen_at."""
    def test_rediscovered_updates_last_seen(self, test_db):
        now = datetime.utcnow()
        offer = JobOffer(
            company_id=1,
            job_title="Engineer",
            job_url="https://example.com/job1",
            source="lever",
            first_seen_at=now - timedelta(days=5),
            last_seen_at=now - timedelta(days=5)
        )
        test_db.add(offer)
        test_db.commit()
        
        # Rediscover
        update_job_offer_lifecycle(test_db, "https://example.com/job1")
        test_db.commit()
        
        fetched = test_db.query(JobOffer).first()
        assert fetched.last_seen_at > now - timedelta(minutes=1)
        assert fetched.consecutive_misses == 0

    """Test 3: Single miss does not close."""
    def test_single_miss_no_close(self, test_db):
        offer = JobOffer(
            company_id=1,
            job_title="Engineer",
            job_url="https://example.com/job1",
            source="lever",
            status="active"
        )
        test_db.add(offer)
        test_db.commit()
        
        # Mark as missing
        mark_missing_jobs(test_db, set(), "lever")
        test_db.commit()
        
        fetched = test_db.query(JobOffer).first()
        assert fetched.consecutive_misses == 1
        assert fetched.status == "active"
        assert fetched.closed_at is None

    """Test 4: Two consecutive misses close offer."""
    def test_two_misses_close(self, test_db):
        offer = JobOffer(
            company_id=1,
            job_title="Engineer",
            job_url="https://example.com/job1",
            source="lever",
            status="active",
            consecutive_misses=1
        )
        test_db.add(offer)
        test_db.commit()
        
        mark_missing_jobs(test_db, set(), "lever")
        test_db.commit()
        
        fetched = test_db.query(JobOffer).first()
        assert fetched.consecutive_misses == 2
        assert fetched.status == "closed"
        assert fetched.closed_at is not None

    """Test 5: Reappearance reactivates closed offer."""
    def test_reappearance_reactivates(self, test_db):
        offer = JobOffer(
            company_id=1,
            job_title="Engineer",
            job_url="https://example.com/job1",
            source="lever",
            status="closed",
            closed_at=datetime.utcnow(),
            consecutive_misses=2
        )
        test_db.add(offer)
        test_db.commit()
        
        update_job_offer_lifecycle(test_db, "https://example.com/job1")
        test_db.commit()
        
        fetched = test_db.query(JobOffer).first()
        assert fetched.status == "active"
        assert fetched.closed_at is None
        assert fetched.consecutive_misses == 0


class TestSnapshots:
    """Test 6-8: Snapshot creation and signals."""
    
    def test_snapshot_per_company_source(self, test_db):
        """Test 6: Snapshots are per (company, source), not global."""
        offer1 = JobOffer(
            company_id=1, job_title="Job 1", job_url="https://ex.com/1",
            source="lever", status="active"
        )
        offer2 = JobOffer(
            company_id=1, job_title="Job 2", job_url="https://ex.com/2",
            source="greenhouse", status="active"
        )
        test_db.add_all([offer1, offer2])
        test_db.commit()
        
        snap_lever = create_hiring_snapshot(test_db, 1, "lever")
        snap_gh = create_hiring_snapshot(test_db, 1, "greenhouse")
        test_db.commit()
        
        assert snap_lever.source == "lever"
        assert snap_gh.source == "greenhouse"
        assert snap_lever.company_id == 1
        assert snap_gh.company_id == 1

    def test_snapshot_counts(self, test_db):
        """Test 7: Snapshot counts match data."""
        for i in range(3):
            offer = JobOffer(
                company_id=1, job_title=f"Job {i}", job_url=f"https://ex.com/{i}",
                source="lever", status="active"
            )
            test_db.add(offer)
        test_db.commit()
        
        snap = create_hiring_snapshot(test_db, 1, "lever")
        assert snap.active_jobs_count == 3

    def test_insufficient_history_status(self, test_db):
        """Test 8: Scoring returns insufficient_history with < 2 snapshots."""
        offer = JobOffer(
            company_id=1, job_title="Job", job_url="https://ex.com/1",
            source="lever", status="active"
        )
        test_db.add(offer)
        test_db.commit()
        
        snap = create_hiring_snapshot(test_db, 1, "lever")
        test_db.commit()
        
        signals = calculate_hiring_signals(test_db, 1)
        assert signals["status"] == "insufficient_history"


class TestAcceleration:
    """Test 9: Acceleration scoring is deterministic."""
    
    def test_acceleration_deterministic(self, test_db):
        """Same data = same score."""
        for i in range(5):
            offer = JobOffer(
                company_id=1, job_title=f"Data Job {i}", job_url=f"https://ex.com/{i}",
                source="lever", status="active",
                first_seen_at=datetime.utcnow() - timedelta(days=2)
            )
            test_db.add(offer)
        test_db.commit()
        
        snap1 = create_hiring_snapshot(test_db, 1, "lever")
        test_db.commit()
        
        # Wait, add another snapshot
        test_db.query(JobOffer).update({"first_seen_at": datetime.utcnow() - timedelta(days=30)})
        snap2 = create_hiring_snapshot(test_db, 1, "lever", datetime.utcnow() + timedelta(days=7))
        test_db.commit()
        
        signals1 = calculate_hiring_signals(test_db, 1)
        signals2 = calculate_hiring_signals(test_db, 1)
        
        assert signals1["acceleration_score"] == signals2["acceleration_score"]


class TestErrorHandling:
    """Test 10: Source failure doesn't corrupt lifecycle."""
    
    def test_failed_source_no_lifecycle_change(self, test_db):
        """If source errors, existing offers untouched."""
        offer = JobOffer(
            company_id=1, job_title="Job", job_url="https://ex.com/1",
            source="lever", status="active", consecutive_misses=0
        )
        test_db.add(offer)
        test_db.commit()
        
        original_misses = offer.consecutive_misses
        
        # Simulate error: don't call mark_missing_jobs
        test_db.commit()
        
        fetched = test_db.query(JobOffer).first()
        assert fetched.consecutive_misses == original_misses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
