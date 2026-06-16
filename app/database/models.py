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
    project = "project"
    in_progress = "in_progress"
    learning = "learning"

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
    tags = Column(JSON, default=list)
    truth_level = Column(SQLEnum(TruthLevelEnum), default=TruthLevelEnum.verified)
    priority = Column(Integer, default=0)
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
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    analysis_json = Column(JSON, nullable=False)
    missions = Column(JSON, default=list)
    required_skills = Column(JSON, default=list)
    soft_skills = Column(JSON, default=list)
    ats_keywords = Column(JSON, default=list)
    missing_points = Column(JSON, default=list)
    strengths = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="analyses")

class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    telegram_user_id = Column(String(255), nullable=False)
    document_type = Column(SQLEnum(DocumentTypeEnum), nullable=False)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(Text, nullable=True)
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
