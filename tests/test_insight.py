from agent.insight import InsightGenerator
from agent.types import QueryResult


class DummyOllama:
    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        return "dummy"


def test_deterministic_conditional_summary_uses_exact_values() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "team_name",
            "player_name",
            "games",
            "wins",
            "win_pct",
            "avg_player_points",
            "avg_team_points",
        ],
        rows=[
            {
                "team_name": "Hawks",
                "player_name": "Trae Young",
                "games": 252,
                "wins": 137,
                "win_pct": 54.37,
                "avg_player_points": 33.23,
                "avg_team_points": 119.74,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "137-115" in text
    assert "252 games" in text
    assert "54.37%" in text
    assert "33.23" in text
    assert "119.74" in text
