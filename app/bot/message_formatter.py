"""Format Telegram messages with clean HTML markup.

Replaces emoji-heavy formatting with professional HTML.
"""

from telegram.constants import ParseMode


def format_analysis_message(
    job_title: str,
    company: str,
    positioning: str,
    match_score: int,
    strengths: list,
    weaknesses: list,
) -> tuple[str, str]:
    """Format analysis result as professional HTML message.

    Returns:
        (message_text, parse_mode)
    """
    strengths_text = "\n".join([f"• {s}" for s in strengths[:3]])
    weaknesses_text = "\n".join([f"• {w}" for w in weaknesses[:3]])

    text = f"""<b>Offre analysée</b>

<b>Poste</b>
{job_title}

<b>Entreprise</b>
{company}

<b>Positionnement recommandé</b>
<i>{positioning}</i>

<b>Match</b>
<code>{match_score}/10</code>

<b>Points forts</b>
{strengths_text}

<b>Points à renforcer</b>
{weaknesses_text}"""

    return (text, ParseMode.HTML)


def format_match_detail_message(
    company: str,
    job_title: str,
    positioning: str,
    match_score: int,
    strengths: list,
    weaknesses: list,
    missing_skills: list,
) -> tuple[str, str]:
    """Format detailed match analysis as professional HTML.

    Returns:
        (message_text, parse_mode)
    """
    strengths_text = "\n".join([f"• {s}" for s in strengths[:4]])
    weaknesses_text = "\n".join([f"• {w}" for w in weaknesses[:4]])
    missing_text = "\n".join([f"• {m}" for m in missing_skills[:4]])

    text = f"""<b>Analyse détaillée du match</b>

<b>Entreprise</b>
{company}

<b>Poste</b>
{job_title}

<b>Score</b>
<code>{match_score}/10</code>

<b>Positionnement</b>
<i>{positioning}</i>

<b>Points forts</b>
{strengths_text}

<b>Points à renforcer</b>
{weaknesses_text}

<b>Compétences manquantes</b>
{missing_text}"""

    return (text, ParseMode.HTML)


def format_applications_list_message(applications: list) -> tuple[str, str]:
    """Format list of saved applications.

    Args:
        applications: List of Application objects

    Returns:
        (message_text, parse_mode)
    """
    if not applications:
        return ("<b>Aucune candidature sauvegardée</b>", ParseMode.HTML)

    lines = ["<b>Mes candidatures récentes</b>\n"]

    for i, app in enumerate(applications, 1):
        positioning = app.recommended_angle or "Non défini"
        match = app.match_score or "N/A"
        lines.append(
            f"{i}. <b>{app.company}</b> — {app.job_title}\n"
            f"   Positionnement: <i>{positioning}</i>\n"
            f"   Match: <code>{match}/10</code>\n"
        )

    return ("\n".join(lines), ParseMode.HTML)


def format_home_message() -> tuple[str, str]:
    """Format home menu message.

    Returns:
        (message_text, parse_mode)
    """
    text = "<b>Job Apply Assistant</b>\n\nQue veux-tu faire?"

    return (text, ParseMode.HTML)


def format_profile_message(
    name: str,
    location: str,
    email: str,
    phone: str,
    linkedin: str,
    github: str,
) -> tuple[str, str]:
    """Format profile view message.

    Returns:
        (message_text, parse_mode)
    """
    text = f"""<b>Mon profil</b>

<b>Nom</b>
{name or "Non défini"}

<b>Localisation</b>
{location or "Non défini"}

<b>Email</b>
<code>{email or "Non défini"}</code>

<b>Téléphone</b>
{phone or "Non défini"}

<b>LinkedIn</b>
{linkedin or "Non défini"}

<b>GitHub</b>
{github or "Non défini"}"""

    return (text, ParseMode.HTML)


def format_document_generated_message(document_type: str) -> tuple[str, str]:
    """Format document generation success message.

    Args:
        document_type: "cv", "letter", or "mail"

    Returns:
        (message_text, parse_mode)
    """
    messages = {
        "cv": "<b>CV généré</b>",
        "letter": "<b>Lettre générée</b>",
        "mail": "<b>Mail généré</b>",
    }

    text = messages.get(document_type.lower(), "<b>Document généré</b>")

    return (text, ParseMode.HTML)
