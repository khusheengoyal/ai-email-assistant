import streamlit as st

from classify import classify_email
from fallback_tone import DEFAULT_TONE, TONE_OPTIONS, get_tone_instruction
from fetch_emails import fetch_unread_emails
from followups import find_awaiting_replies
from gmail_auth import get_gmail_service
from sender_log import count_from_sender, record_email
from styles import ACCENT_END, CATEGORY_COLORS, CSS
from writing_style import get_style_profile

st.set_page_config(page_title="AI Email Assistant", page_icon="✦", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

if "processed" not in st.session_state:
    st.session_state.processed = False
    st.session_state.emails = []
    st.session_state.skipped_count = 0
    st.session_state.awaiting = []
    st.session_state.active_tab = "Inbox"
    st.session_state.style_mode = "fallback"
    st.session_state.style_sample_count = 0
    st.session_state.active_tone = DEFAULT_TONE

with st.sidebar:
    st.markdown("### Settings")
    st.selectbox(
        "Default Tone",
        TONE_OPTIONS,
        index=TONE_OPTIONS.index(DEFAULT_TONE),
        key="default_tone",
        help="Used for drafted replies until you have enough sent mail for a personalized style.",
    )


def process_inbox():
    with st.status("Reading inbox...", expanded=True) as status:
        service = get_gmail_service()

        status.update(label="Checking your writing style...")
        style_result = get_style_profile(service)
        active_tone = st.session_state.default_tone
        if style_result["mode"] == "personalized":
            style_guidance = style_result["profile"]
        else:
            style_guidance = get_tone_instruction(active_tone)

        emails = fetch_unread_emails(service, max_results=20)
        skipped = [e for e in emails if e["is_bulk_mail"]]
        real = [e for e in emails if not e["is_bulk_mail"]]
        status.update(label=f"Read {len(emails)} unread email(s), {len(skipped)} look like bulk mail")

        status.update(label=f"Prioritizing {len(real)} email(s)...")
        processed = []
        for email in real:
            result = classify_email(email, style_guidance=style_guidance)
            sender_count = count_from_sender(email["from"]) + 1
            record_email(email["id"], email["from"], email["subject"], result.get("category", ""))
            processed.append({**email, "classification": result, "sender_count": sender_count})

        status.update(label="Checking threads awaiting reply...")
        awaiting = find_awaiting_replies(service)

        status.update(label="Done", state="complete")

    st.session_state.emails = processed
    st.session_state.skipped_count = len(skipped)
    st.session_state.awaiting = awaiting
    st.session_state.processed = True
    st.session_state.style_mode = style_result["mode"]
    st.session_state.style_sample_count = style_result["sample_count"]
    st.session_state.active_tone = active_tone


st.markdown('<div class="hero-header">&#10022; Morning Briefing</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Your inbox, prioritized.</div>', unsafe_allow_html=True)

if st.button("Refresh Inbox"):
    process_inbox()

urgent_count = sum(
    1 for e in st.session_state.emails if e["classification"].get("category") == "Urgent"
)
needs_reply_count = sum(
    1 for e in st.session_state.emails if e["classification"].get("category") == "Needs Reply"
)
awaiting_count = len(st.session_state.awaiting)
newsletters_count = st.session_state.skipped_count

stats = [
    ("Urgent", urgent_count, CATEGORY_COLORS["Urgent"]),
    ("Needs Reply", needs_reply_count, CATEGORY_COLORS["Needs Reply"]),
    ("Awaiting Follow-up", awaiting_count, ACCENT_END),
    ("Newsletters Skipped", newsletters_count, CATEGORY_COLORS["Newsletter"]),
]

cards_html = "".join(
    f'<div class="stat-card" style="--stat-color:{color}">'
    f'<div class="stat-number">{value}</div>'
    f'<div class="stat-label">{label}</div>'
    f"</div>"
    for label, value, color in stats
)
st.markdown(f'<div class="stat-row">{cards_html}</div>', unsafe_allow_html=True)


def render_email_card(email):
    classification = email["classification"]

    if classification.get("error"):
        st.markdown(
            f'<div class="email-card" style="--cat-color:{CATEGORY_COLORS["FYI"]}">'
            f'<div class="email-subject">{email["subject"]}</div>'
            f'<div class="email-meta">{email["from"]}</div>'
            f'<div class="email-summary">Could not classify this email.</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    category = classification.get("category", "FYI")
    color = CATEGORY_COLORS.get(category, ACCENT_END)
    priority = classification.get("priority_score", "-")
    sender_note = f' &middot; {email["sender_count"]}x this week' if email["sender_count"] > 1 else ""

    action_items_html = "".join(
        f'<div class="action-item">&#8226; {item.get("task", "")}'
        + (f' &mdash; <span class="action-deadline">{item["deadline"]}</span>' if item.get("deadline") else "")
        + "</div>"
        for item in classification.get("action_items", [])
    )

    st.markdown(
        f'<div class="email-card" style="--cat-color:{color}">'
        f'<div class="email-card-top">'
        f'<div><div class="email-subject">{email["subject"]}</div>'
        f'<div class="email-meta">{email["from"]}{sender_note}</div></div>'
        f'<div style="text-align:right"><span class="category-badge" style="--cat-color:{color}">{category}</span>'
        f'<div class="priority-pill">Priority {priority}/10</div></div>'
        f"</div>"
        f'<div class="email-summary">{classification.get("summary", "")}</div>'
        f"{action_items_html}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if classification.get("suggested_reply"):
        with st.expander("Suggested reply (draft only)"):
            if st.session_state.style_mode == "personalized":
                st.markdown(
                    '<span class="style-badge personalized">&#10022; Personalized from your writing style</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span class="style-badge fallback">Default tone: {st.session_state.active_tone}</span>',
                    unsafe_allow_html=True,
                )
            st.text_area(
                "Draft",
                value=classification["suggested_reply"],
                key=f"draft_{email['id']}",
                label_visibility="collapsed",
                height=120,
            )


def render_awaiting_row(item):
    st.markdown(
        f'<div class="awaiting-row">'
        f'<div><b>{item["subject"]}</b><br>'
        f'<span class="email-meta">to {item["to"]}</span></div>'
        f'<div class="awaiting-days">{item["days_waiting"]}d waiting</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


inbox_tab, awaiting_tab = st.tabs(["Inbox", f"Awaiting Reply ({awaiting_count})"])

with inbox_tab:
    if not st.session_state.processed:
        st.info("Click **Refresh Inbox** to read and prioritize your unread mail.")
    elif not st.session_state.emails:
        st.success("Nothing to triage — inbox is clear.")
    else:
        sorted_emails = sorted(
            st.session_state.emails,
            key=lambda e: e["classification"].get("priority_score", 0),
            reverse=True,
        )
        for email in sorted_emails:
            render_email_card(email)

with awaiting_tab:
    if not st.session_state.processed:
        st.info("Click **Refresh Inbox** to check threads awaiting a reply.")
    elif not st.session_state.awaiting:
        st.success("No threads waiting on a reply.")
    else:
        for item in st.session_state.awaiting:
            render_awaiting_row(item)
