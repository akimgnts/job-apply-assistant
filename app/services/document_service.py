import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.config import config

logger = logging.getLogger(__name__)

template_env = Environment(
    loader=FileSystemLoader(config.PROJECT_ROOT / "app" / "templates")
)

def get_output_path(application_id: int, document_type: str) -> Path:
    """Get file path for generated document."""
    output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)
    return output_dir / f"app_{application_id}_{document_type}.html"

def render_cv(context: dict) -> str:
    """Render CV template."""
    template = template_env.get_template("cv.html")
    return template.render(**context)

def render_letter(context: dict) -> str:
    """Render motivation letter template."""
    template = template_env.get_template("letter.html")
    return template.render(**context)

def render_mail(context: dict) -> str:
    """Render email template."""
    template = template_env.get_template("mail.txt")
    return template.render(**context)

def save_document(content: str, filepath: Path) -> str:
    """Save document to file and return path."""
    try:
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Document saved: {filepath}")
        return str(filepath)
    except Exception as e:
        logger.error(f"Error saving document: {e}")
        raise
