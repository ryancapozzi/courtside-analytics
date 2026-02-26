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


def test_deterministic_threshold_count_summary() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "threshold_stat",
            "threshold_operator",
            "threshold_value",
            "games_meeting_threshold",
            "avg_stat_value",
        ],
        rows=[
            {
                "player_name": "John Wall",
                "threshold_stat": "points",
                "threshold_operator": ">=",
                "threshold_value": 25,
                "games_meeting_threshold": 145,
                "avg_stat_value": 31.2,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "John Wall has 145 games" in text
    assert "(points >= 25)" in text
    assert "31.20 points" in text


def test_deterministic_player_profile_summary() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "metric_name",
            "stat_operation",
            "games",
            "requested_value",
            "per_game_value",
        ],
        rows=[
            {
                "player_name": "LeBron James",
                "metric_name": "assists",
                "stat_operation": "sum",
                "games": 82,
                "requested_value": 688,
                "per_game_value": 8.39,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "LeBron James recorded 688 total assists" in text
    assert "82 games" in text
    assert "8.39 assists per game" in text


def test_deterministic_team_record_summary() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "team_name",
            "games",
            "wins",
            "losses",
            "win_pct",
            "avg_points",
            "avg_points_allowed",
        ],
        rows=[
            {
                "team_name": "Lakers",
                "games": 82,
                "wins": 47,
                "losses": 35,
                "win_pct": 57.32,
                "avg_points": 116.2,
                "avg_points_allowed": 112.1,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "Lakers are 47-35" in text
    assert "57.32%" in text
    assert "116.20 points scored" in text


def test_deterministic_team_head_to_head_summary() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=["team_a", "team_b", "games", "team_a_wins", "team_b_wins", "team_a_win_pct"],
        rows=[
            {
                "team_a": "Lakers",
                "team_b": "Celtics",
                "games": 20,
                "team_a_wins": 12,
                "team_b_wins": 8,
                "team_a_win_pct": 60.0,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "Lakers vs Celtics has produced 20 games" in text
    assert "12-8" in text
    assert "60.00%" in text


def test_deterministic_single_game_high_summary() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "metric_name",
            "metric_value",
            "game_date",
            "season_label",
            "opponent_team",
        ],
        rows=[
            {
                "player_name": "Stephen Curry",
                "metric_name": "points",
                "metric_value": 62,
                "game_date": "2021-01-03",
                "season_label": "2020-21",
                "opponent_team": "Portland Trail Blazers",
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "top single-game points output" in text
    assert "62" in text
    assert "2021-01-03" in text


def test_player_ranking_summary_not_misread_as_profile() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "games",
            "avg_points",
            "avg_assists",
            "avg_rebounds",
            "metric_value",
        ],
        rows=[
            {
                "player_name": "Nikola Jokic",
                "games": 42,
                "avg_points": 28.76,
                "avg_assists": 10.52,
                "avg_rebounds": 12.52,
                "metric_value": 10.52,
            },
            {
                "player_name": "Cade Cunningham",
                "games": 49,
                "avg_points": 25.53,
                "avg_assists": 9.76,
                "avg_rebounds": 5.76,
                "metric_value": 9.76,
            },
        ],
    )

    text = insight.summarize("q", result)

    assert text.startswith("Top players from this query:")


def test_deterministic_player_profile_summary_avg_operation() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=["player_name", "metric_name", "stat_operation", "games", "requested_value"],
        rows=[
            {
                "player_name": "LeBron James",
                "metric_name": "assists",
                "stat_operation": "avg",
                "games": 20,
                "requested_value": 8.5,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "LeBron James averaged 8.50 assists" in text
