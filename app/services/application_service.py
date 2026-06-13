import logging
from sqlalchemy.orm import Session
from app.database.models import Application, JobAnalysis, UserSession, ApplicationStatusEnum

logger = logging.getLogger(__name__)

def create_application(
    db: Session,
    telegram_user_id: str,
    raw_offer: str,
    source_url: str | None = None,
) -> Application:
    """Create new application record."""
    app = Application(
        telegram_user_id=telegram_user_id,
        raw_offer=raw_offer,
        source_url=source_url,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    logger.info(f"Created application {app.id} for user {telegram_user_id}")
    return app

def save_analysis(
    db: Session,
    application_id: int,
    analysis_json: dict,
) -> JobAnalysis:
    """Save job analysis to database."""
    analysis = JobAnalysis(
        application_id=application_id,
        analysis_json=analysis_json,
        missions=analysis_json.get("missions", []),
        required_skills=analysis_json.get("required_skills", []),
        soft_skills=analysis_json.get("soft_skills", []),
        ats_keywords=analysis_json.get("ats_keywords", []),
        missing_points=analysis_json.get("missing_points", []),
        strengths=analysis_json.get("strengths", []),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    logger.info(f"Saved analysis for application {application_id}")
    return analysis

def update_application_with_analysis(
    db: Session,
    application_id: int,
    analysis_json: dict,
) -> Application:
    """Update application with analysis results."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application {application_id} not found")

    app.company = analysis_json.get("company")
    app.job_title = analysis_json.get("job_title")
    app.recommended_angle = analysis_json.get("recommended_angle")
    app.match_score = analysis_json.get("match_score")
    app.status = ApplicationStatusEnum.analyzed

    db.commit()
    db.refresh(app)
    logger.info(f"Updated application {application_id} with analysis")
    return app

def get_or_create_user_session(db: Session, telegram_user_id: str) -> UserSession:
    """Get or create user session."""
    session = db.query(UserSession).filter(UserSession.telegram_user_id == telegram_user_id).first()
    if not session:
        session = UserSession(telegram_user_id=telegram_user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created session for user {telegram_user_id}")
    return session

def update_user_session(
    db: Session,
    telegram_user_id: str,
    last_application_id: int,
    state: str = "waiting_for_command",
) -> UserSession:
    """Update user session with latest application."""
    session = get_or_create_user_session(db, telegram_user_id)
    session.last_application_id = last_application_id
    session.state = state
    db.commit()
    db.refresh(session)
    return session

def get_last_application(db: Session, telegram_user_id: str) -> Application | None:
    """Get last application for user."""
    session = db.query(UserSession).filter(UserSession.telegram_user_id == telegram_user_id).first()
    if not session or not session.last_application_id:
        return None
    return db.query(Application).filter(Application.id == session.last_application_id).first()

def mark_application_as_generated(db: Session, application_id: int) -> Application:
    """Mark application as having generated documents."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application {application_id} not found")
    app.status = ApplicationStatusEnum.generated
    db.commit()
    db.refresh(app)
    return app
