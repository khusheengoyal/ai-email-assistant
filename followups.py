from datetime import datetime, timezone


def find_awaiting_replies(service, days_threshold=3, lookback_days=30):
    sent = service.users().messages().list(
        userId="me", q=f"in:sent newer_than:{lookback_days}d"
    ).execute()

    thread_ids = {m["threadId"] for m in sent.get("messages", [])}

    awaiting = []
    now = datetime.now(timezone.utc)

    for thread_id in thread_ids:
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()

        messages = thread.get("messages", [])
        if not messages:
            continue

        last_message = messages[-1]
        if "SENT" not in last_message.get("labelIds", []):
            continue

        sent_time = datetime.fromtimestamp(
            int(last_message["internalDate"]) / 1000, tz=timezone.utc
        )
        days_waiting = (now - sent_time).days

        if days_waiting >= days_threshold:
            headers = {h["name"]: h["value"] for h in last_message["payload"]["headers"]}
            awaiting.append({
                "thread_id": thread_id,
                "subject": headers.get("Subject", "(no subject)"),
                "to": headers.get("To", ""),
                "last_sent_date": headers.get("Date", ""),
                "days_waiting": days_waiting,
            })

    awaiting.sort(key=lambda t: t["days_waiting"], reverse=True)
    return awaiting


if __name__ == "__main__":
    import sys

    from gmail_auth import get_gmail_service

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    service = get_gmail_service()
    results = find_awaiting_replies(service, days_threshold=3, lookback_days=30)

    print(f"{len(results)} thread(s) awaiting reply\n")
    for item in results:
        print(f"  {item['subject']}  ->  {item['to']}  ({item['days_waiting']}d waiting)")
