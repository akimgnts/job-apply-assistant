"""Phase 6: Orchestrate outreach generation pipeline."""

from sqlalchemy.orm import Session
from app.database.models import OutreachDraft
from app.services.outreach_context_builder import OutreachContextBuilder
from app.services.outreach_message_generator import OutreachMessageGenerator
from app.services.outreach_grounding_validator import GroundingValidator
import logging

logger = logging.getLogger(__name__)


class OutreachDraftService:
    @staticmethod
    async def create_draft(
        db: Session,
        company_id: int,
        contact_id: int,
        job_offer_ids: list[int],
        channel: str = "email"
    ) -> OutreachDraft:
        """Full pipeline: context → generate → validate → persist."""

        # Step 1: Build context
        context = OutreachContextBuilder.build(db, company_id, contact_id, job_offer_ids)
        logger.info(f"Context built: {len(context.verified_skills)} skills, {len(context.gap_skills)} gaps")

        # Step 2: Generate message
        generated = await OutreachMessageGenerator.generate(context)
        message = generated["message"]
        subject = generated["subject"]
        evidence_ids = generated.get("evidence_ids_used", [])

        logger.info(f"Message generated: {len(message)} chars")

        # Step 3: Validate grounding
        grounding = GroundingValidator.validate(message, evidence_ids, context.gap_skills)
        logger.info(f"Grounding check: grounded={grounding['grounded']}, claims={len(grounding.get('unsupported_claims', []))}")

        # Step 4: Persist
        status = "READY" if grounding["grounded"] else "NEEDS_REVIEW"

        draft = OutreachDraft(
            company_id=company_id,
            contact_id=contact_id,
            job_offer_id=job_offer_ids[0] if job_offer_ids else None,
            channel=channel,
            subject_line=subject,
            message_text=message,
            evidence_ids=evidence_ids,
            grounding_result=grounding,
            status=status
        )

        db.add(draft)
        db.commit()

        logger.info(f"Draft created: ID={draft.id}, status={status}")
        return draft

    @staticmethod
    def list_by_status(db: Session, status: str) -> list[OutreachDraft]:
        return db.query(OutreachDraft).filter(OutreachDraft.status == status).all()
