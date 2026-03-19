from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from agent.types import IntentType


runner = CliRunner()


class DummyResponse:
    def __init__(self, columns, rows, provenance):
        self.answer = "ok"
        self.intent = IntentType.TEAM_TREND
        self.sql = "SELECT 1"
        self.sql_source = "query_spec"
        self.columns = columns
        self.rows = rows
        self.provenance = provenance


class DummyAgent:
    def __init__(self, response):
        self._response = response

    def answer(self, question: str):
        return self._response


def test_chart_command_saves_supported_chart(monkeypatch, tmp_path: Path) -> None:
    response = DummyResponse(
        columns=["season_label", "games", "wins", "win_pct", "avg_points"],
        rows=[
            {"season_label": "2022-23", "games": 82, "wins": 43, "win_pct": 52.44, "avg_points": 117.1},
            {"season_label": "2023-24", "games": 82, "wins": 47, "win_pct": 57.32, "avg_points": 118.4},
        ],
        provenance={"teams": ["Lakers"]},
    )

    monkeypatch.setattr("cli.main.load_agent_settings", lambda: object())
    monkeypatch.setattr("cli.main.AnalyticsAgent", lambda settings: DummyAgent(response))
    monkeypatch.setattr("cli.main.save_line_chart", lambda df, x, y, title, output_path: output_path)

    output_path = tmp_path / "trend.png"
    result = runner.invoke(app, ["chart", "Show the trend of the Lakers over time.", "--output-path", str(output_path)])

    assert result.exit_code == 0
    assert "Saved chart to:" in result.stdout
    assert "trend.png" in result.stdout


def test_chart_command_reports_unsupported_shape(monkeypatch) -> None:
    response = DummyResponse(
        columns=["team_name", "games", "wins", "losses"],
        rows=[{"team_name": "Lakers", "games": 82, "wins": 47, "losses": 35}],
        provenance={"teams": ["Lakers"]},
    )

    monkeypatch.setattr("cli.main.load_agent_settings", lambda: object())
    monkeypatch.setattr("cli.main.AnalyticsAgent", lambda settings: DummyAgent(response))

    result = runner.invoke(app, ["chart", "What is the Lakers record this season?"])

    assert result.exit_code == 0
    assert "No supported chart shape was produced" in result.stdout


def test_chart_command_reports_missing_plot_dependency(monkeypatch) -> None:
    response = DummyResponse(
        columns=["season_label", "games", "wins", "win_pct", "avg_points"],
        rows=[
            {"season_label": "2022-23", "games": 82, "wins": 43, "win_pct": 52.44, "avg_points": 117.1},
            {"season_label": "2023-24", "games": 82, "wins": 47, "win_pct": 57.32, "avg_points": 118.4},
        ],
        provenance={"teams": ["Lakers"]},
    )

    monkeypatch.setattr("cli.main.load_agent_settings", lambda: object())
    monkeypatch.setattr("cli.main.AnalyticsAgent", lambda settings: DummyAgent(response))
    monkeypatch.setattr(
        "cli.main.save_line_chart",
        lambda df, x, y, title, output_path: (_ for _ in ()).throw(
            RuntimeError("Visualization requires matplotlib and valid chart data.")
        ),
    )

    result = runner.invoke(app, ["chart", "Show the trend of the Lakers over time."])

    assert result.exit_code == 1
    assert "Visualization requires matplotlib and valid chart data." in result.stdout
    assert "Install chart dependencies" in result.stdout
