import logging
import json
from sqlalchemy.orm import Session
from app.services.openai_service import analyze_offer
from app.prompts.analysis_prompt import get_analysis_prompt
from app.database.models import ProfileBlock

logger = logging.getLogger(__name__)

class AnalysisAgent:
    """Analyze job offer and match with candidate profile."""

    @staticmethod
    async def analyze(db: Session, job_offer: str) -> dict:
        """
        Analyze job offer using OpenAI.
        Returns structured analysis JSON.
        """
        profile_blocks = db.query(ProfileBlock).order_by(ProfileBlock.priority.desc()).all()
        profile_data = [
            {
                "id": b.id,
                "title": b.title,
                "content": b.content,
                "category": b.category.value,
                "tags": b.tags,
                "truth_level": b.truth_level.value,
            }
            for b in profile_blocks
        ]

        prompt = get_analysis_prompt(job_offer, profile_data)

        try:
            analysis = await analyze_offer(prompt)
            logger.info(f"Analysis completed for job: {analysis.get('job_title')}")
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis: {e}")
            raise
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
