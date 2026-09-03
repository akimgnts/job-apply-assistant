"""Phase 6: Generate outreach message using LLM."""

from app.services.openai_service import call_openai
from app.services.outreach_context_builder import OutreachContext
import re
import logging

logger = logging.getLogger(__name__)


class OutreachMessageGenerator:
    @staticmethod
    async def generate(context: OutreachContext) -> dict:
        """Generate message from context. Returns {subject, message, evidence_ids_used}."""

        prompt = f"""You are writing a professional outreach email to a hiring contact.

TO: {context.contact_name}, {context.contact_role} at {context.company_name}
FROM: {context.candidate_info['name']}

CANDIDATE'S VERIFIED SKILLS (use ONLY these):"""

        for skill in context.verified_skills:
            prompt += f"\n- {skill.skill}: \"{skill.evidence_snippet}\""

        if context.gap_skills:
            prompt += f"\n\nCANDIDATE'S GAPS (mention transparently as 'learning' or 'interested in'):\n"
            for gap in context.gap_skills[:3]:
                prompt += f"- {gap}\n"

        prompt += """
RULES:
1. NO skills not listed above.
2. NO invented metrics, projects, or years.
3. NO mentioning gaps as current expertise.
4. Keep to 150-200 words.
5. Professional but warm tone.

Write:
SUBJECT: <one line, under 60 chars>
BODY:
<email body>"""

        response = await call_openai(prompt, json_mode=False)

        # Parse response
        subject = ""
        body = ""
        if "SUBJECT:" in response:
            parts = response.split("BODY:")
            subject = parts[0].split("SUBJECT:")[-1].strip()
            body = parts[-1].strip() if len(parts) > 1 else ""

        evidence_ids_used = [s.evidence_id for s in context.verified_skills]

        return {
            "subject": subject,
            "message": body,
            "evidence_ids_used": evidence_ids_used
        }
