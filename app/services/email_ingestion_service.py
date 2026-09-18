"""Page-atomic Gmail import with a durable cursor and a shared process lock."""
import fcntl
import hashlib
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from app.config import config
from app.database.models import EmailEvent, GmailSyncState
from app.services.gmail_service import GmailService, GmailUnavailable
from app.services.email_tracking_service import classify_email, link_known_thread


@contextmanager
def ingestion_lock(db):
    key = hashlib.sha256((str(db.bind.url) + config.GMAIL_APPLICATION_USER_ID).encode()).hexdigest()[:24]
    path = Path(tempfile.gettempdir()) / f'jobapply-gmail-{key}.lock'
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GmailUnavailable('Une synchronisation est déjà en cours. Réessayez dans un instant.') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class EmailIngestionService:
    def __init__(self, db, gmail_service=None):
        self.db = db
        self.gmail = gmail_service or GmailService()

    def ingest_emails(self, max_pages=3):
        if not config.GMAIL_ENABLED:
            raise GmailUnavailable('Gmail est désactivé. Configurez GMAIL_ENABLED et autorisez le compte avant de synchroniser.')
        with ingestion_lock(self.db):
            return self._ingest(max_pages)

    def _ingest(self, max_pages):
        owner = config.GMAIL_APPLICATION_USER_ID
        state = self.db.get(GmailSyncState, owner)
        if state is None:
            state = GmailSyncState(owner_id=owner)
            self.db.add(state)
            self.db.commit()
        imported = duplicate = 0
        try:
            mailbox = self.gmail.authenticate()
            if state.mailbox and state.mailbox != mailbox:
                raise GmailUnavailable('Le compte autorisé diffère du compte synchronisé. Utilisez un espace candidat distinct pour changer de compte.')
            if state.query != config.GMAIL_SEARCH_QUERY:
                state.next_page_token = None
            state.mailbox, state.query = mailbox, config.GMAIL_SEARCH_QUERY
            for _ in range(max_pages):
                page = self.gmail.page(state.query, 100, state.next_page_token)
                page_imported = page_duplicate = 0
                for item in page['messages']:
                    existing = self.db.query(EmailEvent).filter_by(owner_id=owner, mailbox=mailbox, gmail_message_id=item['gmail_message_id']).first()
                    if existing:
                        page_duplicate += 1
                        continue
                    proposed = classify_email(item)
                    item = {k:v for k,v in item.items() if k != 'automated'}
                    event = EmailEvent(**item, owner_id=owner, mailbox=mailbox,
                        detected_type=proposed['type'], classification_reason=proposed['reason'], status='pending')
                    link_known_thread(self.db, event)
                    self.db.add(event)
                    self.db.flush()
                    page_imported += 1
                state.next_page_token = page['next_page_token']
                state.last_synced_at, state.last_error = datetime.utcnow(), None
                self.db.commit()
                imported += page_imported
                duplicate += page_duplicate
                if not state.next_page_token:
                    break
            return {'imported':imported, 'duplicates':duplicate, 'has_more':bool(state.next_page_token), 'last_synced_at':state.last_synced_at.isoformat()+'Z'}
        except Exception as exc:
            self.db.rollback()
            message = str(exc) if isinstance(exc, GmailUnavailable) else 'Synchronisation interrompue. Les pages déjà enregistrées sont conservées ; réessayez.'
            state = self.db.get(GmailSyncState, owner)
            state.last_error = message
            self.db.commit()
            raise GmailUnavailable(message) from None
