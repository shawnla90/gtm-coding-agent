"""
_decay.py — Shared signal-decay rules.

Every signal type has a half-life (urgency decays one tier every N days) and
a max-age (older than this → forced to 'backlog' or dropped).

Imported by:
- scripts/analyze_content.py (caps Claude's urgency output)
- scripts/generate_insights.py (filters stale signals before generating briefs)
- scripts/decay_signals.py (one-shot retroactive cleanup)
"""

# SCAFFOLD: Define your signal taxonomy below. Each signal type maps to a
# half-life and max-age (both in days). Half-life is the age at which the
# urgency gets downgraded one tier. Max-age is the age at which the signal
# is forced to 'backlog' regardless of its original urgency.
#
# See docs/voice-dna.md for calibration guidance.

from __future__ import annotations

# Signal-type → {"half_life": int, "max_age": int}
DECAY_RULES: dict[str, dict[str, int]] = {
    # TODO: add your taxonomy here. Shape:
    # "pricing-complaint": {"half_life": 30, "max_age": 90},
    # "product-launch":    {"half_life": 14, "max_age": 60},
}

URGENCY_ORDER = ["act-now", "this-week", "this-month", "backlog"]

# Fallback rule applied when a signal type is not in DECAY_RULES.
DEFAULT_RULE = {"half_life": 30, "max_age": 90}


def _rule_for(signal_type: str) -> dict[str, int]:
    return DECAY_RULES.get(signal_type, DEFAULT_RULE)


def decay_urgency(signal_type: str, age_days: int, current_urgency: str) -> str:
    """Cap urgency based on age and signal-type half-life.

    1. Negative age (post dated in the future) is treated as 0.
    2. age >= max_age always returns 'backlog'.
    3. Universal guards: act-now needs age < 14 days, this-week needs age < 30 days.
    4. Otherwise, downgrade one tier per half-life elapsed.
    """
    age_days = max(0, age_days or 0)
    rule = _rule_for(signal_type)

    if age_days >= rule["max_age"]:
        return "backlog"

    if current_urgency == "act-now" and age_days >= 14:
        current_urgency = "this-week"
    if current_urgency == "this-week" and age_days >= 30:
        current_urgency = "this-month"

    current_idx = URGENCY_ORDER.index(current_urgency) if current_urgency in URGENCY_ORDER else 3
    decay_tiers = age_days // rule["half_life"]
    new_idx = min(len(URGENCY_ORDER) - 1, current_idx + decay_tiers)
    return URGENCY_ORDER[new_idx]


def should_drop(signal_type: str, age_days: int) -> bool:
    """Signals past 2x max_age are candidates for deletion (not just demotion).

    Caller decides whether to actually delete or just skip.
    """
    age_days = age_days or 0
    rule = _rule_for(signal_type)
    return age_days >= rule["max_age"] * 2


def urgency_hint_for_age(age_days: int) -> str:
    """What urgency Claude should aim for given a post's age.

    Injected into the analyzer system prompt so Claude has a clear ceiling.
    """
    age_days = max(0, age_days or 0)
    if age_days < 14:
        return "Can be act-now / this-week / this-month / backlog depending on specifics"
    if age_days < 30:
        return "Cap at this-week"
    if age_days < 60:
        return "Cap at this-month"
    if age_days < 180:
        return "Only backlog; signal extraction is optional"
    return "Skip extraction; post is too old for actionable intel"


def format_age(age_days: int | None) -> str:
    """Human-readable age string, e.g. '3d', '2w', '4mo', '1y'."""
    if age_days is None or age_days < 0:
        return "?"
    if age_days < 7:
        return f"{age_days}d"
    if age_days < 30:
        return f"{age_days // 7}w"
    if age_days < 365:
        return f"{age_days // 30}mo"
    return f"{age_days // 365}y"
