from datetime import datetime, timedelta
from types import SimpleNamespace
from app.services.application_tracking_agent import ApplicationTrackingAgent as Agent
from app.services.offer_signal_service import OfferSignalService


def event(i, subject, body='', sent=False, **kwargs):
    values = dict(id=i, subject=subject, body_text=body, snippet=body, sender_email='recruiter@acme.com', labels=['SENT'] if sent else [], thread_id='thread', application_id=None, status='pending', confirmed_type=None, received_at=datetime(2026, 9, 22, 10, i))
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_sent_mention_is_not_an_application():
    assert Agent.classify(event(1, 'À propos de Cidel', 'On a parlé du poste chez Cidel hier.', sent=True))['label'] == 'noise'


def test_short_reply_joins_outbound_thread():
    rows = Agent.build_opportunities([event(1, 'Candidature — Data Analyst | Acme', sent=True), event(2, 'Re: Candidature — Data Analyst | Acme', 'Merci, je transmets à mon équipe.')])
    assert len(rows) == 1
    assert rows[0]['email_count'] == 2
    assert rows[0]['sent_count'] == 1
    assert rows[0]['received_count'] == 1


def test_latest_rejection_supersedes_interview():
    rows = Agent.build_opportunities([event(1, 'Entretien de recrutement'), event(2, 'Votre candidature', 'Nous ne donnerons pas suite à votre candidature.')])
    assert rows[0]['status'] == 'rejected'


def test_ignored_messages_do_not_reappear():
    assert Agent.build_opportunities([event(1, 'Candidature — Data Analyst | Acme', sent=True, status='archived')]) == []


def test_missing_publication_date_is_not_recent():
    offer = SimpleNamespace(posted_date=None, first_seen_at=datetime.utcnow(), created_at=datetime.utcnow())
    assert not OfferSignalService.is_recent(offer, 2)


def test_recent_discovery_does_not_refresh_old_offer():
    offer = SimpleNamespace(posted_date=datetime.utcnow()-timedelta(days=3), first_seen_at=datetime.utcnow(), created_at=datetime.utcnow())
    assert not OfferSignalService.is_recent(offer, 2)


def test_partial_application_link_groups_entire_thread():
    rows = Agent.build_opportunities([event(1, 'Candidature — Data Analyst | Acme', sent=True, application_id=42), event(2, 'Re: Candidature — Data Analyst | Acme', 'Merci pour votre candidature.')])
    assert len(rows) == 1
    assert rows[0]['application_id'] == 42
    assert rows[0]['email_count'] == 2


def test_sentence_is_not_a_job_title():
    assert Agent._extract_job_title('AI déjà travaillé chez Cidel') == ''
    assert Agent._extract_job_title('BI / Data qui peut être utile chez Activision') == ''


def test_recipient_company_beats_previous_employer_in_body():
    item = event(1, 'Candidature — Data Analyst', 'Mon expérience chez Sidel me permet de répondre à votre offre.', sent=True, recipients=['rh@nexton-group.com'])
    assert Agent.classify(item)['company'] == 'Nexton-group'


def test_candidate_name_is_not_company():
    item = event(1, 'Candidature VIE — Ingénieur Data | Akim Guentas', sent=True, recipients=['rh@hello-pomelo.com'])
    info = Agent.classify(item)
    assert info['company'] == 'Hello-pomelo'
    assert 'Ingénieur Data' in info['job_title']
