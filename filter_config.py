"""
Loads and validates the pre-filter rule configuration (see filter_rules.json).

The config controls which unread emails get treated as bulk mail and skipped
from classification. If the config file is missing, unreadable, or fails
validation, we fall back to DEFAULT_CONFIG rather than crashing or silently
classifying everything as important/unimportant.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

CONFIG_PATH = os.environ.get("FILTER_CONFIG_PATH", "filter_rules.json")

DEFAULT_CONFIG = {
    "sender_patterns": [r"no[-.]?reply", r"do[-.]?not[-.]?reply"],
    "blocked_domains": [],
    "header_rules": [
        {"header": "List-Unsubscribe", "condition": "present"},
    ],
    "allowlist": {"senders": [], "domains": []},
}

VALID_HEADER_CONDITIONS = {"present", "equals", "contains"}


def _validate(config: dict) -> list:
    """Return a list of human-readable validation errors (empty = valid)."""
    errors = []

    if not isinstance(config, dict):
        return ["config root must be a JSON object"]

    sender_patterns = config.get("sender_patterns", [])
    if not isinstance(sender_patterns, list):
        errors.append("sender_patterns must be a list of strings")
    else:
        for pattern in sender_patterns:
            if not isinstance(pattern, str):
                errors.append(f"sender_patterns entry {pattern!r} is not a string")
                continue
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"sender_patterns entry {pattern!r} is not a valid regex: {exc}")

    blocked_domains = config.get("blocked_domains", [])
    if not isinstance(blocked_domains, list) or not all(isinstance(d, str) for d in blocked_domains):
        errors.append("blocked_domains must be a list of strings")

    header_rules = config.get("header_rules", [])
    if not isinstance(header_rules, list):
        errors.append("header_rules must be a list of objects")
    else:
        for rule in header_rules:
            if not isinstance(rule, dict) or "header" not in rule or "condition" not in rule:
                errors.append(f"header_rules entry {rule!r} must have 'header' and 'condition'")
                continue
            if rule["condition"] not in VALID_HEADER_CONDITIONS:
                errors.append(
                    f"header_rules condition {rule['condition']!r} must be one of {sorted(VALID_HEADER_CONDITIONS)}"
                )
            elif rule["condition"] in {"equals", "contains"} and "value" not in rule:
                errors.append(
                    f"header_rules entry for {rule['header']!r} needs a 'value' for condition {rule['condition']!r}"
                )

    allowlist = config.get("allowlist", {})
    if not isinstance(allowlist, dict):
        errors.append("allowlist must be an object with 'senders' and 'domains' lists")
    else:
        for key in ("senders", "domains"):
            if key in allowlist and not isinstance(allowlist[key], list):
                errors.append(f"allowlist.{key} must be a list of strings")

    return errors


def load_filter_config(path: str = CONFIG_PATH) -> dict:
    """Load, validate, and return the pre-filter config, falling back to
    DEFAULT_CONFIG on any missing file, parse error, or validation failure."""
    if not os.path.exists(path):
        logger.warning("Filter config %s not found; using default rules", path)
        return DEFAULT_CONFIG

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Filter config %s could not be read (%s); using default rules", path, exc)
        return DEFAULT_CONFIG

    errors = _validate(config)
    if errors:
        logger.warning(
            "Filter config %s failed validation, using default rules instead:\n%s",
            path,
            "\n".join(f"  - {e}" for e in errors),
        )
        return DEFAULT_CONFIG

    # Top-level keys present in the user's config fully replace the default
    # for that key (lists are not merged) -- e.g. supplying "sender_patterns"
    # means only those patterns apply, the built-in no-reply patterns are
    # not implicitly kept. See README's "Pre-filter configuration" section.
    merged = {**DEFAULT_CONFIG, **config}
    allowlist = {**DEFAULT_CONFIG["allowlist"], **merged.get("allowlist", {})}
    merged["allowlist"] = allowlist
    return merged
