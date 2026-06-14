import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import config
from app.services.openai_service import generate_text
from app.services.document_service import render_cv, render_letter, render_mail, save_document, get_output_path
from app.prompts.generation_prompt import get_cv_prompt, get_letter_prompt, get_mail_prompt
from app.agents.matching_agent import MatchingAgent
from app.database.models import GeneratedDocument, DocumentTypeEnum, ProfileBlock, CategoryEnum

logger = logging.getLogger(__name__)

class GenerationAgent:
    """Generate CV, letter, and email from analysis."""

    @staticmethod
    def _build_candidate_info(db: Session) -> dict:
        """Build candidate contact info from config/database."""
        candidate = {
            "name": config.CANDIDATE_NAME or "Candidate",
            "email": config.CANDIDATE_EMAIL or "",
            "phone": config.CANDIDATE_PHONE or "",
            "linkedin": config.CANDIDATE_LINKEDIN or "",
            "github": config.CANDIDATE_GITHUB or "",
            "website": config.CANDIDATE_WEBSITE or "",
        }
        return candidate

    @staticmethod
    def _build_profile_structure(db: Session, block_ids: list) -> dict:
        """Convert profile blocks into structured CV sections."""
        blocks = MatchingAgent.get_selected_blocks(db, block_ids)

        experiences = []
        projects = []
        skills_sections = []
        education = []
        certifications = []
        languages = []

        for block in blocks:
            if block["category"] == CategoryEnum.experience.value:
                experiences.append({
                    "title": block.get("title", ""),
                    "company": block.get("tags", [""])[0] if block.get("tags") else "",
                    "context": "",
                    "dates": "",
                    "bullets": [block.get("content", "")],
                })
            elif block["category"] == CategoryEnum.project.value:
                projects.append({
                    "title": block.get("title", ""),
                    "context": "",
                    "dates": "",
                    "bullets": [block.get("content", "")],
                })
            elif block["category"] == CategoryEnum.skill.value:
                skills_sections.append({
                    "label": block.get("title", ""),
                    "content": block.get("content", ""),
                })
            elif block["category"] == CategoryEnum.education.value:
                education.append({
                    "title": block.get("title", ""),
                    "school": block.get("tags", [""])[0] if block.get("tags") else "",
                    "year": "",
                    "meta": "",
                })
            elif block["category"] == CategoryEnum.certification.value:
                certifications.append({
                    "name": block.get("title", ""),
                })
            elif block["category"] == CategoryEnum.language.value:
                languages.append({
                    "name": block.get("title", ""),
                    "level": block.get("tags", [""])[0] if block.get("tags") else "",
                })

        return {
            "experiences": experiences,
            "projects": projects,
            "skills_sections": skills_sections,
            "education": education,
            "certifications": certifications,
            "languages": languages,
        }

    @staticmethod
    async def generate_cv(
        db: Session,
        application_id: int,
        analysis: dict,
        positioning: str,
    ) -> str:
        """Generate CV content."""
        block_ids = analysis.get("profile_blocks_to_use", [])
        blocks = MatchingAgent.get_selected_blocks(db, block_ids)

        prompt = get_cv_prompt(analysis, blocks, positioning)
        content = await generate_text(prompt)

        candidate = GenerationAgent._build_candidate_info(db)
        profile_structure = GenerationAgent._build_profile_structure(db, block_ids)

        context = {
            "candidate": candidate,
            "cv": {
                "title": f"{positioning.upper()}",
                "summary": content,
                "experiences": profile_structure["experiences"],
                "projects": profile_structure["projects"],
                "skills_sections": profile_structure["skills_sections"],
                "education": profile_structure["education"],
                "certifications": profile_structure["certifications"],
                "languages": profile_structure["languages"],
                "ats_keywords": analysis.get("ats_keywords", []),
            },
        }

        html = render_cv(context)

        filepath = get_output_path(application_id, "cv")
        save_document(html, filepath)

        doc = GeneratedDocument(
            application_id=application_id,
            document_type=DocumentTypeEnum.cv,
            filename=filepath.name,
            content=html,
            file_path=str(filepath),
        )
        db.add(doc)
        db.commit()

        logger.info(f"Generated CV for application {application_id}")
        return html

    @staticmethod
    async def generate_letter(
        db: Session,
        application_id: int,
        analysis: dict,
        positioning: str,
    ) -> str:
        """Generate motivation letter."""
        prompt = get_letter_prompt(analysis, positioning)
        content = await generate_text(prompt)

        context = {
            "candidate_name": "Akim Guentas",
            "company": analysis.get("company", ""),
            "job_position": analysis.get("job_title", ""),
            "content": content,
        }

        html = render_letter(context)

        filepath = get_output_path(application_id, "letter")
        save_document(html, filepath)

        doc = GeneratedDocument(
            application_id=application_id,
            document_type=DocumentTypeEnum.letter,
            filename=filepath.name,
            content=html,
            file_path=str(filepath),
        )
        db.add(doc)
        db.commit()

        logger.info(f"Generated letter for application {application_id}")
        return html

    @staticmethod
    async def generate_mail(
        db: Session,
        application_id: int,
        analysis: dict,
        positioning: str,
    ) -> str:
        """Generate email to recruiter."""
        prompt = get_mail_prompt(analysis, positioning)
        content = await generate_text(prompt)

        context = {
            "candidate_name": "Akim Guentas",
            "company": analysis.get("company", ""),
            "content": content,
        }

        mail = render_mail(context)

        filepath = get_output_path(application_id, "mail")
        save_document(mail, filepath)

        doc = GeneratedDocument(
            application_id=application_id,
            document_type=DocumentTypeEnum.mail,
            filename=filepath.name,
            content=mail,
            file_path=str(filepath),
        )
        db.add(doc)
        db.commit()

        logger.info(f"Generated mail for application {application_id}")
        return mail

    @staticmethod
    async def generate_documents(
        db: Session,
        application_id: int,
        analysis: dict,
        positioning: str,
        document_types: list[str] = None,
    ) -> dict[str, str]:
        """Generate requested documents."""
        if document_types is None:
            document_types = ["cv", "letter", "mail"]

        results = {}

        if "cv" in document_types:
            results["cv"] = await GenerationAgent.generate_cv(db, application_id, analysis, positioning)
        if "letter" in document_types:
            results["letter"] = await GenerationAgent.generate_letter(db, application_id, analysis, positioning)
        if "mail" in document_types:
            results["mail"] = await GenerationAgent.generate_mail(db, application_id, analysis, positioning)

        logger.info(f"Generated documents for application {application_id}: {list(results.keys())}")
        return results
