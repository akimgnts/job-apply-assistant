"""Read-only Gmail transport. Interactive OAuth is deliberately outside the server."""
import base64
import os
import re
import tempfile
from datetime import datetime, timezone
from email.utils import parseaddr, getaddresses
from html.parser import HTMLParser
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailUnavailable(RuntimeError):
    """Actionable connection failure safe to present without provider secrets."""


class _TextHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'div', 'br', 'li'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _body(part: dict) -> tuple[list[str], list[str]]:
    plain, html = [], []
    if part.get('filename'):
        return plain, html
    data = part.get('body', {}).get('data')
    mime = part.get('mimeType', 'text/plain')
    if data and mime in ('text/plain', 'text/html'):
        try:
            raw = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
            text = raw.decode('utf-8', errors='replace')
            (plain if mime == 'text/plain' else html).append(text)
        except (ValueError, TypeError):
            pass
    for child in part.get('parts', []):
        p, h = _body(child)
        plain.extend(p)
        html.extend(h)
    return plain, html


def parse_message(message: dict) -> dict:
    """Decode nested MIME without rendering HTML; use Gmail's canonical UTC timestamp."""
    payload = message.get('payload', {})
    headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
    name, address = parseaddr(headers.get('from', ''))
    plain, html = _body(payload)
    if plain:
        body = '\n'.join(plain)
    else:
        parser = _TextHTML()
        parser.feed('\n'.join(html))
        body = ''.join(parser.parts)
    stamp = message.get('internalDate')
    received = datetime.fromtimestamp(int(stamp) / 1000, timezone.utc).replace(tzinfo=None) if stamp else None
    return {'gmail_message_id': message['id'], 'thread_id': message.get('threadId'),
            'sender_email': address.lower(), 'sender_name': name,
            'recipients': [email.lower() for _, email in getaddresses([headers.get('to', ''), headers.get('cc', '')])],
            'subject': headers.get('subject', '')[:500], 'snippet': message.get('snippet', ''),
            'body_text': body.strip()[:20000], 'received_at': received,
            'labels': message.get('labelIds', []),
            'automated': headers.get('auto-submitted', 'no').lower() != 'no' or bool(headers.get('list-unsubscribe'))}


def fetch_page(service, user_id: str, query: str, size: int, page_token: str | None = None) -> dict:
    """Fetch one complete page or fail; never hide a provider error as an empty inbox."""
    kwargs = {'userId': user_id, 'q': query, 'maxResults': min(max(size, 1), 100)}
    if page_token:
        kwargs['pageToken'] = page_token
    result = service.users().messages().list(**kwargs).execute()
    messages = [parse_message(service.users().messages().get(userId=user_id, id=row['id'], format='full').execute())
                for row in result.get('messages', [])]
    return {'messages': messages, 'next_page_token': result.get('nextPageToken')}


def save_credentials(credentials, path: Path) -> None:
    """Replace a private JSON token atomically, including after refresh."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.gmail-token-')
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(credentials.to_json())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class GmailService:
    """Connect only with an existing, restricted OAuth token; never open a browser here."""
    def __init__(self):
        self.service = None

    def authenticate(self):
        from app.config import config
        path = Path(config.GMAIL_TOKEN_FILE)
        if path.suffix != '.json' or not path.is_file():
            raise GmailUnavailable('Autorisez Gmail avec python -m app.services.gmail_oauth, puis relancez la synchronisation.')
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            credentials = Credentials.from_authorized_user_file(str(path))
            if set(credentials.scopes or []) != set(SCOPES):
                raise GmailUnavailable('Le jeton Gmail doit autoriser uniquement gmail.readonly. Recréez l’autorisation.')
            if not credentials.valid:
                if not credentials.refresh_token:
                    raise GmailUnavailable('L’autorisation Gmail a expiré. Reconnectez le compte.')
                credentials.refresh(Request())
                save_credentials(credentials, path)
            import httplib2
            from google_auth_httplib2 import AuthorizedHttp
            self.service = build('gmail', 'v1', http=AuthorizedHttp(credentials, http=httplib2.Http(timeout=30)), cache_discovery=False)
            profile = self.service.users().getProfile(userId=config.GMAIL_USER_ID).execute()
            return profile['emailAddress'].lower()
        except GmailUnavailable:
            raise
        except Exception:
            raise GmailUnavailable('Connexion Gmail impossible. Vérifiez les dépendances Google et l’autorisation du compte.') from None

    def page(self, query, size=100, page_token=None):
        from app.config import config
        try:
            return fetch_page(self.service, config.GMAIL_USER_ID, query, size, page_token)
        except Exception:
            raise GmailUnavailable('La lecture Gmail a échoué. Réessayez ; aucune page incomplète n’a été enregistrée.') from None
