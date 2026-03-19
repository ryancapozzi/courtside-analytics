from agent.insight import InsightGenerator
from agent.query_spec import QueryFamily, QuerySpec
from agent.types import IntentType, QueryResult


class DummyOllama:
    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        return "dummy"


class NumericPreservingOllama:
    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        return "LeBron James recorded 688 total assists across 82 games. That equals 8.39 assists per game."


class HallucinatingOllama:
    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        return "LeBron James posted 9,999 assists in every season."


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

    spec = QuerySpec(
        family=QueryFamily.CONDITIONAL_TEAM_PERFORMANCE,
        intent=IntentType.CONDITIONAL_TEAM_PERFORMANCE,
        threshold_stat="points",
        threshold_operator=">=",
        threshold_value=30,
    )

    text = insight.summarize("q", result, spec)

    assert "137-115" in text
    assert "252 games" in text
    assert "54.37%" in text
    assert "33.23" in text
    assert "119.74" in text
    assert "30+ points" in text


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

    assert "John Wall cleared 25+ points in 145 games" in text
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

    assert text.startswith("Leaders in this result set")


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


def test_player_profile_view_summary_uses_multiple_core_stats() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "games",
            "avg_points",
            "avg_rebounds",
            "avg_assists",
            "avg_minutes",
            "avg_turnovers",
            "fg_pct",
            "three_pct",
            "ft_pct",
        ],
        rows=[
            {
                "player_name": "Stephen Curry",
                "games": 6,
                "avg_points": 26.67,
                "avg_rebounds": 5.83,
                "avg_assists": 6.67,
                "avg_minutes": 39.5,
                "avg_turnovers": 3.33,
                "fg_pct": 47.2,
                "three_pct": 39.1,
                "ft_pct": 92.0,
            }
        ],
    )

    text = insight.summarize("q", result)

    assert "26.67 points, 5.83 rebounds, and 6.67 assists" in text
    assert "39.50 minutes" in text
    assert "47.20% from the field" in text


def test_player_season_group_summary_uses_total_language_for_sum_queries() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "season_label",
            "metric_name",
            "stat_operation",
            "games",
            "requested_value",
        ],
        rows=[
            {
                "player_name": "LeBron James",
                "season_label": "2018-19",
                "metric_name": "assists",
                "stat_operation": "sum",
                "games": 55,
                "requested_value": 454,
            },
            {
                "player_name": "LeBron James",
                "season_label": "2019-20",
                "metric_name": "assists",
                "stat_operation": "sum",
                "games": 60,
                "requested_value": 636,
            },
        ],
    )

    text = insight.summarize("q", result)

    assert "season-by-season total" in text
    assert "636 total assists" in text


def test_rewrite_with_ollama_uses_natural_copy_when_numbers_preserved() -> None:
    insight = InsightGenerator(NumericPreservingOllama(), model="dummy")
    result = QueryResult(
        columns=["player_name", "metric_name", "stat_operation", "games", "requested_value", "per_game_value"],
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

    text = insight.summarize("How many assists did LeBron have?", result)

    assert text.startswith("LeBron James recorded 688 total assists")


def test_summarize_no_rows_returns_guidance() -> None:
    insight = InsightGenerator(DummyOllama(), model="dummy")
    result = QueryResult(columns=["team_name"], rows=[])

    text = insight.summarize("Any question", result)

    assert text.startswith("No rows matched the requested criteria.")


def test_deterministic_summary_ignores_generative_rewrite_layer() -> None:
    insight = InsightGenerator(HallucinatingOllama(), model="dummy")
    result = QueryResult(
        columns=[
            "player_name",
            "season_label",
            "metric_name",
            "stat_operation",
            "games",
            "requested_value",
        ],
        rows=[
            {
                "player_name": "LeBron James",
                "season_label": "2023-24",
                "metric_name": "assists",
                "stat_operation": "sum",
                "games": 67,
                "requested_value": 540,
            },
            {
                "player_name": "LeBron James",
                "season_label": "2024-25",
                "metric_name": "assists",
                "stat_operation": "sum",
                "games": 38,
                "requested_value": 564,
            },
        ],
    )

    text = insight.summarize("Show LeBron James assists by season", result)

    assert "season-by-season total" in text
    assert "9,999 assists" not in text
