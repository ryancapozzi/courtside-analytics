from agent.intents import (
    classify_intent,
    extract_game_scope,
    extract_primary_metric,
    extract_ranking_limit,
    extract_ranking_metric,
    extract_thresholds,
)
from agent.types import IntentType


def test_classify_conditional_intent() -> None:
    question = "How did the Hawks perform when Trae Young scored more than 25 points?"
    assert classify_intent(question, team_count=1, player_count=1) == IntentType.CONDITIONAL_TEAM_PERFORMANCE


def test_classify_team_comparison() -> None:
    question = "Compare the Lakers and Warriors by season win percentage."
    assert classify_intent(question, team_count=2) == IntentType.TEAM_COMPARISON


def test_classify_player_threshold_count_intent() -> None:
    question = "How many times has John Wall scored 25 points?"
    assert classify_intent(question, player_count=1) == IntentType.PLAYER_THRESHOLD_COUNT


def test_classify_player_profile_summary_intent() -> None:
    question = "What is LeBron James averaging this season?"
    assert classify_intent(question, player_count=1) == IntentType.PLAYER_PROFILE_SUMMARY


def test_classify_player_single_game_high_intent() -> None:
    question = "What is Stephen Curry's career high points?"
    assert classify_intent(question, player_count=1) == IntentType.PLAYER_SINGLE_GAME_HIGH


def test_classify_team_record_summary_intent() -> None:
    question = "What is the Lakers record this season?"
    assert classify_intent(question, team_count=1) == IntentType.TEAM_RECORD_SUMMARY


def test_classify_team_head_to_head_intent() -> None:
    question = "What is the Lakers record against the Celtics?"
    assert classify_intent(question, team_count=2) == IntentType.TEAM_HEAD_TO_HEAD


def test_classify_team_ranking_intent() -> None:
    question = "Who are the top 5 teams by win percentage?"
    assert classify_intent(question) == IntentType.TEAM_RANKING


def test_classify_team_ranking_from_best_record() -> None:
    question = "Which team has the best record this season?"
    assert classify_intent(question) == IntentType.TEAM_RANKING


def test_classify_team_ranking_from_points_allowed_phrase() -> None:
    question = "Which team allows the fewest points this season?"
    assert classify_intent(question) == IntentType.TEAM_RANKING


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


def test_extract_primary_metric_win_pct() -> None:
    assert extract_primary_metric("Show top teams by win percentage.") == "win_pct"


def test_extract_primary_metric_record() -> None:
    assert extract_primary_metric("Which team has the best record this season?") == "win_pct"


def test_extract_primary_metric_turnovers() -> None:
    assert extract_primary_metric("How many turnovers does Luka average?") == "turnovers"


def test_extract_primary_metric_from_allow_points_phrase() -> None:
    assert extract_primary_metric("Which team allows the fewest points this season?") == "opponent_points"


def test_extract_ranking_limit() -> None:
    assert extract_ranking_limit("Who are the top 7 players by points?") == 7
