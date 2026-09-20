from datetime import datetime, timedelta
from app.database.models import Company, JobOffer
from app.services.offer_signal_service import OfferSignalService


def make_offer(title, raw='', first_seen_at=None, status='active', source='business_france_vie'):
    company = Company(name='ACME')
    return JobOffer(
        company=company,
        company_id=1,
        job_title=title,
        job_url='https://example.org/job',
        source=source,
        raw_text=raw,
        status=status,
        first_seen_at=first_seen_at or datetime.utcnow(),
        last_seen_at=first_seen_at or datetime.utcnow(),
    )


def test_scores_data_bi_offer_with_recent_boost_and_reasons():
    offer = make_offer('VIE Data Analyst', 'SQL Power BI CRM automation', datetime.utcnow() - timedelta(days=1))

    result = OfferSignalService.score(offer)

    assert result['score'] >= 80
    assert result['tier'] == 'priority'
    assert result['role_family'] == 'Data / BI'
    assert result['recency'] == 'new'
    assert any('Data / BI' in reason for reason in result['reasons'])
    assert any('Récente' in reason for reason in result['reasons'])


def test_penalizes_irrelevant_senior_or_non_target_offer():
    offer = make_offer('Senior Mechanical Engineer', 'maintenance industrielle 10 ans management mécanique', datetime.utcnow() - timedelta(days=60))

    result = OfferSignalService.score(offer)

    assert result['score'] < 45
    assert result['tier'] == 'noise'
    assert result['recency'] == 'stale'
    assert any('hors cible' in reason.lower() or 'senior' in reason.lower() for reason in result['reasons'])


def test_recent_filter_detects_last_seen_or_first_seen():
    assert OfferSignalService.is_recent(make_offer('BI Analyst', first_seen_at=datetime.utcnow() - timedelta(days=3)), days=7)
    assert not OfferSignalService.is_recent(make_offer('BI Analyst', first_seen_at=datetime.utcnow() - timedelta(days=30)), days=7)


def test_incidental_substrings_do_not_match_ai_or_api():
    signal = OfferSignalService.score(make_offer('Commercial spécialiste', 'Capital social et filiale internationale'))
    assert signal['role_family'] == 'Autre'
    assert signal['tier'] == 'noise'


def test_role_fit_distinguishes_target_analyst_from_generic_tool_mention():
    analyst = OfferSignalService.score(make_offer('Data Analyst', 'SQL Power BI Python'))
    developer = OfferSignalService.score(make_offer('Software Developer', 'Python C++'))
    assert analyst['score'] > developer['score'] + 20


def test_recency_uses_publication_not_latest_scrape_and_precise_48_hours():
    offer = make_offer('Data Analyst')
    offer.posted_date = datetime.utcnow() - timedelta(days=40)
    assert OfferSignalService.recency_label(offer) == 'stale'
    assert not OfferSignalService.is_recent(offer, 2)
    offer.posted_date = datetime.utcnow() - timedelta(hours=49)
    assert OfferSignalService.recency_label(offer) == 'fresh'
    offer.posted_date = None
    offer.first_seen_at = datetime.utcnow() - timedelta(days=40)
    assert OfferSignalService.recency_label(offer) == 'stale'


def test_content_confidence_and_fit_do_not_depend_on_recency():
    sparse = make_offer('Data Analyst', 'Company: Acme\nLocation: Paris\nID: 12')
    score = OfferSignalService.score(sparse)
    assert score['confidence'] == 'low'
    sparse.first_seen_at = datetime.utcnow() - timedelta(days=60)
    assert OfferSignalService.score(sparse)['score'] == score['score']
