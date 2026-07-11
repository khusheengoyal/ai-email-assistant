"""
Default-tone engine, used when writing_style.py reports insufficient sent-mail
history. Deliberately kept independent of writing_style.py: this module knows
nothing about the user's actual writing, only a fixed set of selectable tones.
"""

DEFAULT_TONE = "Professional"

TONE_INSTRUCTIONS = {
    "Professional": (
        "Write in a clear, professional, businesslike tone. Be polite and direct, "
        "use complete sentences, and avoid slang."
    ),
    "Friendly": (
        "Write in a warm, approachable tone, as if to a colleague you get along with well. "
        "Contractions and light conversational phrasing are fine."
    ),
    "Concise": (
        "Write as briefly as possible while remaining polite -- short sentences, no filler, "
        "get straight to the point."
    ),
    "Formal": (
        "Write in a formal, respectful register suitable for a senior stakeholder or client. "
        "Avoid contractions and casual phrasing."
    ),
    "Casual": (
        "Write in a relaxed, informal tone, as if messaging a friendly peer. Contractions and "
        "casual phrasing are welcome."
    ),
}

TONE_OPTIONS = list(TONE_INSTRUCTIONS.keys())


def get_tone_instruction(tone: str) -> str:
    return TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS[DEFAULT_TONE])
