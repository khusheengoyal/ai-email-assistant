from gmail_auth import get_gmail_service


def main():
    service = get_gmail_service()

    results = service.users().messages().list(userId="me", maxResults=1).execute()
    messages = results.get("messages", [])

    if not messages:
        print("No messages found in this inbox.")
        return

    message_id = messages[0]["id"]
    message = service.users().messages().get(userId="me", id=message_id, format="metadata",
                                               metadataHeaders=["From", "Subject"]).execute()

    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}

    print("Subject:", headers.get("Subject", "(no subject)"))
    print("From:", headers.get("From", "(unknown sender)"))
    print("Snippet:", message.get("snippet", ""))


if __name__ == "__main__":
    main()
