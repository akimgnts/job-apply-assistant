import logging
from app.services.openai_service import generate_cv_payload
from app.prompts.letter_prompt import get_letter_prompt

logger = logging.getLogger(__name__)

FORBIDDEN_PHRASES = [
    "depuis toujours passionné",
    "parcours atypique",
    "j'ai appris à",
    "je suis motivé par",
    "ma passion pour",
    "expert en",
    "leader",
    "dirigé une équipe",
    "mentoré",
    "piloté une équipe",
]


class LetterAgent:
    """Generate French cover letter (HTML).

    Philosophy:
    - Forward-looking (what can Akim bring?)
    - Not autobiographical
    - Not CV summary
    - Bridges offer understanding + CV
    """

    @staticmethod
    async def generate_letter_payload(
        offer: dict,
        positioning: str,
        gap_analysis: dict,
        cv_payload: dict = None,
    ) -> dict:
        """Generate letter payload (object + paragraphs + signature).

        Returns:
        {
            "object": "Candidature — ...",
            "paragraphs": ["...", "...", ...],
            "signature": "Akim Guentas"
        }
        """
        prompt = get_letter_prompt(offer, positioning, gap_analysis, cv_payload or {})

        try:
            result = await generate_cv_payload(prompt)

            # Validate
            validation = LetterAgent._validate_letter(result)
            if not validation["is_valid"]:
                logger.warning(f"Letter validation issues: {validation['issues']}")
                # Still use it, but log issues
            else:
                logger.info("Letter validation passed")

            logger.info(f"Letter generated: {len(result.get('paragraphs', []))} paragraphs")

            return result

        except Exception as e:
            logger.error(f"Letter generation failed: {e}")
            return LetterAgent._build_fallback_letter(offer)

    @staticmethod
    def _validate_letter(letter: dict) -> dict:
        """Validate letter for issues."""
        issues = []
        full_text = (letter.get("object", "") + " ".join(letter.get("paragraphs", [])))

        # Check language (French indicators)
        if "you" in full_text.lower() or "your" in full_text.lower():
            issues.append("English text detected (should be French)")

        # Check paragraph count
        para_count = len(letter.get("paragraphs", []))
        if para_count < 4 or para_count > 6:
            issues.append(f"Paragraph count {para_count} (should be 4-6)")

        # Check for forbidden phrases
        full_text_lower = full_text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in full_text_lower:
                issues.append(f"Forbidden phrase detected: '{phrase}'")

        # Check for None text
        if "None" in full_text:
            issues.append("'None' text found")

        # Check for exaggeration markers
        exaggeration_markers = ["monde", "leader", "expert", "dirigé", "mentoré"]
        for marker in exaggeration_markers:
            if marker in full_text_lower:
                # Only flag if it seems like a claim
                if "dirigé une" in full_text_lower or "mentoré des" in full_text_lower:
                    issues.append(f"Potential exaggeration: '{marker}'")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def _build_fallback_letter(offer: dict) -> dict:
        """Safe fallback letter when generation fails."""
        company = offer.get("company", "votre entreprise")
        job_title = offer.get("job_title", "ce poste")

        return {
            "object": f"Candidature — {job_title} — {company}",
            "paragraphs": [
                f"Votre recherche d'un candidat pour le poste de {job_title} suscite mon intérêt "
                f"au regard de mes compétences en analyse de données, reporting et automatisation.",
                f"Mon expérience en consolidation de données multi-sources, création de tableaux de bord "
                f"et coordination transversale me permettrait de contribuer aux missions que vous portez chez {company}.",
                f"J'ai développé une approche centrée sur l'accessibilité de l'information et la simplification "
                f"des processus opérationnels, que je pourrais mettre au service de vos projets.",
                f"Je souhaite vous rencontrer afin de discuter de vos enjeux actuels et de la manière dont "
                f"mes compétences pourraient contribuer à leur résolution.",
            ],
            "signature": "Akim Guentas",
        }
