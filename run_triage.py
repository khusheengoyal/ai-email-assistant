import json
import sys

from classify import classify_email
from fallback_tone import DEFAULT_TONE, get_tone_instruction
from fetch_emails import fetch_unread_emails
from gmail_auth import get_gmail_service
from sender_log import count_from_sender, record_email
from writing_style import get_style_profile


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    service = get_gmail_service()

    style_result = get_style_profile(service)
    if style_result["mode"] == "personalized":
        style_guidance = style_result["profile"]
        print(f"Writing style: personalized (from {style_result['sample_count']} sent emails)\n")
    else:
        style_guidance = get_tone_instruction(DEFAULT_TONE)
        print(f"Writing style: default tone ({DEFAULT_TONE})\n")

    emails = fetch_unread_emails(service, max_results=5)

    skipped = [e for e in emails if e["is_bulk_mail"]]
    real = [e for e in emails if not e["is_bulk_mail"]]

    print(f"{len(emails)} unread: {len(real)} to classify, {len(skipped)} skipped as bulk mail\n")

    for email in real:
        result = classify_email(email, style_guidance=style_guidance)

        sender_count = count_from_sender(email["from"]) + 1
        record_email(email["id"], email["from"], email["subject"], result.get("category", ""))

        print("Subject:", email["subject"])
        print(f"Sender context: {sender_count} email(s) from this sender in the past week")
        print(json.dumps(result, indent=2))
        print("-" * 60)


if __name__ == "__main__":
    main()
