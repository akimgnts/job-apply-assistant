import logging
import re
from sqlalchemy.orm import Session
from app.config import config
from app.services.openai_service import generate_text, generate_cv_payload
from app.services.document_service import render_cv, render_letter, render_mail, save_document, get_output_path
from app.prompts.generation_prompt import get_cv_payload_prompt, get_cv_prompt, get_letter_prompt, get_mail_prompt
from app.agents.matching_agent import MatchingAgent
from app.agents.quality_agent import QualityAgent
from app.database.models import GeneratedDocument, DocumentTypeEnum, ProfileBlock, CategoryEnum

logger = logging.getLogger(__name__)

class GenerationAgent:
    """Generate CV, letter, and email from analysis."""

    @staticmethod
    def _build_candidate_info(db: Session) -> dict:
        """Build candidate contact info from config/database."""
        candidate = {
            "name": config.CANDIDATE_NAME or "",
            "email": config.CANDIDATE_EMAIL or "",
            "phone": config.CANDIDATE_PHONE or "",
            "linkedin": config.CANDIDATE_LINKEDIN or "",
            "github": config.CANDIDATE_GITHUB or "",
            "website": config.CANDIDATE_WEBSITE or "",
        }
        return candidate

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove markdown/HTML artifacts from text."""
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r"^```[\w]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    @staticmethod
    def _clean_payload(payload: dict) -> dict:
        """Clean up CV payload, removing HTML/markdown."""
        if not payload:
            return {}

        payload["title"] = GenerationAgent._clean_text(payload.get("title", ""))[:100]
        payload["summary"] = GenerationAgent._clean_text(payload.get("summary", ""))[:500]

        for exp in payload.get("experiences", []):
            exp["title"] = GenerationAgent._clean_text(exp.get("title", ""))
            exp["company"] = GenerationAgent._clean_text(exp.get("company", ""))
            exp["context"] = GenerationAgent._clean_text(exp.get("context", ""))
            exp["dates"] = GenerationAgent._clean_text(exp.get("dates", ""))
            exp["bullets"] = [
                GenerationAgent._clean_text(b) for b in exp.get("bullets", [])
            ]

        for proj in payload.get("projects", []):
            proj["title"] = GenerationAgent._clean_text(proj.get("title", ""))
            proj["context"] = GenerationAgent._clean_text(proj.get("context", ""))
            proj["dates"] = GenerationAgent._clean_text(proj.get("dates", ""))
            proj["bullets"] = [
                GenerationAgent._clean_text(b) for b in proj.get("bullets", [])
            ]

        for skill in payload.get("skills_sections", []):
            skill["label"] = GenerationAgent._clean_text(skill.get("label", ""))
            skill["content"] = GenerationAgent._clean_text(skill.get("content", ""))

        for edu in payload.get("education", []):
            edu["title"] = GenerationAgent._clean_text(edu.get("title", ""))
            edu["school"] = GenerationAgent._clean_text(edu.get("school", ""))
            edu["year"] = GenerationAgent._clean_text(edu.get("year", ""))

        for cert in payload.get("certifications", []):
            cert["name"] = GenerationAgent._clean_text(cert.get("name", ""))

        for lang in payload.get("languages", []):
            lang["name"] = GenerationAgent._clean_text(lang.get("name", ""))
            lang["level"] = GenerationAgent._clean_text(lang.get("level", ""))

        payload["ats_keywords"] = [
            GenerationAgent._clean_text(k) for k in payload.get("ats_keywords", [])
        ]

        return payload

    @staticmethod
    async def generate_cv(
        db: Session,
        application_id: int,
        analysis: dict,
        positioning: str,
    ) -> str:
        """Generate CV with validation against profile_blocks.

        Flow:
        1. Get selected profile blocks
        2. Generate CV payload (JSON only)
        3. Clean payload (remove markdown/HTML)
        4. Validate against profile blocks (remove hallucinations)
        5. Render Jinja2 template
        6. Save to DB + file
        """
        block_ids = analysis.get("profile_blocks_to_use", [])
        blocks = MatchingAgent.get_selected_blocks(db, block_ids)

        prompt = get_cv_payload_prompt(analysis, blocks, positioning)
        payload = await generate_cv_payload(prompt)

        payload = GenerationAgent._clean_payload(payload)

        # VALIDATION STEP: Detect and remove hallucinations
        validation_result = QualityAgent.validate_cv_payload(payload, blocks)
        clean_payload = validation_result["clean_payload"]
        removed_items = validation_result["removed_items"]

        if removed_items:
            logger.warning(f"Hallucinations removed: {removed_items}")

        candidate = GenerationAgent._build_candidate_info(db)

        context = {
            "candidate": candidate,
            "cv": clean_payload,
        }

        logger.info(
            f"CV generated: title={clean_payload.get('title', 'N/A')}, "
            f"experiences={len(clean_payload.get('experiences', []))}, "
            f"skills={len(clean_payload.get('skills_sections', []))}, "
            f"hallucinations_removed={len(removed_items)}"
        )

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
