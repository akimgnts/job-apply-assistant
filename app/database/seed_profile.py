from app.database.db import SessionLocal, engine, Base
from app.database.models import ProfileBlock, CategoryEnum, TruthLevelEnum

PROFILE_BLOCKS = [
    {
        "category": CategoryEnum.experience,
        "title": "Sidel — Marketing & Communication / Data Reporting",
        "content": "Expérience en alternance chez Sidel sur des missions marketing, communication, reporting et coordination internationale. Travail sur Excel, Power BI, analyse clients, événements B2B, contenus marketing, suivi de leads, coordination avec équipes commerciales et communication.",
        "tags": ["marketing", "communication", "data", "reporting", "powerbi", "excel", "b2b", "coordination", "international"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 10,
    },
    {
        "category": CategoryEnum.project,
        "title": "Elevia — Projet IA / Matching professionnel",
        "content": "Projet personnel de plateforme IA autour du matching entre profils candidats et offres. Travail sur parsing CV, extraction de compétences, canonicalisation, scoring, matching, FastAPI, PostgreSQL, pipelines de données, observabilité et génération d'explications de matching.",
        "tags": ["ai", "data", "matching", "fastapi", "postgresql", "cv_parsing", "skills", "automation", "product"],
        "truth_level": TruthLevelEnum.in_progress,
        "priority": 10,
    },
    {
        "category": CategoryEnum.experience,
        "title": "Made By Curve — Freelance design",
        "content": "Activité freelance en design graphique, retouche photo, création de visuels social media, identité visuelle, direction artistique légère et utilisation de la suite Adobe.",
        "tags": ["design", "adobe", "photoshop", "illustrator", "social_media", "branding", "freelance"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 7,
    },
    {
        "category": CategoryEnum.education,
        "title": "Formation — MSc Business Intelligence & Analytics",
        "content": "Formation en Business Intelligence, Analytics, data analysis appliquée au marketing et aux problématiques business.",
        "tags": ["business_intelligence", "analytics", "data_analysis", "marketing", "business"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 8,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Compétences Data",
        "content": "Compétences en analyse de données, Excel, Power BI, SQL, Python, reporting, visualisation, nettoyage de données et interprétation business.",
        "tags": ["python", "sql", "powerbi", "excel", "reporting", "data_analysis", "dataviz"],
        "truth_level": TruthLevelEnum.verified,
        "priority": 9,
    },
    {
        "category": CategoryEnum.skill,
        "title": "Compétences IA / Automatisation",
        "content": "Utilisation d'outils IA pour l'automatisation, prompt engineering, structuration de workflows, génération documentaire, analyse de texte et conception d'assistants IA.",
        "tags": ["ai", "automation", "prompt_engineering", "workflows", "openai", "agents"],
        "truth_level": TruthLevelEnum.project,
        "priority": 9,
    },
]

def seed_profile():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_count = db.query(ProfileBlock).count()
        if existing_count == 0:
            for block_data in PROFILE_BLOCKS:
                block = ProfileBlock(**block_data)
                db.add(block)
            db.commit()
            print(f"✓ Seeded {len(PROFILE_BLOCKS)} profile blocks")
        else:
            print(f"Profile already seeded ({existing_count} blocks found)")
    finally:
        db.close()

if __name__ == "__main__":
    seed_profile()
