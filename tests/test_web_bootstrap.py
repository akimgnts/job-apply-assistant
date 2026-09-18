"""Local initialization must never touch a remote database or replace live facts."""
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.db import Base
from app.database.models import Company, JobOffer, ProfileBlock


@pytest.fixture
def local_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_snapshot_is_historical_and_repeat_import_preserves_existing(local_db):
    from app.web.bootstrap import import_snapshot
    first = import_snapshot(local_db)
    assert first['total'] == 642
    assert first['imported'] == 642
    assert first['skipped'] == 0
    assert first['snapshot_date'] == '2026-09-05'
    offer = local_db.query(JobOffer).order_by(JobOffer.id).first()
    assert offer.company.name == 'Notion'
    assert offer.source == 'snapshot:ashby'
    assert offer.status == 'archived'
    assert offer.created_at == datetime.fromisoformat('2026-09-05T02:33:26.769887')
    assert offer.last_seen_at.date().isoformat() == '2026-09-05'
    assert offer.last_scraped_at is None
    offer.job_title = 'Live correction'
    offer.source = 'ashby'
    local_db.commit()
    again = import_snapshot(local_db)
    assert again['imported'] == 0
    assert again['skipped'] == 642
    local_db.refresh(offer)
    assert offer.job_title == 'Live correction'
    assert offer.source == 'ashby'


@pytest.mark.parametrize('url', ['postgresql://user:secret@remote.example/db', 'sqlite://', 'sqlite:///:memory:', 'sqlite:///file:remote?uri=true'])
def test_bootstrap_rejects_remote_or_non_file_database(url):
    from app.web.bootstrap import initialize_local
    with pytest.raises(ValueError, match='SQLite'):
        initialize_local(url)


def test_initialize_seeds_v3_only_if_empty(tmp_path):
    from app.web.bootstrap import initialize_local
    url = f'sqlite:///{tmp_path / "workspace.db"}'
    result = initialize_local(url)
    assert result['profile_seeded'] > 0
    engine = create_engine(url)
    with Session(engine) as db:
        block = db.query(ProfileBlock).first()
        assert block.source_ref.startswith('master_v3:')
        block.content = 'My verified correction'
        db.commit()
    assert initialize_local(url)['profile_seeded'] == 0
    with Session(engine) as db:
        assert db.query(ProfileBlock).first().content == 'My verified correction'
        assert db.query(JobOffer).count() == 0
    engine.dispose()
