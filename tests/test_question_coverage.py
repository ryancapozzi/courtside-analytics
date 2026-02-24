import pytest

from agent.intents import classify_intent
from agent.types import IntentType


@pytest.mark.parametrize(
    "question,team_count,player_count,expected",
    [
        (
            "How did the Hawks perform when Trae Young scored over 30 points?",
            1,
            1,
            IntentType.CONDITIONAL_TEAM_PERFORMANCE,
        ),
        (
            "How many times has John Wall scored 25 points?",
            0,
            1,
            IntentType.PLAYER_THRESHOLD_COUNT,
        ),
        (
            "What is LeBron James averaging this season?",
            0,
            1,
            IntentType.PLAYER_PROFILE_SUMMARY,
        ),
        (
            "How does Stephen Curry perform against the Lakers in playoffs?",
            1,
            1,
            IntentType.PLAYER_PROFILE_SUMMARY,
        ),
        (
            "What is Stephen Curry's career high points?",
            0,
            1,
            IntentType.PLAYER_SINGLE_GAME_HIGH,
        ),
        (
            "Compare the Lakers and Warriors by season win percentage.",
            2,
            0,
            IntentType.TEAM_COMPARISON,
        ),
        (
            "Show the trend of the Denver Nuggets over time.",
            1,
            0,
            IntentType.TEAM_TREND,
        ),
        (
            "What is the Lakers record this season?",
            1,
            0,
            IntentType.TEAM_RECORD_SUMMARY,
        ),
        (
            "What is the Lakers record against the Celtics?",
            2,
            0,
            IntentType.TEAM_HEAD_TO_HEAD,
        ),
        (
            "Which team has the best record this season?",
            0,
            0,
            IntentType.TEAM_RANKING,
        ),
        (
            "Which team allows the fewest points this season?",
            0,
            0,
            IntentType.TEAM_RANKING,
        ),
        (
            "Who has the most assists this season?",
            0,
            0,
            IntentType.PLAYER_RANKING,
        ),
    ],
)
def test_question_intent_coverage(
    question: str,
    team_count: int,
    player_count: int,
    expected: IntentType,
) -> None:
    assert classify_intent(question, team_count=team_count, player_count=player_count) == expected

