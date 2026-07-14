from datetime import datetime

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
    st.number_input(
        "Awaiting Reply after (days)",
        min_value=0,
        value=3,
        step=1,
        key="days_threshold",
        help="A sent thread shows up in Awaiting Reply once it's waited this many days without a reply.",
    )


def process_inbox(status_placeholder):
    with status_placeholder.container():
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
            awaiting = find_awaiting_replies(service, days_threshold=st.session_state.days_threshold)

            status.update(label="Done", state="complete")

    status_placeholder.empty()

    st.session_state.emails = processed
    st.session_state.skipped_count = len(skipped)
    st.session_state.awaiting = awaiting
    st.session_state.processed = True
    st.session_state.style_mode = style_result["mode"]
    st.session_state.style_sample_count = style_result["sample_count"]
    st.session_state.active_tone = active_tone


st.markdown('<div class="hero-header">&#10022; Morning Briefing</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Your inbox, prioritized.</div>', unsafe_allow_html=True)

status_slot = st.empty()

if st.button("Refresh Inbox"):
    process_inbox(status_slot)

urgent_count = sum(
    1 for e in st.session_state.emails if e["classification"].get("category") == "Urgent"
)
needs_reply_count = sum(
    1 for e in st.session_state.emails if e["classification"].get("category") == "Needs Reply"
)
awaiting_count = len(st.session_state.awaiting)
newsletters_count = st.session_state.skipped_count


def collect_commitments(emails):
    commitments = []
    for email in emails:
        classification = email["classification"]
        if classification.get("error"):
            continue
        for item in classification.get("action_items", []):
            task = item.get("task", "")
            if not task:
                continue
            commitments.append({
                "task": task,
                "deadline": item.get("deadline"),
                "subject": email["subject"],
                "from": email["from"],
                "category": classification.get("category", "FYI"),
            })
    return commitments


def _commitment_sort_key(indexed):
    index, commitment = indexed
    deadline = commitment["deadline"]
    if deadline:
        try:
            return (0, datetime.strptime(deadline, "%Y-%m-%d"))
        except (ValueError, TypeError):
            return (1, index)
    return (2, index)


commitments = [
    c for _, c in sorted(enumerate(collect_commitments(st.session_state.emails)), key=_commitment_sort_key)
]

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


def render_commitment_row(item):
    color = CATEGORY_COLORS.get(item["category"], ACCENT_END)
    if item["deadline"]:
        deadline_html = f'<div class="commitment-deadline">{item["deadline"]}</div>'
    else:
        deadline_html = '<div class="commitment-deadline none">No deadline</div>'

    st.markdown(
        f'<div class="commitment-row" style="--cat-color:{color}">'
        f'<span class="commitment-check">&#9744;</span>'
        f'<div class="commitment-body">'
        f'<div class="commitment-task">{item["task"]}</div>'
        f'<div class="commitment-meta">{item["subject"]} &middot; {item["from"]}</div>'
        f"</div>"
        f"{deadline_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_awaiting_row(item):
    days_waiting = item["days_waiting"]
    waiting_label = "waiting since today" if days_waiting == 0 else f"{days_waiting}d waiting"
    st.markdown(
        f'<div class="awaiting-row">'
        f'<div><b>{item["subject"]}</b><br>'
        f'<span class="email-meta">to {item["to"]}</span></div>'
        f'<div class="awaiting-days">{waiting_label}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


inbox_tab, commitments_tab, awaiting_tab = st.tabs(
    ["Inbox", f"Commitments ({len(commitments)})", f"Awaiting Reply ({awaiting_count})"]
)

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

with commitments_tab:
    if not st.session_state.processed:
        st.info("Click **Refresh Inbox** to gather commitments from your unread mail.")
    elif not commitments:
        st.success("No open commitments right now.")
    else:
        for item in commitments:
            render_commitment_row(item)

with awaiting_tab:
    if not st.session_state.processed:
        st.info("Click **Refresh Inbox** to check threads awaiting a reply.")
    elif not st.session_state.awaiting:
        st.success("No threads waiting on a reply.")
    else:
        for item in st.session_state.awaiting:
            render_awaiting_row(item)
