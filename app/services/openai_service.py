import json
import logging
import unicodedata
from openai import AsyncOpenAI
from app.config import config

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


def _normalize_text(text: str) -> str:
    """Remove accents and normalize Unicode for OpenAI API compatibility.

    Fixes: UnicodeEncodeError when prompt contains French accents.
    """
    if not text:
        return text
    # Decompose accented characters and remove combining marks
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

async def call_openai(prompt: str, json_mode: bool = False) -> str:
    try:
        # Normalize Unicode to prevent encoding errors (e.g., French accents)
        normalized_prompt = _normalize_text(prompt)

        kwargs = {
            "model": config.OPENAI_MODEL,
            "messages": [{"role": "user", "content": normalized_prompt}],
            "temperature": 0.7,
            "timeout": config.OPENAI_TIMEOUT_SECONDS,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise

async def analyze_offer(prompt: str) -> dict:
    """Call OpenAI for structured job analysis."""
    result = await call_openai(prompt, json_mode=True)
    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {result}")
        raise

async def generate_text(prompt: str) -> str:
    """Call OpenAI for unstructured text generation."""
    return await call_openai(prompt, json_mode=False)

async def generate_cv_payload(prompt: str) -> dict:
    """Call OpenAI for structured CV payload generation."""
    result = await call_openai(prompt, json_mode=True)
    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse CV payload JSON: {result}")
        raise
