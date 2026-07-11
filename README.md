# AI Email Assistant

A Gmail triage assistant that reduces **decisions**, not just keystrokes.

## Why

Office workers get ~121 emails/day; only ~24% are actually important. This
tool reads your inbox, tells you what matters, summarizes the rest, extracts
commitments/deadlines, tracks threads waiting on a reply, and drafts replies
in your own writing style — so the daily inbox pass becomes a 5-minute
review instead of a 45-minute slog.

## Privacy & safety (this is a feature, not a footnote)

- **Draft-only, structurally.** The OAuth token is issued with only
  `gmail.readonly` and `gmail.compose` scopes. `gmail.send` is never
  requested. The app is not merely instructed not to send — it holds no
  credential capable of sending. Enforced by Google, not by a prompt.
- **Minimal retention.** Email bodies are processed in memory for
  classification and never written to disk. Only a small sender/metadata
  log (sender, subject, timestamp, category) persists locally, to support
  "3rd email this week"-style context. The writing-style profile
  (`writing_profile.json`) persists only a short derived description of
  tone/phrasing, never the raw sent-mail bodies it was built from.
- **Secrets never committed.** `credentials.json`, `token.json`, and `.env`
  are gitignored from the start of this repo.
- Classification/summarization runs on Groq, which offers zero-data-retention
  options.

## Status

- [x] Gmail OAuth (readonly + compose scopes) — working
- [x] Read one email — working (proof of chain)
- [x] Fetch unread + extract body/PDF text
- [x] Configurable rule-based pre-filter (sender patterns, blocked domains,
      header rules, allowlist)
- [x] Groq classification (category, priority, summary, action items, draft)
- [x] Writing-style profile from sent mail, with graceful default-tone fallback
- [x] Awaiting-reply follow-up tracking
- [x] Sender-aware repeat-contact log
- [x] Streamlit dashboard (stat row, tabs, email cards, awaiting-reply list)

## Stack

Python, official Gmail API client (`google-api-python-client`), Groq,
`pypdf`, Streamlit.

## Setup

1. Create a Google Cloud project, enable the Gmail API, configure the OAuth
   consent screen (Testing mode, add yourself as a test user), create a
   Desktop-app OAuth client, download as `credentials.json` in the project
   root.
2. `python -m venv .venv`
3. `.venv\Scripts\pip install -r requirements.txt`
4. `.venv\Scripts\python read_one_email.py` — first run opens a browser
   consent screen; approve it. Creates `token.json`.
5. (Optional) Edit `filter_rules.json` to customize the pre-filter — see
   [Pre-filter configuration](#pre-filter-configuration) below. If you skip
   this, sensible defaults are used automatically.

## Pre-filter configuration

Unread emails are checked against `filter_rules.json` (loaded and validated
by `filter_config.py`) before classification, so obvious bulk mail never
reaches the model. The engine (`prefilter.py`) is rule-registry based — new
rule types are added by writing a `(headers, config) -> bool` checker
function and registering it, without touching `is_bulk_mail()`.

If `filter_rules.json` is missing, unreadable, or fails validation, the app
logs a warning and falls back to built-in defaults (no-reply sender patterns
+ `List-Unsubscribe` header) rather than crashing or under-filtering.

Format:

```json
{
  "sender_patterns": ["no[-.]?reply", "do[-.]?not[-.]?reply", "notifications?@"],
  "blocked_domains": ["mailchimp.com", "sendgrid.net"],
  "header_rules": [
    {"header": "List-Unsubscribe", "condition": "present"},
    {"header": "Precedence", "condition": "equals", "value": "bulk"}
  ],
  "allowlist": {
    "senders": ["boss@company.com"],
    "domains": ["important-client.com"]
  }
}
```

- `sender_patterns` — regexes tested against the `From` header (case-insensitive).
- `blocked_domains` — exact sender-domain matches.
- `header_rules` — each has a `header` name and a `condition`: `present`
  (header exists and is non-empty), `equals`, or `contains` (the latter two
  need a `value`).
- `allowlist` — `senders` (exact match against the sender's bare email
  address) and `domains` (exact match). Allowlist always overrides every
  other rule.

## Writing-style profile & default tone

`writing_style.py` builds a personalized writing-style profile from your own
sent mail, used to guide drafted replies. It never fabricates a profile: the
"sufficient history" threshold is the named constant
`MIN_SUBSTANTIVE_SENT_EMAILS = 5` in `writing_style.py`, requiring at least 5
*substantive* sent emails (short acknowledgements like "Thanks", "OK", or
"Received" — and anything under `MIN_SUBSTANTIVE_WORDS = 8` words — don't
count).

- **History met** → a profile is generated (via Groq) from your sent-mail
  samples and cached in `writing_profile.json`, regenerated automatically
  whenever your substantive sent-mail count changes.
- **History not met** (or profile generation fails) → drafts fall back to a
  selectable **Default Tone** (Professional, Friendly, Concise, Formal,
  Casual — see `fallback_tone.py`), chosen from the sidebar in the Streamlit
  app. This is deliberately a separate module from `writing_style.py` so the
  personalized engine and the fallback-tone engine can evolve independently.

Mode is re-evaluated on every "Refresh Inbox," so it switches automatically
between personalized and fallback as your sent-mail history grows — no code
change or app restart needed. Whichever mode is active is shown next to every
drafted reply ("✦ Personalized from your writing style" or "Default tone:
Professional").

## Non-goals

- Never sends email automatically or otherwise. Every reply is a draft
  requiring explicit human approval.
- Not a full email client — triage and drafting only.

## License

MIT — see [LICENSE](LICENSE).
