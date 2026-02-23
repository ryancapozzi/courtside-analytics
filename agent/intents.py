from __future__ import annotations

import re

from .types import IntentType


THRESHOLD_RE = re.compile(
    r"(more than|over|above|greater than|at least|less than|under)\s+(\d+(?:\.\d+)?)\s+(points|rebounds|assists)",
    re.IGNORECASE,
)

SEASON_RE = re.compile(r"(20\d{2}-\d{2}|20\d{2})")



def classify_intent(question: str) -> IntentType:
    text = question.lower()

    if any(token in text for token in ["compare", "vs", "versus"]):
        return IntentType.TEAM_COMPARISON

    if any(token in text for token in ["trend", "over time", "by season"]):
        return IntentType.TEAM_TREND

    if any(token in text for token in ["top", "rank", "highest", "leaders"]):
        return IntentType.PLAYER_RANKING

    if "when" in text and THRESHOLD_RE.search(question):
        return IntentType.CONDITIONAL_TEAM_PERFORMANCE

    return IntentType.UNKNOWN



def extract_thresholds(question: str) -> dict[str, float]:
    thresholds: dict[str, float] = {}

    for match in THRESHOLD_RE.finditer(question):
        comparator = match.group(1).lower()
        value = float(match.group(2))
        stat = match.group(3).lower()

        key = f"{stat}_{comparator.replace(' ', '_')}"
        thresholds[key] = value

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
