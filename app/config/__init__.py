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
