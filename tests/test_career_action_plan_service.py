from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.db import Base
from app.database.models import Application, JobAnalysis, SkillGapEvent
from app.services.career_action_plan_service import CareerActionPlanService


def make_session():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def test_builds_action_plan_from_latest_analyses_and_gap_events():
    db, engine = make_session()
    try:
        first = Application(telegram_user_id='local', raw_offer='Data analyst role', company='Acme', job_title='Data Analyst')
        second = Application(telegram_user_id='local', raw_offer='BI role', company='Beta', job_title='BI Analyst')
        other = Application(telegram_user_id='other', raw_offer='Hidden role', company='Hidden', job_title='Hidden')
        db.add_all([first, second, other])
        db.flush()
        db.add_all([
            JobAnalysis(application_id=first.id, analysis_json={'match_score': 8, 'role_family': 'Data / BI'}, missing_points=['dbt', 'SQL avancé'], strengths=['Power BI', 'Analyse métier']),
            JobAnalysis(application_id=first.id, analysis_json={'match_score': 9, 'role_family': 'Data / BI'}, missing_points=['dbt'], strengths=['Power BI']),
            JobAnalysis(application_id=second.id, analysis_json={'match_score': 7, 'positioning': {'skill_profile': 'business_data'}}, missing_points=['dbt', 'Airflow'], strengths=['SQL']),
            JobAnalysis(application_id=other.id, analysis_json={'match_score': 10}, missing_points=['Secret'], strengths=['Secret']),
            SkillGapEvent(telegram_user_id='local', application_id=first.id, offer_title='Data Analyst', company='Acme', role_family='Data / BI', positioning='BI', skill_name='dbt', skill_category='tool', required=1, present=0, gap=1, importance_score=8, confidence=9),
            SkillGapEvent(telegram_user_id='local', application_id=second.id, offer_title='BI Analyst', company='Beta', role_family='Data / BI', positioning='BI', skill_name='Airflow', skill_category='tool', required=1, present=0, gap=1, importance_score=6, confidence=8),
        ])
        db.commit()

        result = CareerActionPlanService.build(db, 'local')

        assert result['total_offers_analyzed'] == 2
        assert result['learning_memory']['applications_analyzed'] == 2
        assert result['market_signals']['top_requested_skills'][0]['skill'] == 'dbt'
        assert result['market_signals']['top_strengths'][0]['skill'] == 'Power BI'
        assert result['gap_priorities'][0]['skill'] == 'dbt'
        assert result['gap_priorities'][0]['priority'] == 'high'
        assert 'Projet' in result['action_plan'][0]['action']
        assert result['positioning_insights']['best_role_families'][0]['role_family'] == 'Data / BI'
    finally:
        db.close()
        engine.dispose()


def test_uses_stored_offers_as_market_sample_when_no_llm_analysis_exists():
    from app.database.models import Company, JobOffer, ProfileBlock, CategoryEnum, TruthLevelEnum
    db, engine = make_session()
    try:
        company = Company(name='Market Co')
        db.add(company)
        db.flush()
        db.add_all([
            JobOffer(company_id=company.id, job_title='Data Analyst SQL dbt', job_url='https://example.org/1', source='archive', raw_text='SQL Power BI dbt data modeling'),
            JobOffer(company_id=company.id, job_title='BI Analyst', job_url='https://example.org/2', source='archive', raw_text='Power BI SQL CRM analytics'),
            ProfileBlock(category=CategoryEnum.skill, title='SQL', content='SQL, Power BI, CRM analytics', truth_level=TruthLevelEnum.verified),
        ])
        db.commit()

        result = CareerActionPlanService.build(db, 'local')

        assert result['total_offers_analyzed'] == 2
        assert result['learning_memory']['source'] == 'stored_offers'
        assert {'SQL', 'Power BI'}.issubset({item['skill'] for item in result['market_signals']['top_requested_skills']})
        assert result['gap_priorities'][0]['skill'] == 'dbt'
        assert result['action_plan'][0]['skill'] == 'dbt'
    finally:
        db.close()
        engine.dispose()


def test_recommends_reinforcing_market_strengths_when_no_gap_is_detected():
    from app.database.models import Company, JobOffer, ProfileBlock, CategoryEnum, TruthLevelEnum
    db, engine = make_session()
    try:
        company = Company(name='Market Co')
        db.add(company)
        db.flush()
        db.add_all([
            JobOffer(company_id=company.id, job_title='BI Analyst', job_url='https://example.org/1', source='archive', raw_text='Power BI SQL CRM analytics'),
            ProfileBlock(category=CategoryEnum.skill, title='BI stack', content='Power BI SQL CRM analytics', truth_level=TruthLevelEnum.verified),
        ])
        db.commit()

        result = CareerActionPlanService.build(db, 'local')

        assert result['gap_priorities'] == []
        assert result['action_plan'][0]['priority'] == 'leverage'
        assert result['action_plan'][0]['skill'] in {'Power BI', 'SQL', 'CRM analytics'}
    finally:
        db.close()
        engine.dispose()
