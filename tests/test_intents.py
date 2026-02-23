from agent.intents import classify_intent, extract_thresholds
from agent.types import IntentType


def test_classify_conditional_intent() -> None:
    question = "How did the Hawks perform when Trae Young scored more than 25 points?"
    assert classify_intent(question) == IntentType.CONDITIONAL_TEAM_PERFORMANCE


def test_classify_team_comparison() -> None:
    question = "Compare the Lakers and Warriors by season win percentage."
    assert classify_intent(question) == IntentType.TEAM_COMPARISON


def test_extract_thresholds() -> None:
    question = "How did the Hawks perform when Trae Young scored over 30 points?"
    thresholds = extract_thresholds(question)
    assert thresholds["points_over"] == 30
