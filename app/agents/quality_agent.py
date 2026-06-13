import logging
import json
from sqlalchemy.orm import Session
from app.services.openai_service import analyze_offer
from app.prompts.quality_prompt import get_quality_check_prompt
from app.database.models import ProfileBlock

logger = logging.getLogger(__name__)

class QualityAgent:
    """Verify generated documents don't contain invented or exaggerated claims."""

    @staticmethod
    async def check_document(
        db: Session,
        document_content: str,
        document_type: str,
    ) -> dict:
        """
        Check document quality and integrity.
        Returns quality report with recommendation.
        """
        profile_blocks = db.query(ProfileBlock).all()
        profile_data = [
            {
                "id": b.id,
                "title": b.title,
                "content": b.content,
                "category": b.category.value,
                "tags": b.tags,
            }
            for b in profile_blocks
        ]

        prompt = get_quality_check_prompt(document_content, document_type, profile_data)

        try:
            report = await analyze_offer(prompt)
            logger.info(f"Quality check for {document_type}: {report.get('quality_score', 0)}/10")
            return report
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quality report: {e}")
            return {"quality_score": 5, "recommendation": "REVIEW"}
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {"quality_score": 5, "recommendation": "REVIEW"}
