"""Format Telegram messages with clean, structured HTML markup."""

from telegram.constants import ParseMode


def format_analysis_message(
    job_title: str,
    company: str,
    positioning: str,
    match_score: int,
    strengths: list,
    weaknesses: list,
) -> tuple[str, str]:
    """Format analysis result as structured HTML message.

    Returns:
        (message_text, parse_mode)
    """
    strengths_text = "\n".join([f"  • {s}" for s in strengths[:3]]) if strengths else "  Aucun point relevé"
    weaknesses_text = "\n".join([f"  • {w}" for w in weaknesses[:3]]) if weaknesses else "  Tous les points couverts"

    text = f"""<b>📊 Offre analysée</b>

<b>Poste</b>
{job_title}

<b>Entreprise</b>
{company}

━━━━━━━━━━━━━━━━━━━━━

<b>Positionnement</b>
<i>{positioning}</i>

<b>Score de match</b>
<code>{match_score} / 10</code>

━━━━━━━━━━━━━━━━━━━━━

<b>✅ Points forts</b>
{strengths_text}

<b>⚠️  Points à renforcer</b>
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
    """Format detailed match analysis as structured HTML.

    Returns:
        (message_text, parse_mode)
    """
    strengths_text = "\n".join([f"  ✓ {s}" for s in strengths[:4]]) if strengths else "  Aucun point relevé"
    weaknesses_text = "\n".join([f"  ✗ {w}" for w in weaknesses[:4]]) if weaknesses else "  Pas de points faibles"
    missing_text = "\n".join([f"  • {m}" for m in missing_skills[:4]]) if missing_skills else "  Tout est couvert"

    score_bar = "████████░░" if match_score >= 8 else "██████░░░░" if match_score >= 6 else "████░░░░░░" if match_score >= 4 else "██░░░░░░░░"

    text = f"""<b>🔍 Analyse détaillée</b>

<b>{company}</b>
{job_title}

━━━━━━━━━━━━━━━━━━━━━

<b>Match Score</b>
<code>{match_score}/10</code> {score_bar}

<b>Angle de candidature</b>
<i>{positioning}</i>

━━━━━━━━━━━━━━━━━━━━━

<b>✅ Atouts</b>
{strengths_text}

<b>⚠️  Défis</b>
{weaknesses_text}

<b>📚 À développer</b>
{missing_text}"""

    return (text, ParseMode.HTML)


def format_applications_list_message(applications: list) -> tuple[str, str]:
    """Format list of saved applications with clean structure.

    Args:
        applications: List of Application objects

    Returns:
        (message_text, parse_mode)
    """
    if not applications:
        return ("<b>📭 Aucune candidature sauvegardée</b>\n\nEnvoie une offre pour commencer.", ParseMode.HTML)

    lines = ["<b>📋 Mes candidatures</b>\n"]

    for i, app in enumerate(applications, 1):
        positioning = app.recommended_angle or "Non défini"
        match = app.match_score or "—"

        lines.append(
            f"\n<b>{i}. {app.company}</b>\n"
            f"   Poste: {app.job_title}\n"
            f"   Angle: <i>{positioning}</i>\n"
            f"   Match: <code>{match}/10</code>"
        )

    lines.append("\n\n<i>Sélectionne une candidature pour voir les détails</i>")
    return ("\n".join(lines), ParseMode.HTML)


def format_home_message() -> tuple[str, str]:
    """Format home menu message with clear hierarchy.

    Returns:
        (message_text, parse_mode)
    """
    text = """<b>📌 Job Apply Assistant</b>

<i>Analyse tes offres. Génère CV, lettre, mail.</i>

━━━━━━━━━━━━━━━━━━━━━

<b>Que veux-tu faire?</b>

Use les boutons ci-dessous pour naviguer."""

    return (text, ParseMode.HTML)


def format_profile_message(
    name: str,
    location: str,
    email: str,
    phone: str,
    linkedin: str,
    github: str,
) -> tuple[str, str]:
    """Format profile view with structured information.

    Returns:
        (message_text, parse_mode)
    """
    linkedin_link = f"<a href='https://linkedin.com/in/{linkedin}'>View profile</a>" if linkedin else "—"
    github_link = f"<a href='https://github.com/{github}'>@{github}</a>" if github else "—"

    text = f"""<b>👤 Mon profil</b>

━━━━━━━━━━━━━━━━━━━━━

<b>Identité</b>
Nom: <b>{name or "—"}</b>
Localisation: {location or "—"}

<b>Contact</b>
Email: <code>{email or "—"}</code>
Téléphone: {phone or "—"}

<b>Réseaux</b>
LinkedIn: {linkedin_link}
GitHub: {github_link}

━━━━━━━━━━━━━━━━━━━━━"""

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
