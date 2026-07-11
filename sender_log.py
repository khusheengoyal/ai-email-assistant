import json
import os
from datetime import datetime, timedelta, timezone

LOG_PATH = "sender_log.json"


def _load_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r") as f:
        return json.load(f)


def _save_log(entries):
    with open(LOG_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def record_email(email_id: str, sender: str, subject: str, category: str):
    entries = _load_log()

    if any(e["message_id"] == email_id for e in entries):
        return

    entries.append({
        "message_id": email_id,
        "sender": sender,
        "subject": subject,
        "category": category,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save_log(entries)


def count_from_sender(sender: str, days: int = 7) -> int:
    entries = _load_log()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    return sum(
        1 for e in entries
        if e["sender"] == sender and datetime.fromisoformat(e["timestamp"]) >= cutoff
    )
