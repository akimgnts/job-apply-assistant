import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

logger.info(f"Template directory: {TEMPLATE_DIR}")
logger.info(f"Template directory exists: {TEMPLATE_DIR.exists()}")
if TEMPLATE_DIR.exists():
    logger.info(f"Available templates: {list(TEMPLATE_DIR.glob('*'))}")

template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR))
)

def get_output_path(application_id: int, document_type: str) -> Path:
    """Get file path for generated document."""
    output_dir = Path(Path(__file__).resolve().parent.parent.parent / "outputs")
    output_dir.mkdir(exist_ok=True, parents=True)
    return output_dir / f"app_{application_id}_{document_type}.html"

def get_template_debug_info() -> dict:
    """Get debug info about template directory."""
    available = []
    if TEMPLATE_DIR.exists():
        available = [f.name for f in TEMPLATE_DIR.glob("*") if f.is_file()]

    return {
        "template_dir": str(TEMPLATE_DIR),
        "template_dir_exists": TEMPLATE_DIR.exists(),
        "available_templates": available,
        "cwd": str(Path.cwd()),
    }

def render_cv(context: dict, template_name: str = "cv.html") -> str:
    """Render CV template."""
    template = template_env.get_template(template_name)
    return template.render(**context)

def render_letter(context: dict, template_name: str = "letter_master.html") -> str:
    """Render motivation letter template (LetterAgent V1)."""
    template = template_env.get_template(template_name)
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
