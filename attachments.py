import base64
import io

from pypdf import PdfReader


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


# Registry: mimeType -> function(bytes) -> extracted text.
# Add DOCX/XLSX/image support later by registering another entry here —
# find_attachment_parts / process_attachments never need to change.
EXTRACTORS = {
    "application/pdf": extract_pdf_text,
}


def find_attachment_parts(payload):
    parts_found = []

    if payload.get("filename"):
        parts_found.append(payload)

    for part in payload.get("parts", []):
        parts_found.extend(find_attachment_parts(part))

    return parts_found


def get_attachment_bytes(service, message_id, attachment_id):
    attachment = service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
    ).execute()
    return base64.urlsafe_b64decode(attachment["data"])


def process_attachments(service, message_id, payload):
    extracted_sections = []
    has_attachment = False

    for part in find_attachment_parts(payload):
        has_attachment = True
        mime_type = part.get("mimeType", "")
        extractor = EXTRACTORS.get(mime_type)
        if not extractor:
            continue

        attachment_id = part.get("body", {}).get("attachmentId")
        if not attachment_id:
            continue

        raw_bytes = get_attachment_bytes(service, message_id, attachment_id)
        text = extractor(raw_bytes)
        if text:
            extracted_sections.append(f"--- Attachment: {part['filename']} ---\n{text}")

    return has_attachment, "\n\n".join(extracted_sections)
