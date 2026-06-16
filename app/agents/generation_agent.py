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
    def _build_fallback_cv_payload(blocks: list[dict], positioning: str) -> dict:
        """Build safe CV payload directly from profile_blocks (no OpenAI).

        Used when OpenAI-generated payload contains hallucinations.
        Constructs CV entirely from authorized blocks.
        """
        payload = {
            "title": positioning,
            "summary": "Professional with expertise in data analysis, business intelligence and automation.",
            "experiences": [],
            "projects": [],
            "skills_sections": [],
            "education": [],
            "certifications": [],
            "languages": [],
            "ats_keywords": [],
        }

        for block in blocks:
            category = block.get("category", "")

            if category == "experience":
                payload["experiences"].append({
                    "title": block.get("title", ""),
                    "company": block.get("tags", [""])[0] if block.get("tags") else "",
                    "context": "",
                    "dates": "",
                    "bullets": [block.get("content", "")[:200]],
                })

            elif category == "project":
                payload["projects"].append({
                    "title": block.get("title", ""),
                    "context": "",
                    "dates": "",
                    "bullets": [block.get("content", "")[:200]],
                })

            elif category == "skill":
                if block.get("tags"):
                    payload["skills_sections"].append({
                        "label": block.get("title", ""),
                        "content": ", ".join(str(t) for t in block["tags"]),
                    })

            elif category == "education":
                payload["education"].append({
                    "title": block.get("title", ""),
                    "school": block.get("tags", [""])[0] if block.get("tags") else "",
                    "year": "",
                    "meta": "",
                })

            elif category == "certification":
                payload["certifications"].append({
                    "name": block.get("title", ""),
                })

            elif category == "language":
                payload["languages"].append({
                    "name": block.get("title", ""),
                    "level": block.get("tags", [""])[0] if block.get("tags") else "Intermediate",
                })

        return payload

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
        """Generate CV using complete profile base + selected emphasis.

        Flow:
        1. Fetch ALL profile_blocks (complete base)
        2. Fetch selected_blocks (priority signal)
        3. Generate CV payload (JSON only, using BOTH sets)
        4. Clean payload (remove markdown/HTML)
        5. Validate against all_profile_blocks (remove hallucinations)
        6. Render Jinja2 template
        7. Save to DB + file
        """
        # Get selected blocks (priority signal)
        block_ids = analysis.get("profile_blocks_to_use", [])
        selected_blocks = MatchingAgent.get_selected_blocks(db, block_ids)

        # Get ALL blocks (complete profile base)
        all_blocks = MatchingAgent.get_selected_blocks(
            db, [b["id"] for b in MatchingAgent.get_selected_blocks(db, None) or []]
        )
        # Simpler: just query directly
        from app.database.models import ProfileBlock
        all_profile_blocks = db.query(ProfileBlock).order_by(ProfileBlock.priority.desc()).all()
        all_blocks_dict = [
            {
                "id": b.id,
                "title": b.title,
                "content": b.content,
                "category": b.category.value,
                "tags": b.tags,
            }
            for b in all_profile_blocks
        ]

        prompt = get_cv_payload_prompt(analysis, all_blocks_dict, selected_blocks, positioning)
        payload = await generate_cv_payload(prompt)

        payload = GenerationAgent._clean_payload(payload)

        # VALIDATION STEP: Detect and remove hallucinations
        validation_result = QualityAgent.validate_cv_payload(payload, all_blocks_dict)
        clean_payload = validation_result["clean_payload"]
        removed_items = validation_result["removed_items"]

        if removed_items:
            logger.warning(f"Hallucinations removed: {removed_items}")

        # SAFETY FALLBACK: If too many hallucinations, use safe payload
        if len(removed_items) > 2 or not clean_payload.get("experiences"):
            logger.warning(
                f"Too many hallucinations or invalid payload, using safe fallback CV"
            )
            clean_payload = GenerationAgent._build_fallback_cv_payload(all_blocks_dict, positioning)

        candidate = GenerationAgent._build_candidate_info(db)

        context = {
            "candidate": candidate,
            "cv": clean_payload,
        }

        # Extract titles for logging
        exp_titles = [e.get("title", "") for e in clean_payload.get("experiences", [])]
        skill_labels = [s.get("label", "") for s in clean_payload.get("skills_sections", [])]

        logger.info(
            f"CV generated: title={clean_payload.get('title', 'N/A')}, "
            f"all_blocks={len(all_blocks_dict)}, "
            f"selected_blocks={len(selected_blocks)}, "
            f"experiences={len(clean_payload.get('experiences', []))} {exp_titles}, "
            f"skills={len(clean_payload.get('skills_sections', []))} {skill_labels}, "
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
