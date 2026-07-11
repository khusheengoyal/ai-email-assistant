"""
Builds a personalized writing-style profile from the user's own sent mail.

"Sufficient history" (MIN_SUBSTANTIVE_SENT_EMAILS below) gates everything: if
the user hasn't sent enough substantive mail, we never call the model to
guess a style -- we just report mode="fallback" and let app.py/classify.py
fall back to a selectable default tone (see fallback_tone.py). This module
only ever produces a profile from real writing samples, never a fabricated
one.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

from fetch_emails import extract_body_text
from groq_client import get_groq_client

logger = logging.getLogger(__name__)

# "Sufficient history" threshold (Requirement 2): at least this many
# substantive sent emails are required before we build a personalized
# writing-style profile. Below this, we fall back to a default tone.
MIN_SUBSTANTIVE_SENT_EMAILS = 5

# An email counts as "substantive" only if it has at least this many words
# after whitespace normalization -- short acknowledgements don't teach us
# anything about writing style.
MIN_SUBSTANTIVE_WORDS = 8

MODEL = "llama-3.3-70b-versatile"
PROFILE_CACHE_PATH = "writing_profile.json"
MAX_SAMPLES = 25
LOOKBACK_DAYS = 180

_SHORT_REPLY_BLOCKLIST = {
    "thanks", "thank you", "thanks!", "ok", "okay", "got it", "received",
    "sounds good", "noted", "will do", "perfect", "sure", "yes", "no",
    "great", "cool", "np", "no problem", "confirmed", "done",
}

STYLE_PROMPT_TEMPLATE = """You are analyzing a person's own sent emails to build a writing-style \
profile that will later guide an AI drafting replies on their behalf. Based ONLY on the writing \
samples below, describe (in 4-6 short bullet points) their typical: tone/formality, greeting \
style, sign-off style, sentence length/structure, and any distinctive phrases or habits. Do not \
invent details not evidenced by the samples. Respond with plain text bullet points only, no \
preamble.

Writing samples (most recent first, separated by "---"):
{samples}
"""


def _is_substantive(body_text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", body_text).strip()
    if not cleaned:
        return False

    normalized = cleaned.strip(".!? ").lower()
    if normalized in _SHORT_REPLY_BLOCKLIST:
        return False

    return len(cleaned.split()) >= MIN_SUBSTANTIVE_WORDS


def _list_sent_message_ids(service, lookback_days: int = LOOKBACK_DAYS, max_results: int = 100) -> list:
    """Cheap Gmail call: message IDs only, no bodies. Used as a fast staleness
    check before paying for a full per-message fetch."""
    results = service.users().messages().list(
        userId="me", q=f"in:sent newer_than:{lookback_days}d", maxResults=max_results
    ).execute()
    return [m["id"] for m in results.get("messages", [])]


def _fetch_sent_bodies(service, message_ids: list) -> list:
    bodies = []
    for message_id in message_ids:
        message = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        text = extract_body_text(message["payload"])
        if text:
            bodies.append(text.strip())

    return bodies


def get_substantive_sent_bodies(service) -> list:
    """Fetch recent sent mail and return only the substantive bodies."""
    message_ids = _list_sent_message_ids(service)
    return [body for body in _fetch_sent_bodies(service, message_ids) if _is_substantive(body)]


def has_sufficient_history(service) -> bool:
    return len(get_substantive_sent_bodies(service)) >= MIN_SUBSTANTIVE_SENT_EMAILS


def _load_cache():
    if not os.path.exists(PROFILE_CACHE_PATH):
        return None
    try:
        with open(PROFILE_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _save_cache(profile_text: str, sample_count: int, message_ids: list) -> None:
    with open(PROFILE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "profile": profile_text,
            "sample_count": sample_count,
            "message_ids": sorted(message_ids),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)


def _generate_profile(samples: list) -> str:
    client = get_groq_client()
    joined = "\n\n---\n\n".join(samples[:MAX_SAMPLES])
    prompt = STYLE_PROMPT_TEMPLATE.format(samples=joined[:12000])

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def get_style_profile(service, force_refresh: bool = False) -> dict:
    """
    Returns either:
      {"mode": "personalized", "profile": "<style description>", "sample_count": N}
      {"mode": "fallback", "sample_count": N}

    Re-evaluates sent-mail history on every call, so the mode switches
    automatically as history accumulates -- no code change or app restart
    required. Any Gmail/Groq failure degrades gracefully to fallback mode
    rather than crashing the caller.

    Cost note: a cheap id-only Gmail list call is used as the cache key, so a
    cache hit skips both the per-message body fetch and the Groq call --
    only a config/history change pays the full cost.
    """
    try:
        message_ids = _list_sent_message_ids(service)
    except Exception:
        logger.exception("Failed to list sent mail; falling back to default tone")
        return {"mode": "fallback", "sample_count": 0}

    cache = None if force_refresh else _load_cache()
    if cache and cache.get("message_ids") == sorted(message_ids) and cache.get("profile"):
        return {"mode": "personalized", "profile": cache["profile"], "sample_count": cache["sample_count"]}

    try:
        samples = [b for b in _fetch_sent_bodies(service, message_ids) if _is_substantive(b)]
    except Exception:
        logger.exception("Failed to fetch sent mail bodies; falling back to default tone")
        return {"mode": "fallback", "sample_count": 0}

    sample_count = len(samples)
    if sample_count < MIN_SUBSTANTIVE_SENT_EMAILS:
        return {"mode": "fallback", "sample_count": sample_count}

    try:
        profile_text = _generate_profile(samples)
    except Exception:
        logger.exception("Failed to generate writing-style profile; falling back to default tone")
        return {"mode": "fallback", "sample_count": sample_count}

    _save_cache(profile_text, sample_count, message_ids)
    return {"mode": "personalized", "profile": profile_text, "sample_count": sample_count}
