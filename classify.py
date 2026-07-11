import json

from fallback_tone import DEFAULT_TONE, get_tone_instruction
from groq_client import get_groq_client

MODEL = "llama-3.3-70b-versatile"
CLASSIFICATION_TEMPERATURE = 0.2

PROMPT_TEMPLATE = """You are an email triage assistant. Given the email below, respond with ONLY a JSON object (no markdown code fences, no extra commentary) with exactly these fields:

{{
  "category": one of "Urgent", "Needs Reply", "FYI", "Newsletter",
  "priority_score": integer 1-10,
  "priority_reason": "one-line reason for the score",
  "summary": "1-2 sentence summary",
  "action_items": [{{"task": "...", "deadline": "YYYY-MM-DD or null"}}],
  "suggested_reply": "a draft reply, or empty string if no reply is needed"
}}

When writing "suggested_reply", follow this style guidance (do not mention it in the reply):
{style_guidance}

From: {sender}
Subject: {subject}
Body:
{body}
"""

DEFAULT_STYLE_GUIDANCE = get_tone_instruction(DEFAULT_TONE)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json"):]
    return text.strip()


def classify_email(email: dict, style_guidance: str = DEFAULT_STYLE_GUIDANCE) -> dict:
    client = get_groq_client()
    prompt = PROMPT_TEMPLATE.format(
        sender=email["from"],
        subject=email["subject"],
        body=email["body_text"][:6000],
        style_guidance=style_guidance,
    )

    response = client.chat.completions.create(
        model=MODEL,
        temperature=CLASSIFICATION_TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content
    cleaned = _strip_code_fences(raw)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse model response as JSON",
            "raw_response": raw,
        }
