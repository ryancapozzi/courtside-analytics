from __future__ import annotations

import re

from .types import IntentType


THRESHOLD_COMPARATOR_RE = re.compile(
    (
        r"(more than|over|above|greater than|at least|less than|under|fewer than|"
        r"exactly|equal to)\s+(\d+(?:\.\d+)?)\s+"
        r"(points|rebounds|assists|steals|blocks|turnovers)"
    ),
    re.IGNORECASE,
)

THRESHOLD_ACTION_RE = re.compile(
    (
        r"(?:score(?:d|s|ing)?|record(?:ed|s|ing)?|put up|drop(?:ped|s|ping)?|"
        r"have|has|had|get|gets|got|grab(?:bed|s|bing)?|dish(?:ed|es|ing)?|"
        r"commit(?:ted|s|ting)?)\s+"
        r"(\d+(?:\.\d+)?)\s*(\+|plus)?\s+"
        r"(points|rebounds|assists|steals|blocks|turnovers)"
    ),
    re.IGNORECASE,
)

THRESHOLD_PLUS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(\+|plus)\s*(points|rebounds|assists|steals|blocks|turnovers)",
    re.IGNORECASE,
)

SEASON_RE = re.compile(r"(20\d{2}-\d{2}|20\d{2})")
TOP_N_RE = re.compile(r"\btop\s+(\d{1,2})\b", re.IGNORECASE)
COUNT_STYLE_RE = re.compile(r"\b(how many times|how many games|how often|count)\b", re.IGNORECASE)
TEAM_RANKING_RE = re.compile(
    r"\b(top|best|rank|ranking|leaders)\b.*\b(team|teams)\b|\bteam rankings?\b",
    re.IGNORECASE,
)
PLAYER_RANKING_RE = re.compile(
    r"\b(top|rank|ranking|highest|leaders)\b.*\b(players?|scorers?)\b",
    re.IGNORECASE,
)
TEAM_HEAD_TO_HEAD_RE = re.compile(r"\b(head[- ]?to[- ]?head|against|vs|versus)\b", re.IGNORECASE)
TEAM_RECORD_RE = re.compile(
    r"\b(record|win-loss|wins-losses|win percentage|win pct|winning percentage|wins)\b",
    re.IGNORECASE,
)
PLAYER_PROFILE_RE = re.compile(r"\b(average|avg|averaging|per game|stat line|stats)\b", re.IGNORECASE)
PLAYER_SINGLE_GAME_HIGH_RE = re.compile(
    r"\b(career high|single game high|most .* in a game|max(?:imum)?)\b",
    re.IGNORECASE,
)
TREND_RE = re.compile(r"\b(trend|over time|by season)\b", re.IGNORECASE)
AVERAGE_STYLE_RE = re.compile(r"\b(average|avg|averaging|per game|mean)\b", re.IGNORECASE)
TOTAL_STYLE_RE = re.compile(r"\b(total|sum|combined|in total|altogether)\b", re.IGNORECASE)
MAX_STYLE_RE = re.compile(r"\b(most|max|maximum|highest|peak)\b", re.IGNORECASE)
MIN_STYLE_RE = re.compile(r"\b(min|minimum|lowest|fewest)\b", re.IGNORECASE)
COUNT_STAT_STYLE_RE = re.compile(r"\b(count|how many)\b", re.IGNORECASE)


def classify_intent(question: str, team_count: int = 0, player_count: int = 0) -> IntentType:
    text = question.lower()
    has_threshold = bool(extract_thresholds(question))
    has_against_mode = detect_against_mode(question)
    has_record = bool(TEAM_RECORD_RE.search(question))
    has_trend = bool(TREND_RE.search(question))
    has_compare = any(token in text for token in ["compare", "vs", "versus"])
    has_player_high = bool(PLAYER_SINGLE_GAME_HIGH_RE.search(question))
    has_player_profile = bool(PLAYER_PROFILE_RE.search(question))
    primary_metric = extract_primary_metric(question)

    if has_compare and team_count >= 2 and player_count == 0:
        return IntentType.TEAM_COMPARISON

    if has_trend and team_count >= 1 and player_count == 0:
        return IntentType.TEAM_TREND

    if TEAM_HEAD_TO_HEAD_RE.search(question) and has_record and team_count >= 2 and player_count == 0:
        return IntentType.TEAM_HEAD_TO_HEAD

    if _is_team_ranking_question(question, team_count, player_count):
        return IntentType.TEAM_RANKING

    if _is_player_ranking_question(question, player_count):
        return IntentType.PLAYER_RANKING

    if has_player_high and player_count >= 1:
        return IntentType.PLAYER_SINGLE_GAME_HIGH

    if COUNT_STYLE_RE.search(text) and has_threshold and player_count >= 1:
        return IntentType.PLAYER_THRESHOLD_COUNT

    if "when" in text and has_threshold and team_count >= 1 and player_count >= 1:
        return IntentType.CONDITIONAL_TEAM_PERFORMANCE

    if TEAM_RECORD_RE.search(question) and team_count >= 1 and player_count == 0:
        return IntentType.TEAM_RECORD_SUMMARY

    if has_against_mode and team_count >= 1 and player_count >= 1:
        return IntentType.PLAYER_PROFILE_SUMMARY

    if (
        has_player_profile
        or (player_count >= 1 and primary_metric in _SUPPORTED_PLAYER_METRICS)
        or (player_count >= 1 and "how many" in text)
    ):
        return IntentType.PLAYER_PROFILE_SUMMARY

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
    metric = extract_primary_metric(question)
    if metric in _SUPPORTED_PLAYER_METRICS:
        return metric
    return "points"


def extract_primary_metric(question: str) -> str:
    text = question.lower()
    if "record" in text:
        return "win_pct"
    if "win percentage" in text or "win pct" in text or "winning percentage" in text:
        return "win_pct"
    if "allow" in text and "point" in text:
        return "opponent_points"
    if "points allowed" in text or "defense" in text or "defensive" in text:
        return "opponent_points"
    if "turnover" in text:
        return "turnovers"
    if "minute" in text:
        return "minutes"
    if "win" in text and "points" not in text:
        return "wins"
    if "assist" in text:
        return "assists"
    if "rebound" in text:
        return "rebounds"
    if "steal" in text:
        return "steals"
    if "block" in text:
        return "blocks"
    return "points"


def extract_ranking_limit(question: str) -> int:
    match = TOP_N_RE.search(question)
    if not match:
        return 15
    parsed = int(match.group(1))
    if parsed < 1:
        return 15
    return min(parsed, 50)


def detect_against_mode(question: str) -> bool:
    text = question.lower()
    return " against " in f" {text} " or " vs " in f" {text} " or " versus " in f" {text} "


def extract_stat_operation(question: str, primary_metric: str) -> str:
    text = question.lower()

    if primary_metric == "win_pct":
        return "avg"

    if AVERAGE_STYLE_RE.search(text):
        return "avg"

    if TOTAL_STYLE_RE.search(text):
        return "sum"

    if MAX_STYLE_RE.search(text) and "top" not in text and "rank" not in text:
        return "max"

    if MIN_STYLE_RE.search(text) and "top" not in text and "rank" not in text:
        return "min"

    if COUNT_STAT_STYLE_RE.search(text):
        if any(token in text for token in ["how many games", "how many times", "how often"]):
            return "count"
        # "How many assists did X have?" is best interpreted as total assists.
        return "sum"

    return "avg"


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


def _is_team_ranking_question(question: str, team_count: int, player_count: int) -> bool:
    if player_count > 0:
        return False
    if TEAM_RANKING_RE.search(question):
        return True
    text = question.lower()
    if any(
        phrase in text
        for phrase in [
            "best record",
            "most wins",
            "fewest points allowed",
            "allows the fewest points",
            "allow the fewest points",
            "highest win percentage",
            "lowest points allowed",
        ]
    ):
        return True
    return (
        any(token in text for token in ["top", "best", "rank", "leaders", "most", "fewest"])
        and any(
            token in text
            for token in [
                "win percentage",
                "win pct",
                "wins",
                "teams",
                "record",
                "points allowed",
                "allow",
            ]
        )
        and team_count <= 1
    )


def _is_player_ranking_question(question: str, player_count: int) -> bool:
    if PLAYER_RANKING_RE.search(question):
        return True
    text = question.lower()
    return (
        any(token in text for token in ["top", "rank", "highest", "leaders", "most"])
        and any(
            token in text
            for token in [
                "player",
                "players",
                "scorer",
                "scorers",
                "assists",
                "rebounds",
                "steals",
                "blocks",
                "points",
                "turnovers",
                "minutes",
            ]
        )
        and player_count <= 1
    )


_SUPPORTED_PLAYER_METRICS = {
    "points",
    "assists",
    "rebounds",
    "steals",
    "blocks",
    "turnovers",
    "minutes",
}
