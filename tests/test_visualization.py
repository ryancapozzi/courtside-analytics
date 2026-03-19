from pathlib import Path

from analytics.visualization import build_chart_plan


def test_build_chart_plan_for_team_comparison() -> None:
    columns = ["season_label", "team_name", "games", "wins", "win_pct"]
    rows = [
        {"season_label": "2022-23", "team_name": "Lakers", "games": 82, "wins": 43, "win_pct": 52.44},
        {"season_label": "2022-23", "team_name": "Warriors", "games": 82, "wins": 44, "win_pct": 53.66},
        {"season_label": "2023-24", "team_name": "Lakers", "games": 82, "wins": 47, "win_pct": 57.32},
        {"season_label": "2023-24", "team_name": "Warriors", "games": 82, "wins": 46, "win_pct": 56.10},
    ]

    plan = build_chart_plan(columns, rows, {"teams": ["Lakers", "Warriors"]})

    assert plan is not None
    assert plan.x == "season_label"
    assert plan.y == ["Lakers", "Warriors"]
    assert "Lakers vs Warriors" in plan.title
    assert list(plan.dataframe.columns) == ["season_label", "Lakers", "Warriors"]


def test_build_chart_plan_for_season_grouped_player_stat() -> None:
    columns = [
        "player_name",
        "season_label",
        "metric_name",
        "stat_operation",
        "games",
        "requested_value",
    ]
    rows = [
        {
            "player_name": "LeBron James",
            "season_label": "2022-23",
            "metric_name": "assists",
            "stat_operation": "sum",
            "games": 55,
            "requested_value": 375,
        },
        {
            "player_name": "LeBron James",
            "season_label": "2023-24",
            "metric_name": "assists",
            "stat_operation": "sum",
            "games": 71,
            "requested_value": 612,
        },
    ]

    plan = build_chart_plan(columns, rows, {"players": ["LeBron James"]})

    assert plan is not None
    assert plan.x == "season_label"
    assert plan.y == "metric_value"
    assert "LeBron James Assists by Season" == plan.title
    assert list(plan.dataframe.columns) == ["season_label", "metric_value"]


def test_build_chart_plan_returns_none_for_non_chart_shape() -> None:
    columns = ["team_name", "games", "wins", "losses"]
    rows = [{"team_name": "Lakers", "games": 82, "wins": 47, "losses": 35}]

    plan = build_chart_plan(columns, rows, {"teams": ["Lakers"]})

    assert plan is None
