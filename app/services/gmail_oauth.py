"""Explicit one-time Gmail consent: python -m app.services.gmail_oauth."""
from pathlib import Path
from app.config import config
from app.services.gmail_service import SCOPES, save_credentials


def main():
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not Path(config.GMAIL_CREDENTIALS_FILE).is_file():
        raise SystemExit('Téléchargez un client OAuth de type application de bureau et configurez GMAIL_CREDENTIALS_FILE.')
    if Path(config.GMAIL_TOKEN_FILE).suffix != '.json':
        raise SystemExit('GMAIL_TOKEN_FILE doit être un fichier .json, jamais un pickle.')
    flow = InstalledAppFlow.from_client_secrets_file(config.GMAIL_CREDENTIALS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    save_credentials(credentials, Path(config.GMAIL_TOKEN_FILE))
    print('Autorisation Gmail en lecture seule enregistrée. Activez GMAIL_ENABLED puis redémarrez le serveur.')


if __name__ == '__main__':
    main()
