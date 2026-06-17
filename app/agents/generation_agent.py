import logging
import re
from sqlalchemy.orm import Session
from app.config import config
from app.services.openai_service import generate_text, generate_cv_payload
from app.services.document_service import render_cv, render_letter, render_mail, save_document, get_output_path
from app.services.master_cv_service import load_master_cv, validate_adaptation
from app.prompts.generation_prompt import get_cv_payload_prompt, get_cv_prompt, get_letter_prompt, get_mail_prompt
from app.agents.matching_agent import MatchingAgent
from app.agents.quality_agent import QualityAgent
from app.agents.cv_adaptation_agent import CVAdaptationAgent
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
    def _build_fallback_adaptation(master_cv: dict, positioning: str) -> dict:
        """Build safe adaptation fallback when CVAdaptationAgent fails.

        Uses FIXED ordering with ALL original bullets.
        Default projects: Elevia, Job Apply Assistant, V.I.E Matcher (no SkillMap).
        """
        # FIXED ordering (never changes)
        fixed_exp_order = [0, 1, 2]  # Sidel, MadeByAkim, Vassard
        default_proj_ids = [0, 1, 2]  # Elevia, Job Apply Assistant, V.I.E Matcher

        adaptation = {
            "title": positioning,
            "summary": "",
            "experience_order": fixed_exp_order,
            "experience_bullets": {
                str(i): master_cv["experiences"][i].get("bullets", [])
                for i in fixed_exp_order
            },
            "project_order": default_proj_ids,
            "project_bullets": {
                str(i): master_cv["projects"][i].get("bullets", [])
                for i in default_proj_ids
            },
            "ats_keywords": [],
        }
        return adaptation

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
        skill_profile: str = "general_business_data",
        telegram_user_id: str = None,
    ) -> str:
        """Generate CV by adapting Master CV. Never invent content.

        Flow:
        1. Load Master CV (source of truth)
        2. Call CVAdaptationAgent to adapt for job offer using skill_profile
        3. Validate adaptation (no new content)
        4. Render master_cv.html with adaptation payload
        5. Save to DB + file
        """
        # Load Master CV (fixed, verified content)
        master_cv = load_master_cv()
        logger.info(f"Master CV loaded: {len(master_cv['experiences'])} experiences")

        try:
            # ADAPT: Get adaptation JSON (not full CV) with skill profile guidance
            adaptation = await CVAdaptationAgent.adapt_cv(
                analysis,
                positioning,
                master_cv,
                skill_profile,
            )

            # VALIDATE: Ensure no hallucinations in adaptation
            validation_result = validate_adaptation(adaptation, master_cv)
            if not validation_result["is_valid"]:
                logger.warning(f"Adaptation validation failed: {validation_result['issues']}")
                # Fallback: use master CV with unchanged title/summary
                adaptation = GenerationAgent._build_fallback_adaptation(master_cv, positioning)

            logger.info(
                f"CV adapted: title={adaptation.get('title', 'N/A')}, "
                f"experiences_order={adaptation.get('experience_order', [])}, "
                f"projects_order={adaptation.get('project_order', [])}"
            )

        except Exception as e:
            logger.error(f"CV adaptation failed: {e}, using fallback")
            adaptation = GenerationAgent._build_fallback_adaptation(master_cv, positioning)

        # Build context for master_cv.html template
        candidate = GenerationAgent._build_candidate_info(db)

        context = {
            "candidate": candidate,
            "adaptation": adaptation,
            "master_cv": master_cv,
        }

        # Render master_cv.html with adaptation payload
        html = render_cv(context, template_name="master_cv.html")

        filepath = get_output_path(application_id, "cv")
        save_document(html, filepath)

        doc = GeneratedDocument(
            application_id=application_id,
            telegram_user_id=telegram_user_id or "",
            document_type=DocumentTypeEnum.cv,
            filename=filepath.name,
            content=html,
            file_path=str(filepath),
            positioning=positioning,
            skill_profile=skill_profile,
        )
        db.add(doc)
        db.commit()

        logger.info(f"Generated CV for application {application_id} user={telegram_user_id}")
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
        skill_profile: str = "general_business_data",
        telegram_user_id: str = None,
    ) -> dict[str, str]:
        """Generate requested documents using skill profile."""
        if document_types is None:
            document_types = ["cv", "letter", "mail"]

        results = {}

        if "cv" in document_types:
            results["cv"] = await GenerationAgent.generate_cv(db, application_id, analysis, positioning, skill_profile, telegram_user_id)
        if "letter" in document_types:
            results["letter"] = await GenerationAgent.generate_letter(db, application_id, analysis, positioning)
        if "mail" in document_types:
            results["mail"] = await GenerationAgent.generate_mail(db, application_id, analysis, positioning)

        logger.info(f"Generated documents for application {application_id}: {list(results.keys())} with skill_profile={skill_profile} user={telegram_user_id}")
        return results
