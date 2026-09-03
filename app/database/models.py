from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.database.db import Base

class CategoryEnum(str, enum.Enum):
    experience = "experience"
    skill = "skill"
    project = "project"
    education = "education"
    certification = "certification"
    tool = "tool"
    language = "language"

class TruthLevelEnum(str, enum.Enum):
    verified = "verified"
    declared = "declared"
    learning = "learning"

class ProficiencyLevelEnum(int, enum.Enum):
    """Mastery level: 0 (learning) → 3 (expert)"""
    learning = 0
    beginner = 1
    intermediate = 2
    expert = 3

class BlockStatusEnum(str, enum.Enum):
    """Project/achievement status"""
    completed = "completed"
    deployed = "deployed"
    in_progress = "in_progress"
    exploratory = "exploratory"
    not_deployed = "not_deployed"

class ApplicationStatusEnum(str, enum.Enum):
    analyzed = "analyzed"
    generated = "generated"
    saved = "saved"
    archived = "archived"

class DocumentTypeEnum(str, enum.Enum):
    cv = "cv"
    letter = "letter"
    mail = "mail"

class ProfileBlock(Base):
    __tablename__ = "profile_blocks"

    id = Column(Integer, primary_key=True)
    category = Column(SQLEnum(CategoryEnum), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)  # Keywords, metadata

    # Truth & verification
    truth_level = Column(SQLEnum(TruthLevelEnum), default=TruthLevelEnum.verified)

    # Skill-specific (for skills/technologies)
    proficiency_level = Column(SQLEnum(ProficiencyLevelEnum), nullable=True)

    # Project/achievement-specific (for achievements, projects)
    status = Column(SQLEnum(BlockStatusEnum), nullable=True)

    # Structured metrics (e.g., {"before": "5-6h/week", "after": "~1h/week", "reduction": "~80%"})
    metrics = Column(JSON, default=dict)

    # Technologies/tools used in this block
    technologies = Column(JSON, default=list)  # ["Python", "Power BI", "Excel"]

    # Job families this block is relevant for
    job_families = Column(JSON, default=list)  # ["Data Analyst", "BI Analyst"]

    # Company/organization context
    company = Column(String(255), nullable=True)

    # Time period (ISO dates or flexible strings)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)

    # Critical: Claims that should NEVER be modified, exaggerated, or invented
    forbidden_claims = Column(JSON, default=list)
    # Example: ["Do not claim 100% automation", "Do not invent metrics"]

    # Reference to source (for traceability)
    source_ref = Column(String(255), nullable=True)  # e.g., "master_v3:sidel_automation"

    # ATS weighting
    priority = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    source_url = Column(Text, nullable=True)
    raw_offer = Column(Text, nullable=False)
    recommended_angle = Column(String(255), nullable=True)
    match_score = Column(Integer, nullable=True)
    status = Column(SQLEnum(ApplicationStatusEnum), default=ApplicationStatusEnum.analyzed)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analyses = relationship("JobAnalysis", back_populates="application")
    documents = relationship("GeneratedDocument", back_populates="application")

class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), nullable=True)
    analysis_json = Column(JSON, nullable=False)
    missions = Column(JSON, default=list)
    required_skills = Column(JSON, default=list)
    soft_skills = Column(JSON, default=list)
    ats_keywords = Column(JSON, default=list)
    missing_points = Column(JSON, default=list)
    strengths = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="analyses")
    job_offer = relationship("JobOffer", foreign_keys=[job_offer_id])

class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    telegram_user_id = Column(String(255), nullable=False)
    document_type = Column(SQLEnum(DocumentTypeEnum), nullable=False)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(Text, nullable=True)
    format = Column(String(10), default="html")  # html, pdf, txt
    positioning = Column(String(255), nullable=True)
    skill_profile = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="documents")

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String(255), unique=True, nullable=False)
    last_application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    state = Column(String(50), default="idle")
    session_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    gap_events = relationship("SkillGapEvent", back_populates="user_session")


class SkillGapEvent(Base):
    """Store skill gaps discovered in each job offer analysis."""
    __tablename__ = "skill_gap_events"

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String(255), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    user_session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=True)

    offer_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role_family = Column(String(100), nullable=True)
    positioning = Column(String(100), nullable=True)

    skill_name = Column(String(100), nullable=False)
    skill_category = Column(String(50), nullable=True)

    required = Column(Integer, default=0)  # bool: 0=false, 1=true
    present = Column(Integer, default=0)   # bool: 0=false, 1=true
    gap = Column(Integer, default=0)       # bool: required & !present

    importance_score = Column(Integer, default=5)  # 1-10 scale
    confidence = Column(Integer, default=8)        # 1-10 scale

    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", foreign_keys=[application_id])
    user_session = relationship("UserSession", back_populates="gap_events")


class CareerIntelligenceSnapshot(Base):
    """Periodic snapshot of career intelligence insights."""
    __tablename__ = "career_intelligence_snapshots"

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String(255), nullable=False)

    total_offers_analyzed = Column(Integer, default=0)
    top_strengths = Column(JSON, default=list)      # List of skill names
    frequent_gaps = Column(JSON, default=list)       # List of dicts: {skill, frequency, importance}
    critical_gaps = Column(JSON, default=list)       # Ranked by gap_score
    recommended_projects = Column(JSON, default=list)
    role_family_strengths = Column(JSON, default=dict)  # {role_family: score}
    role_family_weaknesses = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BotInstance(Base):
    """Track bot instance lifecycle for singleton management."""
    __tablename__ = "bot_instances"

    id = Column(Integer, primary_key=True)
    pid = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)  # 'started', 'stopped', 'error'
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class ConversationHistory(Base):
    """Record all user conversations for audit and replay.

    Note: Python attribute 'metadata_json' maps to SQL column 'metadata' to avoid
    SQLAlchemy reserved name conflict.
    """
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    message_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Company(Base):
    """Employer aggregation for Job Market Radar MVP.

    Groups job offers by company; tracks recruitment activity.
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    website = Column(String(500), nullable=True)
    job_count_this_week = Column(Integer, default=0)
    skill_frequency = Column(JSON, default=dict)  # {"Python": 3, "SQL": 2, ...}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job_offers = relationship("JobOffer", back_populates="company")
    contacts = relationship("CompanyContact", back_populates="company")


class JobOffer(Base):
    """Scraped job posting linked to a company.

    MVP Phase 1: stores URL, title, required_skills, raw_text from trafilatura.
    """
    __tablename__ = "job_offers"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    job_title = Column(String(255), nullable=False)
    job_url = Column(Text, nullable=False, unique=True)
    source = Column(String(50), nullable=False)  # "indeed", "linkedin", "website", etc.
    raw_text = Column(Text, nullable=True)  # trafilatura output
    required_skills = Column(JSON, default=list)  # ["Python", "SQL", ...]
    posted_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")  # "active", "closed", "archived"
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="job_offers")


class CompanyContact(Base):
    """Hiring contact at a company (manual verification for MVP Phase 1).

    source_url is mandatory: LinkedIn profile, company careers page, etc.
    verification_status tracks lead quality.
    """
    __tablename__ = "company_contacts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    contact_name = Column(String(255), nullable=False)
    role_raw = Column(String(255), nullable=False)  # Free text: "Talent Acquisition Manager"
    role_category = Column(String(100), nullable=True)  # Normalized: "recruiter", "manager", etc.
    email = Column(String(255), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=False)  # MANDATORY: LinkedIn/website/careers
    data_source = Column(String(50), nullable=False)  # "manual_verified", "linkedin", "website"
    verification_status = Column(String(20), default="verified")  # "verified", "pending", "invalid"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")


class OutreachDraft(Base):
    """Outreach message draft (Phase 6).

    Generated from company intelligence + contact + job analysis.
    Grounded against Master CV evidence before status = READY.
    """
    __tablename__ = "outreach_drafts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("company_contacts.id"), nullable=False)
    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), nullable=True)
    channel = Column(String(50), default="email")  # "email", "linkedin", etc.
    subject_line = Column(String(200), nullable=True)
    message_text = Column(Text, nullable=False)
    evidence_ids = Column(JSON, default=list)  # ["SIDEL.DATA_&_BI.001", ...]
    grounding_result = Column(JSON, nullable=True)  # {grounded: bool, unsupported_claims: [...]}
    status = Column(String(50), default="DRAFT")  # "DRAFT", "READY", "NEEDS_REVIEW", "ARCHIVED"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company")
    contact = relationship("CompanyContact")
    job_offer = relationship("JobOffer")
