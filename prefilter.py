"""
Rule-based bulk-mail pre-filter, driven by filter_config.load_filter_config().

Each rule type is a small `(headers, config) -> bool` checker registered in
RULE_CHECKERS. To add a new rule type: write a checker function and append it
to RULE_CHECKERS -- is_bulk_mail() itself never needs to change.
"""

import logging
import re

from filter_config import load_filter_config

logger = logging.getLogger(__name__)

_config = None


def _get_config() -> dict:
    global _config
    if _config is None:
        _config = load_filter_config()
    return _config


def reload_config() -> dict:
    """Force a reload of filter_rules.json (e.g. after editing it at runtime)."""
    global _config
    _config = load_filter_config()
    return _config


def _sender_domain(sender: str) -> str:
    if "@" not in sender:
        return ""
    return sender.rsplit("@", 1)[-1].strip("> ").lower()


def _sender_email(sender: str) -> str:
    """Extract the bare email address from a `From` header like
    '"Jane Doe" <jane@example.com>', for exact allowlist matching."""
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", sender)
    return match.group(0).lower() if match else sender.strip().lower()


def _check_sender_patterns(headers: dict, config: dict) -> bool:
    sender = headers.get("From", "")
    return any(
        re.search(pattern, sender, re.IGNORECASE)
        for pattern in config.get("sender_patterns", [])
    )


def _check_blocked_domains(headers: dict, config: dict) -> bool:
    domain = _sender_domain(headers.get("From", ""))
    blocked = {d.lower() for d in config.get("blocked_domains", [])}
    return bool(domain) and domain in blocked


def _check_header_rules(headers: dict, config: dict) -> bool:
    for rule in config.get("header_rules", []):
        header_value = headers.get(rule["header"])
        condition = rule["condition"]

        if condition == "present" and header_value is not None:
            return True
        if condition == "equals" and header_value == rule.get("value"):
            return True
        if condition == "contains" and header_value and rule.get("value", "") in header_value:
            return True

    return False


# Registry of bulk-mail checkers, applied in order. Add new rule types here.
RULE_CHECKERS = [
    _check_sender_patterns,
    _check_blocked_domains,
    _check_header_rules,
]


def _is_allowlisted(headers: dict, config: dict) -> bool:
    sender = headers.get("From", "")
    email = _sender_email(sender)
    domain = _sender_domain(sender)
    allowlist = config.get("allowlist", {})

    # Exact match on the bare email address -- not substring -- so a short
    # allowlist entry can't accidentally match an unrelated blocked sender
    # (e.g. "news" would otherwise match "newsletter@mailchimp.com").
    if email and email in {s.lower() for s in allowlist.get("senders", [])}:
        return True
    if domain and domain in {d.lower() for d in allowlist.get("domains", [])}:
        return True

    return False


def is_bulk_mail(headers: dict, config: dict = None) -> bool:
    """True if the email should be treated as bulk mail and skipped from
    classification. The allowlist always overrides every other rule."""
    config = config or _get_config()

    if _is_allowlisted(headers, config):
        return False

    return any(checker(headers, config) for checker in RULE_CHECKERS)
