import base64
import sys

from attachments import process_attachments
from gmail_auth import get_gmail_service
from prefilter import is_bulk_mail


def extract_body_text(payload):
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])

    for part in payload.get("parts", []):
        text = extract_body_text(part)
        if text:
            return text

    return ""


def _decode(data):
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def fetch_unread_emails(service, max_results=10):
    results = service.users().messages().list(
        userId="me", q="is:unread", maxResults=max_results
    ).execute()

    email_list = []
    for msg_ref in results.get("messages", []):
        message = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}

        has_attachment, attachment_text = process_attachments(
            service, message["id"], message["payload"]
        )

        body_text = extract_body_text(message["payload"])
        if attachment_text:
            body_text = f"{body_text}\n\n{attachment_text}"

        email_list.append({
            "id": message["id"],
            "thread_id": message["threadId"],
            "from": headers.get("From", "(unknown sender)"),
            "subject": headers.get("Subject", "(no subject)"),
            "date": headers.get("Date", ""),
            "body_text": body_text,
            "has_attachment": has_attachment,
            "snippet": message.get("snippet", ""),
            "is_bulk_mail": is_bulk_mail(headers),
        })

    return email_list


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    service = get_gmail_service()
    emails = fetch_unread_emails(service, max_results=5)

    skipped = [e for e in emails if e["is_bulk_mail"]]
    real = [e for e in emails if not e["is_bulk_mail"]]

    print(f"Found {len(emails)} unread email(s): {len(real)} to process, {len(skipped)} skipped (bulk mail)\n")

    print("=== Skipped (bulk mail) ===")
    for email in skipped:
        print(f"  - {email['subject']}  ({email['from']})")

    print("\n=== To process ===")
    for email in real:
        print("Subject:", email["subject"])
        print("From:", email["from"])
        print("Has attachment:", email["has_attachment"])
        print("Body (first 200 chars):", email["body_text"][:200])
        print("-" * 60)
