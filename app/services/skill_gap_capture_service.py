import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.database.models import SkillGapEvent, ProfileBlock
from app.services.skill_gap_aggregation_service import SkillGapAggregationService

logger = logging.getLogger(__name__)


class SkillGapCaptureService:
    """Capture skill gaps from job analysis."""

    @staticmethod
    def extract_skills_from_analysis(analysis: Dict[str, Any]) -> tuple[List[str], List[str], List[str]]:
        """
        Extract required skills, soft skills, and ATS keywords from analysis.
        Returns: (required_skills, soft_skills, ats_keywords)
        """
        required = analysis.get("required_skills", [])
        soft = analysis.get("soft_skills", [])
        ats = analysis.get("ats_keywords", [])

        return required, soft, ats

    @staticmethod
    def get_candidate_skills(db: Session) -> Dict[str, bool]:
        """
        Build a dictionary of skills the candidate possesses.
        Returns: {skill_name: True}
        """
        blocks = db.query(ProfileBlock).all()
        skills = {}

        for block in blocks:
            # Add title as searchable skill
            skill_name = block.title.lower()
            skills[skill_name] = True

            # Add tags as skills
            if block.tags:
                for tag in block.tags:
                    if isinstance(tag, str):
                        skills[tag.lower()] = True

            # Extract skills from content (basic approach)
            # Could be enhanced with NLP later
            if block.category.value == "skill" or block.category.value == "tool":
                skills[skill_name] = True

        return skills

    @staticmethod
    def normalize_skill_name(skill: str) -> str:
        """Normalize skill name for comparison."""
        return skill.lower().strip()

    @staticmethod
    def is_skill_present(
        skill_name: str,
        candidate_skills: Dict[str, bool],
    ) -> bool:
        """Check if candidate has the skill."""
        normalized = SkillGapCaptureService.normalize_skill_name(skill_name)
        return normalized in candidate_skills

    @staticmethod
    def capture_gaps_from_analysis(
        db: Session,
        telegram_user_id: str,
        application_id: int,
        offer_title: str,
        company: str,
        role_family: str,
        positioning: str,
        analysis: Dict[str, Any],
    ) -> int:
        """
        Capture all skill gaps from a job analysis.
        Returns number of events recorded.
        """
        required_skills, soft_skills, ats_keywords = SkillGapCaptureService.extract_skills_from_analysis(
            analysis
        )
        candidate_skills = SkillGapCaptureService.get_candidate_skills(db)

        event_count = 0

        # Capture required skills (high importance)
        for skill in required_skills:
            if not skill or len(skill) == 0:
                continue

            present = SkillGapCaptureService.is_skill_present(skill, candidate_skills)
            SkillGapAggregationService.record_skill_gap(
                db=db,
                telegram_user_id=telegram_user_id,
                application_id=application_id,
                offer_title=offer_title,
                company=company,
                role_family=role_family,
                positioning=positioning,
                skill_name=skill,
                skill_category="required",
                required=True,
                present=present,
                importance_score=9,  # High importance
                confidence=9,        # High confidence
            )
            event_count += 1

        # Capture soft skills (medium importance)
        for skill in soft_skills:
            if not skill or len(skill) == 0:
                continue

            present = SkillGapCaptureService.is_skill_present(skill, candidate_skills)
            SkillGapAggregationService.record_skill_gap(
                db=db,
                telegram_user_id=telegram_user_id,
                application_id=application_id,
                offer_title=offer_title,
                company=company,
                role_family=role_family,
                positioning=positioning,
                skill_name=skill,
                skill_category="soft_skill",
                required=True,
                present=present,
                importance_score=7,  # Medium importance
                confidence=8,
            )
            event_count += 1

        # Capture ATS keywords (medium importance, lower confidence)
        for skill in ats_keywords:
            if not skill or len(skill) == 0:
                continue

            present = SkillGapCaptureService.is_skill_present(skill, candidate_skills)
            SkillGapAggregationService.record_skill_gap(
                db=db,
                telegram_user_id=telegram_user_id,
                application_id=application_id,
                offer_title=offer_title,
                company=company,
                role_family=role_family,
                positioning=positioning,
                skill_name=skill,
                skill_category="ats_keyword",
                required=True,
                present=present,
                importance_score=6,  # Medium importance
                confidence=6,        # Lower confidence
            )
            event_count += 1

        logger.info(f"Captured {event_count} skill gap events for application {application_id}")
        return event_count
