from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from agent.types import IntentType


runner = CliRunner()


class DummyResponse:
    def __init__(self, columns, rows, provenance, answer="ok", sql="SELECT 1"):
        self.answer = answer
        self.intent = IntentType.TEAM_TREND
        self.sql = sql
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
    monkeypatch.setattr(
        "cli.main.save_line_chart",
        lambda df, x, y, title, output_path, kind="line", y_label="Value": output_path,
    )

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
        lambda df, x, y, title, output_path, kind="line", y_label="Value": (_ for _ in ()).throw(
            RuntimeError("Visualization requires matplotlib and valid chart data.")
        ),
    )

    result = runner.invoke(app, ["chart", "Show the trend of the Lakers over time."])

    assert result.exit_code == 1
    assert "Visualization requires matplotlib and valid chart data." in result.stdout
    assert "Install chart dependencies" in result.stdout


def test_ask_command_shows_clarification_heading(monkeypatch) -> None:
    response = DummyResponse(
        columns=[],
        rows=[],
        provenance={"clarification_required": True, "intent": "unknown", "ambiguities": ["No player detected."]},
        answer="I need one more detail before I can run a safe query.",
        sql="",
    )

    monkeypatch.setattr("cli.main.load_agent_settings", lambda: object())
    monkeypatch.setattr("cli.main.AnalyticsAgent", lambda settings: DummyAgent(response))

    result = runner.invoke(app, ["ask", "How did the Hawks do when he scored 30?"])

    assert result.exit_code == 0
    assert "Needs Clarification" in result.stdout
    assert "I need one more detail" in result.stdout
    assert "\nSQL\n" not in result.stdout


def test_evaluate_command_reports_new_quality_metrics(monkeypatch, tmp_path: Path) -> None:
    benchmark_path = tmp_path / "questions.json"
    output_path = tmp_path / "results.json"
    benchmark_path.write_text(
        '[{"id": 1, "question": "What is the Lakers record this season?", "expected_intent": "team_record_summary", "expected_min_rows": 1}]',
        encoding="utf-8",
    )

    response = DummyResponse(
        columns=["team_name", "games", "wins", "losses"],
        rows=[{"team_name": "Lakers", "games": 82, "wins": 47, "losses": 35}],
        provenance={
            "intent": "team_record_summary",
            "query_family": "team_stat",
            "source": "query_spec",
            "row_count": 1,
            "clarification_required": False,
        },
        answer="Across the regular season sample, the Lakers went 47-35 with a 57.32% win rate.",
    )
    response.intent = IntentType.TEAM_RECORD_SUMMARY

    monkeypatch.setattr("cli.main.load_agent_settings", lambda: object())
    monkeypatch.setattr("cli.main.AnalyticsAgent", lambda settings: DummyAgent(response))

    result = runner.invoke(
        app,
        ["evaluate", "--benchmark-path", str(benchmark_path), "--output-path", str(output_path)],
    )

    assert result.exit_code == 0
    assert "answers_with_numeric_support" in result.stdout
    assert "answers_with_scope_or_caveat" in result.stdout
    assert "provenance_complete" in result.stdout
