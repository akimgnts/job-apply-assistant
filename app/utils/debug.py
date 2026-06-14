import re
import traceback
from typing import Optional

SECRETS_TO_MASK = [
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "DATABASE_URL",
    "sk-proj-",  # OpenAI key prefix
]


def mask_secrets(text: str) -> str:
    """Mask sensitive credentials in error messages."""
    masked = text

    masked = re.sub(
        r"(OPENAI_API_KEY\s*=\s*)[^\s\n]+",
        r"\1***MASKED***",
        masked,
    )
    masked = re.sub(
        r"(TELEGRAM_BOT_TOKEN\s*=\s*)[^\s\n]+",
        r"\1***MASKED***",
        masked,
    )
    masked = re.sub(
        r"(DATABASE_URL\s*=\s*)[^\s\n]+",
        r"\1***MASKED***",
        masked,
    )
    masked = re.sub(
        r"(sk-proj-)[^\s\n]+",
        r"sk-proj-***MASKED***",
        masked,
    )
    masked = re.sub(
        r"(://)([^:]+):([^@]+)(@)",
        r"\1\2:***PASSWORD***\4",
        masked,
    )

    return masked


def format_exception_for_telegram(
    error: Exception,
    context: Optional[dict] = None,
    extra_debug: Optional[dict] = None,
) -> str:
    """Format exception for Telegram with debug info.

    Args:
        error: The exception that occurred
        context: Optional context dict (e.g., user_id, command, etc.)
        extra_debug: Optional debug info (e.g., template_dir, available_templates)

    Returns:
        Formatted string ready for Telegram (masked secrets)
    """
    lines = []

    lines.append("❌ DEBUG ERROR")
    lines.append("")

    lines.append("**Type:**")
    lines.append(f"`{type(error).__name__}`")
    lines.append("")

    lines.append("**Message:**")
    error_msg = str(error) or "(no message)"
    lines.append(f"`{error_msg}`")
    lines.append("")

    if context:
        lines.append("**Context:**")
        for key, value in context.items():
            safe_value = str(value)[:100]
            lines.append(f"`{key}={safe_value}`")
        lines.append("")

    if extra_debug:
        lines.append("**Debug Info:**")
        for key, value in extra_debug.items():
            if isinstance(value, (list, dict)):
                safe_value = str(value)[:150]
            else:
                safe_value = str(value)[:150]
            lines.append(f"`{key}={safe_value}`")
        lines.append("")

    lines.append("**Trace:**")
    tb_lines = traceback.format_exc().split("\n")
    last_20_lines = tb_lines[-20:]
    trace_text = "\n".join(last_20_lines)
    lines.append(f"`{trace_text}`")

    message = "\n".join(lines)
    message = mask_secrets(message)

    return message


def split_telegram_message(text: str, max_length: int = 3500) -> list[str]:
    """Split message for Telegram's character limit.

    Telegram message limit is 4096 characters.
    Use 3500 to be safe with formatting.

    Args:
        text: Message text to split
        max_length: Maximum length per message

    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    for line in text.split("\n"):
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line

            while len(current_chunk) > max_length:
                chunks.append(current_chunk[:max_length])
                current_chunk = current_chunk[max_length:]
        else:
            if current_chunk:
                current_chunk += "\n"
            current_chunk += line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
