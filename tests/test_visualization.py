from pathlib import Path

from analytics.visualization import build_chart_plan, _select_tick_positions


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
    assert plan.kind == "line"
    assert plan.y_label == "Win Percentage"


def test_build_chart_plan_for_single_season_team_comparison_uses_bar_chart() -> None:
    columns = ["season_label", "team_name", "games", "wins", "win_pct"]
    rows = [
        {"season_label": "2023-24", "team_name": "Atlanta Hawks", "games": 2, "wins": 1, "win_pct": 50.0},
        {"season_label": "2023-24", "team_name": "Boston Celtics", "games": 2, "wins": 1, "win_pct": 50.0},
    ]

    plan = build_chart_plan(columns, rows, {"teams": ["Atlanta Hawks", "Boston Celtics"]})

    assert plan is not None
    assert plan.kind == "bar"
    assert plan.y == ["Atlanta Hawks", "Boston Celtics"]
    assert plan.y_label == "Win Percentage"


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
    assert plan.y_label == "Assists"


def test_build_chart_plan_returns_none_for_non_chart_shape() -> None:
    columns = ["team_name", "games", "wins", "losses"]
    rows = [{"team_name": "Lakers", "games": 82, "wins": 47, "losses": 35}]

    plan = build_chart_plan(columns, rows, {"teams": ["Lakers"]})

    assert plan is None


def test_select_tick_positions_thins_dense_season_labels() -> None:
    labels = [f"{year}-{(year + 1) % 100:02d}" for year in range(2000, 2012)]

    positions = _select_tick_positions(labels, max_tick_labels=6)

    assert positions == [0, 3, 6, 9, 11]
    assert positions[0] == 0
    assert positions[-1] == len(labels) - 1
