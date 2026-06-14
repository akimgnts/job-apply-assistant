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

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Candidate info
    CANDIDATE_NAME = os.getenv("CANDIDATE_NAME")
    CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL")
    CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE")
    CANDIDATE_LINKEDIN = os.getenv("CANDIDATE_LINKEDIN")
    CANDIDATE_GITHUB = os.getenv("CANDIDATE_GITHUB")
    CANDIDATE_WEBSITE = os.getenv("CANDIDATE_WEBSITE")

    # Paths
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
    PROJECT_ROOT = Path(__file__).parent.parent

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()
