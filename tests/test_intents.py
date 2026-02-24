from agent.intents import (
    classify_intent,
    extract_game_scope,
    extract_ranking_metric,
    extract_thresholds,
)
from agent.types import IntentType


def test_classify_conditional_intent() -> None:
    question = "How did the Hawks perform when Trae Young scored more than 25 points?"
    assert classify_intent(question) == IntentType.CONDITIONAL_TEAM_PERFORMANCE


def test_classify_team_comparison() -> None:
    question = "Compare the Lakers and Warriors by season win percentage."
    assert classify_intent(question) == IntentType.TEAM_COMPARISON


def test_classify_player_threshold_count_intent() -> None:
    question = "How many times has John Wall scored 25 points?"
    assert classify_intent(question) == IntentType.PLAYER_THRESHOLD_COUNT


def test_extract_thresholds() -> None:
    question = "How did the Hawks perform when Trae Young scored over 30 points?"
    thresholds = extract_thresholds(question)
    assert thresholds["points_over"] == 30


def test_extract_thresholds_from_implicit_scoring_phrase() -> None:
    question = "How many times has John Wall scored 25 points?"
    thresholds = extract_thresholds(question)
    assert thresholds["points_at_least"] == 25


def test_extract_game_scope_defaults_regular() -> None:
    assert extract_game_scope("How did the Hawks perform when Trae Young scored over 30 points?") == "regular"


def test_extract_game_scope_playoffs() -> None:
    assert extract_game_scope("How did the Hawks perform in the playoffs when Trae Young scored over 30 points?") == "playoffs"


def test_extract_ranking_metric_assists() -> None:
    assert extract_ranking_metric("Who are the top players by assists?") == "assists"
