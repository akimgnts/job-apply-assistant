from sqlalchemy import create_engine, select
from app.database.db import Base
from app.database.models import Application, Company, JobOffer, Opportunity, OpportunityLink
from scripts.import_local_workspace import merge_workspace


def test_merge_preserves_existing_application_and_remaps_links():
    source, target = create_engine('sqlite://'), create_engine('sqlite://')
    for engine in (source, target):
        Base.metadata.create_all(engine)
    with source.begin() as conn:
        conn.execute(Application.__table__.insert(), {'id':1, 'telegram_user_id':'local','raw_offer':'local offer','source_url':'https://example.org/new'})
        conn.execute(Opportunity.__table__.insert(), {'id':1,'owner_id':'local','canonical_key':'new'})
        conn.execute(OpportunityLink.__table__.insert(), {'id':1,'opportunity_id':1,'source_type':'application','source_id':1})
    with target.begin() as conn:
        conn.execute(Application.__table__.insert(), {'id':1,'telegram_user_id':'123','raw_offer':'existing offer'})
    result = merge_workspace(source,target,'123')
    assert result['applications'] == 1
    with target.connect() as conn:
        apps = conn.execute(select(Application.__table__).order_by(Application.id)).mappings().all()
        link = conn.execute(select(OpportunityLink.__table__)).mappings().one()
        assert apps[0]['raw_offer'] == 'existing offer'
        assert apps[1]['telegram_user_id'] == '123'
        assert link['source_id'] == apps[1]['id']
    assert all(n == 0 for n in merge_workspace(source,target,'123').values())
