import logging
from sqlalchemy.orm import Session
from app.database.models import ProfileBlock

logger = logging.getLogger(__name__)

class MatchingAgent:
    """Enhance analysis with detailed matching logic."""

    @staticmethod
    def enrich_analysis(analysis: dict, db: Session) -> dict:
        """
        Enrich analysis with profile block details.
        Validate that suggested blocks exist and are valid.
        """
        profile_blocks = db.query(ProfileBlock).all()
        block_map = {b.id: b for b in profile_blocks}

        to_use = analysis.get("profile_blocks_to_use") or []
        to_avoid = analysis.get("profile_blocks_to_avoid") or []

        valid_to_use = [bid for bid in to_use if bid in block_map] if to_use else []
        valid_to_avoid = [bid for bid in to_avoid if bid in block_map] if to_avoid else []

        analysis["profile_blocks_to_use"] = valid_to_use
        analysis["profile_blocks_to_avoid"] = valid_to_avoid

        if not valid_to_use:
            logger.info("No selected profile blocks found; continuing with Master CV adaptation.")

        logger.info(
            f"Enriched analysis: {len(valid_to_use)} blocks to use, "
            f"{len(valid_to_avoid)} blocks to avoid"
        )

        return analysis

    @staticmethod
    def get_selected_blocks(db: Session, block_ids: list[int]) -> list[dict]:
        """Get detailed profile blocks for document generation."""
        if not block_ids:
            return []
        blocks = db.query(ProfileBlock).filter(ProfileBlock.id.in_(block_ids)).all()
        return [
            {
                "id": b.id,
                "title": b.title,
                "content": b.content,
                "category": b.category.value,
                "tags": b.tags,
            }
            for b in blocks
        ]
