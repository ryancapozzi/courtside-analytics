from __future__ import annotations

import re

from .types import IntentType


THRESHOLD_COMPARATOR_RE = re.compile(
    (
        r"(more than|over|above|greater than|at least|less than|under|fewer than|"
        r"exactly|equal to)\s+(\d+(?:\.\d+)?)\s+"
        r"(points|rebounds|assists|steals|blocks)"
    ),
    re.IGNORECASE,
)

THRESHOLD_ACTION_RE = re.compile(
    (
        r"(?:score(?:d|s|ing)?|record(?:ed|s|ing)?|put up|drop(?:ped|s|ping)?|"
        r"have|has|had|get|gets|got|grab(?:bed|s|bing)?|dish(?:ed|es|ing)?)\s+"
        r"(\d+(?:\.\d+)?)\s*(\+|plus)?\s+"
        r"(points|rebounds|assists|steals|blocks)"
    ),
    re.IGNORECASE,
)

THRESHOLD_PLUS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(\+|plus)\s*(points|rebounds|assists|steals|blocks)",
    re.IGNORECASE,
)

SEASON_RE = re.compile(r"(20\d{2}-\d{2}|20\d{2})")
COUNT_STYLE_RE = re.compile(r"\b(how many times|how many games|how often|count)\b", re.IGNORECASE)



def classify_intent(question: str) -> IntentType:
    text = question.lower()
    has_threshold = bool(extract_thresholds(question))

    if any(token in text for token in ["compare", "vs", "versus"]):
        return IntentType.TEAM_COMPARISON

    if any(token in text for token in ["trend", "over time", "by season"]):
        return IntentType.TEAM_TREND

    if any(token in text for token in ["top", "rank", "highest", "leaders"]):
        return IntentType.PLAYER_RANKING

    if COUNT_STYLE_RE.search(text) and has_threshold:
        return IntentType.PLAYER_THRESHOLD_COUNT

    if "when" in text and has_threshold:
        return IntentType.CONDITIONAL_TEAM_PERFORMANCE

    return IntentType.UNKNOWN



def extract_thresholds(question: str) -> dict[str, float]:
    thresholds: dict[str, float] = {}

    for match in THRESHOLD_COMPARATOR_RE.finditer(question):
        comparator = _normalize_comparator(match.group(1))
        value = float(match.group(2))
        stat = match.group(3).lower()

        key = f"{stat}_{comparator}"
        thresholds[key] = value

    for stat, comparator, value in _extract_implicit_thresholds(question):
        key = f"{stat}_{comparator}"
        thresholds.setdefault(key, value)

    return thresholds



def extract_season_mentions(question: str) -> list[str]:
    return [m.group(1) for m in SEASON_RE.finditer(question)]


def extract_game_scope(question: str) -> str:
    text = question.lower()
    if "all games" in text or "all-time" in text or "overall" in text:
        return "all"
    if "playoff" in text or "postseason" in text:
        return "playoffs"
    if "preseason" in text:
        return "preseason"
    if "regular season" in text:
        return "regular"
    # Default to regular season to avoid mixing in special events.
    return "regular"


def extract_ranking_metric(question: str) -> str:
    text = question.lower()
    if "assist" in text:
        return "assists"
    if "rebound" in text:
        return "rebounds"
    if "steal" in text:
        return "steals"
    if "block" in text:
        return "blocks"
    return "points"


def _extract_implicit_thresholds(question: str) -> list[tuple[str, str, float]]:
    out: list[tuple[str, str, float]] = []

    for match in THRESHOLD_ACTION_RE.finditer(question):
        value = float(match.group(1))
        plus = match.group(2)
        stat = match.group(3).lower()
        comparator = "at_least" if plus else "at_least"
        out.append((stat, comparator, value))

    for match in THRESHOLD_PLUS_RE.finditer(question):
        value = float(match.group(1))
        stat = match.group(3).lower()
        out.append((stat, "at_least", value))

    return out


def _normalize_comparator(raw: str) -> str:
    normalized = raw.lower().strip()
    mapping = {
        "more than": "more_than",
        "over": "over",
        "above": "above",
        "greater than": "greater_than",
        "at least": "at_least",
        "less than": "less_than",
        "under": "under",
        "fewer than": "less_than",
        "exactly": "exactly",
        "equal to": "exactly",
    }
    return mapping.get(normalized, "at_least")
