"""AI Suggest Content Service — recommends learning content for Skill Path Templates."""

import json
import logging
import re
import time
from typing import Optional

from src.services import llm_client

logger = logging.getLogger(__name__)

MAX_CHAT_HISTORY = 10
MAX_EXISTING_ITEMS = 20


def suggest_content(
    message: str,
    skill_name: str = "",
    description: str = "",
    badge_levels: list[dict] | None = None,
    existing_items: list[dict] | None = None,
    chat_history: list[dict] | None = None,
    stream: bool = False,
):
    """Generate AI content suggestions.

    Returns a generator of SSE events if stream=True, else a dict.
    """
    if not message or not message.strip():
        raise ValueError("message is required")

    badge_levels = badge_levels or []
    existing_items = (existing_items or [])[:MAX_EXISTING_ITEMS]
    chat_history = (chat_history or [])[-MAX_CHAT_HISTORY:]

    system_prompt = _build_system_prompt(skill_name, description, badge_levels, existing_items)

    messages = []
    for msg in chat_history:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": message})

    if stream:
        return _stream_response(system_prompt, messages)
    else:
        return _sync_response(system_prompt, messages)


def _build_system_prompt(
    skill_name: str,
    description: str,
    badge_levels: list[dict],
    existing_items: list[dict],
) -> str:
    levels_text = ""
    if badge_levels:
        levels_text = "Badge Levels:\n" + "\n".join(
            f"- Level {bl.get('order', '?')}: {bl.get('name', '')}" for bl in badge_levels
        )

    items_text = ""
    if existing_items:
        items_text = "Existing Items:\n" + "\n".join(
            f"- {it.get('title', '')} ({it.get('content_type', '')})" for it in existing_items
        )

    return f"""คุณคือ AI ที่ช่วย Admin แนะนำเนื้อหาการเรียนรู้สำหรับ Skill Path Template

ทักษะ: {skill_name}
คำอธิบาย: {description}
{levels_text}
{items_text}

ตอบเป็นภาษาไทย ให้คำแนะนำที่เป็นประโยชน์
ถ้าแนะนำเนื้อหา ให้แนบ JSON block ในรูปแบบ:
```json
[{{"title": "...", "content_type": "material|quiz|todo|simulation", "learning_type": "formal|social|experiential", "estimated_minutes": 60, "description": "..."}}]
```
ใส่ JSON block ไว้ท้ายข้อความเสมอ"""


def _extract_suggestions(text: str) -> tuple[str, list[dict]]:
    """Extract JSON suggestion cards from AI response text."""
    suggestions = []
    clean_text = text

    # Find JSON code blocks
    pattern = r'```json\s*\n?(.*?)\n?\s*```'
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                suggestions.extend(parsed)
            elif isinstance(parsed, dict):
                suggestions.append(parsed)
        except json.JSONDecodeError:
            pass

    # Remove JSON blocks from display text
    clean_text = re.sub(pattern, '', text, flags=re.DOTALL).strip()

    return clean_text, suggestions


def _stream_response(system_prompt: str, messages: list[dict]):
    """Generator that yields SSE events."""
    if not llm_client.is_available():
        clean = "ขออภัย ระบบ AI ไม่พร้อมใช้งานในขณะนี้ กรุณาลองใหม่ภายหลัง"
        yield f"data: {json.dumps({'text': clean, 'done': False})}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True, 'suggestions': [], 'clean_text': clean})}\n\n"
        return

    try:
        from google import genai
        from google.genai import types

        client = llm_client._get_client()
        contents = [
            types.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[types.Part(text=m["content"])],
            )
            for m in messages
        ]

        response = client.models.generate_content_stream(
            model=llm_client._model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )

        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield f"data: {json.dumps({'text': chunk.text, 'done': False})}\n\n"

        clean_text, suggestions = _extract_suggestions(full_text)
        yield f"data: {json.dumps({'text': '', 'done': True, 'suggestions': suggestions, 'clean_text': clean_text})}\n\n"

    except Exception as e:
        logger.error("AI suggest stream error: %s", e)
        error_msg = "ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อ AI กรุณาลองใหม่"
        yield f"data: {json.dumps({'text': error_msg, 'done': True, 'suggestions': [], 'clean_text': error_msg})}\n\n"


def _sync_response(system_prompt: str, messages: list[dict]) -> dict:
    """Non-streaming response."""
    result_text = llm_client.chat_completion(system_prompt, messages)
    if result_text is None:
        return {
            "clean_text": "ระบบ AI ไม่พร้อมใช้งาน",
            "suggestions": [],
        }

    clean_text, suggestions = _extract_suggestions(result_text)
    return {
        "clean_text": clean_text,
        "suggestions": suggestions,
    }
