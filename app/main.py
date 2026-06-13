from fastapi import FastAPI
from app.config import config
from app.database.db import engine, Base
from app.database.models import ProfileBlock, Application, JobAnalysis, GeneratedDocument, UserSession

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Job Apply Assistant",
    description="IA-powered job application assistant",
    version="0.1.0",
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": config.APP_ENV}

@app.get("/")
async def root():
    return {
        "name": "Job Apply Assistant",
        "version": "0.1.0",
        "message": "API is running. Use Telegram bot for interaction.",
    }
