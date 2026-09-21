import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # App
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = APP_ENV == "development"

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jobapply:password@localhost:5432/job_apply_db")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DEBUG_TELEGRAM_ERRORS = os.getenv("DEBUG_TELEGRAM_ERRORS", "false").lower() == "true"
    DEBUG_TELEGRAM_STEPS = os.getenv("DEBUG_TELEGRAM_STEPS", "false").lower() == "true"

    # Candidate info
    CANDIDATE_NAME = os.getenv("CANDIDATE_NAME")
    CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL")
    CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE")
    CANDIDATE_LINKEDIN = os.getenv("CANDIDATE_LINKEDIN")
    CANDIDATE_GITHUB = os.getenv("CANDIDATE_GITHUB")
    CANDIDATE_WEBSITE = os.getenv("CANDIDATE_WEBSITE")

    # Paths
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Document delivery
    ENABLE_PDF_EXPORT = os.getenv("ENABLE_PDF_EXPORT", "false").lower() == "true"

    # Elevia API Integration
    ELEVIA_ENABLED = os.getenv("ELEVIA_ENABLED", "false").lower() == "true"
    ELEVIA_BASE_URL = os.getenv("ELEVIA_BASE_URL", "http://37.59.112.53:3000/api")
    ELEVIA_API_KEY = os.getenv("ELEVIA_API_KEY", "")
    ELEVIA_REQUEST_TIMEOUT_MS = int(os.getenv("ELEVIA_REQUEST_TIMEOUT_MS", "20000"))

config = Config()

# Gmail is a single explicitly selected mailbox and candidate workspace.
config.GMAIL_ENABLED = os.getenv('GMAIL_ENABLED', 'false').lower() == 'true'
config.GMAIL_CREDENTIALS_FILE = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
config.GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
config.GMAIL_USER_ID = os.getenv('GMAIL_USER_ID', 'me')
config.GMAIL_APPLICATION_USER_ID = os.getenv('WEB_USER_ID', 'local')
config.GMAIL_SEARCH_QUERY = os.getenv('GMAIL_SEARCH_QUERY', 'newer_than:30d {candidature recrutement entretien application interview recruiting recruiter} -category:promotions -category:social')
config.GMAIL_INGESTION_INTERVAL_MINUTES = max(5, int(os.getenv('GMAIL_INGESTION_INTERVAL_MINUTES', '30')))
config.GMAIL_SCHEDULER_ENABLED = os.getenv('GMAIL_SCHEDULER_ENABLED', 'false').lower() == 'true'

# ATS/job-board collection and notifications.
config.ATS_SCHEDULER_ENABLED = os.getenv('ATS_SCHEDULER_ENABLED', 'false').lower() == 'true'
config.ATS_SCHEDULER_TIMES = os.getenv('ATS_SCHEDULER_TIMES', '08:30,18:30')
config.ATS_NOTIFY_TELEGRAM = os.getenv('ATS_NOTIFY_TELEGRAM', 'false').lower() == 'true'
config.ATS_NOTIFY_CHAT_ID = os.getenv('ATS_NOTIFY_CHAT_ID') or os.getenv('WEB_USER_ID')
config.WEB_PUBLIC_URL = os.getenv('WEB_PUBLIC_URL', '')
