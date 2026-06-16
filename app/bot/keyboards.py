"""Telegram bot keyboard layouts (InlineKeyboardMarkup).

All menus as InlineKeyboard for button-based navigation.
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def home_menu() -> InlineKeyboardMarkup:
    """Home menu with main options."""
    keyboard = [
        [InlineKeyboardButton("🔍 Analyser une offre", callback_data="analyze_offer")],
        [InlineKeyboardButton("📂 Mes candidatures", callback_data="my_applications")],
        [InlineKeyboardButton("📄 Mon Master CV", callback_data="view_master_cv")],
        [InlineKeyboardButton("⚙️ Mon profil", callback_data="view_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_home() -> InlineKeyboardMarkup:
    """Back to home button."""
    keyboard = [[InlineKeyboardButton("🏠 Accueil", callback_data="home")]]
    return InlineKeyboardMarkup(keyboard)


def back_home_and_action(action_label: str, action_callback: str) -> InlineKeyboardMarkup:
    """Two buttons: Action + Back home."""
    keyboard = [
        [InlineKeyboardButton(action_label, callback_data=action_callback)],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def offer_extracted_menu() -> InlineKeyboardMarkup:
    """Menu after extracting offer: analyze, save, back."""
    keyboard = [
        [InlineKeyboardButton("📊 Voir le match", callback_data="view_match")],
        [InlineKeyboardButton("📄 Générer CV", callback_data="gen_cv")],
        [InlineKeyboardButton("✉️ Générer lettre", callback_data="gen_letter")],
        [InlineKeyboardButton("📧 Générer mail", callback_data="gen_mail")],
        [InlineKeyboardButton("🚀 Tout générer", callback_data="gen_all")],
        [InlineKeyboardButton("💾 Sauvegarder", callback_data="save_application")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def match_view_menu() -> InlineKeyboardMarkup:
    """Menu in match view: generate docs or back."""
    keyboard = [
        [InlineKeyboardButton("📄 CV", callback_data="gen_cv")],
        [InlineKeyboardButton("✉️ Lettre", callback_data="gen_letter")],
        [InlineKeyboardButton("📧 Mail", callback_data="gen_mail")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def application_detail_menu() -> InlineKeyboardMarkup:
    """Menu for viewing saved application details."""
    keyboard = [
        [InlineKeyboardButton("📊 Match", callback_data="view_match")],
        [InlineKeyboardButton("📄 CV", callback_data="gen_cv")],
        [InlineKeyboardButton("✉️ Lettre", callback_data="gen_letter")],
        [InlineKeyboardButton("📧 Mail", callback_data="gen_mail")],
        [InlineKeyboardButton("🗑 Supprimer", callback_data="delete_application")],
        [InlineKeyboardButton("📂 Mes candidatures", callback_data="my_applications")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def save_or_regenerate_menu() -> InlineKeyboardMarkup:
    """After documents generated: save or regenerate."""
    keyboard = [
        [InlineKeyboardButton("💾 Sauvegarder", callback_data="save_application")],
        [InlineKeyboardButton("♻️ Régénérer", callback_data="gen_all")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def profile_menu() -> InlineKeyboardMarkup:
    """Profile view menu."""
    keyboard = [
        [InlineKeyboardButton("✏️ Modifier email", callback_data="edit_email")],
        [InlineKeyboardButton("✏️ Modifier téléphone", callback_data="edit_phone")],
        [InlineKeyboardButton("✏️ Modifier LinkedIn", callback_data="edit_linkedin")],
        [InlineKeyboardButton("✏️ Modifier portfolio", callback_data="edit_portfolio")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def master_cv_menu() -> InlineKeyboardMarkup:
    """Master CV view menu."""
    keyboard = [
        [InlineKeyboardButton("📥 Télécharger PDF", callback_data="download_cv_pdf")],
        [InlineKeyboardButton("📥 Télécharger HTML", callback_data="download_cv_html")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)
