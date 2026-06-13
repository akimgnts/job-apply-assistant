import json
import logging
from openai import OpenAI
from app.config import config

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY)

async def call_openai(prompt: str, json_mode: bool = False) -> str:
    try:
        kwargs = {
            "model": config.OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
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
