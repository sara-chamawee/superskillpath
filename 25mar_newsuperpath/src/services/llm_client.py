"""LLM Client — wraps Google Gemini API for chat completions."""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_model_name = "gemini-2.5-flash"


def _get_client():
    """Lazy-init Gemini client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — using template responses")
        return None

    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized with model: %s", _model_name)
        return _client
    except Exception as e:
        logger.warning("Failed to init Gemini client: %s — using template responses", e)
        return None


def chat_completion(system_prompt: str, messages: list[dict], temperature: float = 0.7) -> Optional[str]:
    """Call Gemini chat completion. Returns None if not available."""
    client = _get_client()
    if client is None:
        return None

    try:
        from google.genai import types

        # Build contents: system instruction + conversation history
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

        response = client.models.generate_content(
            model=_model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=4096,
            ),
        )
        return response.text
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        return None


def is_available() -> bool:
    """Check if LLM is available."""
    return _get_client() is not None
