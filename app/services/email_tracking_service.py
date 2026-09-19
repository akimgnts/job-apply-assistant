"""Explainable suggestions and conservative tracking: only reviewed events change status."""
import re
import unicodedata
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database.models import Application, EmailEvent, OutreachTracking

EVENT_TYPES = (
    'unknown', 'application_sent', 'acknowledgement', 'application_ack',
    'cold_email', 'recruiter_reply', 'interview_request', 'interview_or_test',
    'rejection', 'bounce', 'newsletter', 'job_board_alert', 'noise'
)
REPLY_TYPES = ('recruiter_reply', 'interview_request', 'interview_or_test', 'rejection')


def normalize(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def classify_email(email: dict) -> dict:
    """Propose a type; classification never marks a recruiter response without review."""
    if 'SENT' in email.get('labels', []):
        return {'type': 'application_sent', 'reason': 'Message présent dans les éléments envoyés ; contenu à vérifier.'}
    text = normalize((email.get('subject') or '') + '\n' + (email.get('body_text') or '').split('\n>')[0][:3500])
    patterns = [
        ('bounce', r'undeliverable|delivery status notification|delivery has failed|adresse introuvable|mail delivery subsystem', 'Notification de non-remise détectée.'),
        ('rejection', r'not be moving forward|not been selected|unable to offer|ne donn(?:ons|erons) pas suite|pas ete retenu|candidature n.a pas ete retenue|regret to inform', 'Formulation de refus détectée ; à confirmer.'),
        ('interview_request', r'proposons un entretien|invite.*(?:interview|entretien)|schedule.*interview|disponibilites.*entretien', 'Proposition d’entretien détectée ; à confirmer.'),
        ('acknowledgement', r'bien recu votre candidature|candidature.*re[çc]ue|application.*received|received your application|thank you for applying', 'Accusé de réception détecté, distinct d’une réponse humaine.'),
    ]
    for kind, pattern, reason in patterns:
        if re.search(pattern, text, re.S):
            return {'type': kind, 'reason': reason}
    if email.get('automated'):
        return {'type': 'newsletter', 'reason': 'En-têtes indiquant un message automatique ; à vérifier.'}
    return {'type': 'unknown', 'reason': 'Aucune règle fiable : choisissez le type après lecture.'}


def owned_applications(db: Session, owner: str):
    return db.query(Application).filter(Application.telegram_user_id == owner)


def suggestions(db: Session, event: EmailEvent) -> list[dict]:
    """Suggest exact company-name mentions only, never auto-link on fuzzy subject matches."""
    text = normalize((event.subject or '') + ' ' + (event.body_text or ''))
    results = []
    for app in owned_applications(db, event.owner_id).all():
        company = normalize(app.company or '').strip()
        if len(company) > 2 and re.search(r'(?<!\w)' + re.escape(company) + r'(?!\w)', text):
            results.append({'id': app.id, 'company': app.company, 'job_title': app.job_title, 'reason': 'Nom de l’entreprise présent dans le message ; association à confirmer.'})
    return results[:10]


def link_known_thread(db: Session, event: EmailEvent) -> None:
    """A previously confirmed thread can be linked, but a new event still needs review."""
    if not event.thread_id:
        return
    matches = db.query(EmailEvent.application_id).join(Application, EmailEvent.application_id == Application.id).filter(
        EmailEvent.owner_id == event.owner_id, EmailEvent.mailbox == event.mailbox,
        EmailEvent.thread_id == event.thread_id, EmailEvent.link_method == 'manual',
        EmailEvent.status == 'processed', Application.telegram_user_id == event.owner_id).distinct().all()
    if len(matches) == 1:
        event.application_id = matches[0][0]
        event.link_method = 'thread'


def update_tracking(db: Session, event: EmailEvent) -> None:
    """Update a single existing outreach record only from a confirmed dated event."""
    if not event.application_id or not event.received_at:
        return
    confirmed_type = {'cold_email': 'application_sent', 'application_ack': 'acknowledgement', 'interview_or_test': 'interview_request'}.get(event.confirmed_type, event.confirmed_type)
    if confirmed_type not in (*REPLY_TYPES, 'application_sent', 'bounce'):
        return
    tracks = db.query(OutreachTracking).filter(OutreachTracking.application_id == event.application_id).order_by(OutreachTracking.id.desc()).all()
    # Multiple recipients per application cannot safely be inferred from email alone.
    if len(tracks) > 1:
        return
    tracking = tracks[0] if tracks else OutreachTracking(application_id=event.application_id, outreach_type='email', status='pending')
    db.add(tracking)
    if confirmed_type == 'application_sent':
        if not tracking.outreach_date or event.received_at < tracking.outreach_date:
            tracking.outreach_date = event.received_at
        if not tracking.last_follow_up or event.received_at > tracking.last_follow_up:
            tracking.last_follow_up = event.received_at
        if not tracking.response_received and not tracking.next_follow_up and tracking.status not in ('bounced', 'rejected', 'archived'):
            tracking.next_follow_up = event.received_at + timedelta(days=tracking.reminder_interval_days or 7)
        return
    if tracking.outreach_date and event.received_at < tracking.outreach_date:
        return
    if tracking.response_date and event.received_at <= tracking.response_date:
        return
    if confirmed_type == 'bounce':
        if not tracking.response_received:
            tracking.status = 'bounced'
            tracking.next_follow_up = None
        return
    tracking.response_received = 1
    tracking.response_date = event.received_at
    tracking.response_message = event.body_text
    tracking.response_sentiment = 'negative' if confirmed_type == 'rejection' else 'positive' if confirmed_type == 'interview_request' else 'neutral'
    tracking.status = {'rejection':'rejected', 'interview_request':'interview', 'recruiter_reply':'responded'}[confirmed_type]
    tracking.next_follow_up = None
