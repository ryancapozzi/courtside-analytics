from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from analytics.evaluation import evaluate_results, render_markdown_report
from analytics.visualization import build_chart_plan, save_line_chart
from agent.config import load_agent_settings
from agent.pipeline import AnalyticsAgent
from data_ingestion.file_discovery import DATASET_FILE_CANDIDATES, find_existing_file
from data_ingestion.profile_source import profile_raw_source


app = typer.Typer(help="Courtside Analytics CLI")
console = Console()


@app.command()
def ask(question: str) -> None:
    """Answer a natural-language analytics question."""
    settings = load_agent_settings()
    agent = AnalyticsAgent(settings)

    response = agent.answer(question)

    console.print("\n[bold cyan]Answer[/bold cyan]")
    console.print(response.answer)

    if response.sql:
        console.print("\n[bold cyan]SQL[/bold cyan]")
        console.print(response.sql)

    console.print("\n[bold cyan]Provenance[/bold cyan]")
    console.print_json(data=response.provenance)

    if response.rows:
        table = Table(title="Top Rows")
        for col in response.columns:
            table.add_column(col)

        for row in response.rows[:10]:
            table.add_row(*(str(row.get(col, "")) for col in response.columns))

        console.print(table)


@app.command("setup-db")
def setup_db() -> None:
    """Apply database schema."""
    subprocess.run(["python3", "database/setup_db.py"], check=True)
    console.print("[green]Database schema applied.[/green]")


@app.command("load-data")
def load_data() -> None:
    """Run ETL against CSVs in data/raw."""
    subprocess.run(["python3", "-m", "data_ingestion.run_etl"], check=True)
    console.print("[green]ETL run completed.[/green]")


@app.command("check-data")
def check_data(raw_dir: str = "data/raw") -> None:
    """Validate required raw CSVs exist and print source coverage."""
    raw_path = Path(raw_dir)
    games_path = find_existing_file(raw_path, "games")
    stats_path = find_existing_file(raw_path, "player_game_stats")

    console.print(f"[bold cyan]Raw Data Check[/bold cyan]\nDirectory: {raw_path.resolve()}")

    if games_path is None or stats_path is None:
        missing: list[str] = []
        if games_path is None:
            missing.append(f"games file ({', '.join(DATASET_FILE_CANDIDATES['games'])})")
        if stats_path is None:
            missing.append(
                "player stats file "
                f"({', '.join(DATASET_FILE_CANDIDATES['player_game_stats'])})"
            )

        console.print(f"[red]Missing required input:[/red] {', '.join(missing)}")
        raise typer.Exit(code=1)

    console.print(f"[green]Found games file:[/green] {games_path.name}")
    console.print(f"[green]Found player stats file:[/green] {stats_path.name}")

    profile = profile_raw_source(raw_path)
    console.print_json(
        data={
            "games_rows": profile.games_rows,
            "player_game_stats_rows": profile.player_game_stats_rows,
            "first_game_date": profile.first_game_date,
            "last_game_date": profile.last_game_date,
            "distinct_seasons": profile.distinct_seasons,
        }
    )


@app.command("audit-db")
def audit_db() -> None:
    """Audit loaded data quality and coverage."""
    subprocess.run(["python3", "database/audit_db.py"], check=True)


@app.command()
def evaluate(
    benchmark_path: str = "data/benchmarks/questions.json",
    output_path: str = "data/benchmarks/results/latest.json",
) -> None:
    """Run the 30-question benchmark and save outputs."""
    settings = load_agent_settings()
    agent = AnalyticsAgent(settings)

    questions = json.loads(Path(benchmark_path).read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []

    for item in questions:
        prompt = item["question"]
        response = agent.answer(prompt)
        results.append(
            {
                "id": item["id"],
                "question": prompt,
                "intent": response.intent.value,
                "sql_source": response.sql_source,
                "row_count": len(response.rows),
                "answer": response.answer,
                "sql": response.sql,
                "provenance": response.provenance,
            }
        )
        console.print(f"Processed benchmark question {item['id']}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")

    summary, findings = evaluate_results(questions, results)
    summary_payload = {
        "total_questions": summary.total_questions,
        "sql_generated": summary.sql_generated,
        "non_empty_results": summary.non_empty_results,
        "intent_matches": summary.intent_matches,
        "template_ratio": summary.template_ratio,
        "findings_count": len(findings),
    }

    summary_path = output.with_name(f"{output.stem}_summary.json")
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    report_path = output.with_name(f"{output.stem}_report.md")
    report_path.write_text(render_markdown_report(summary, findings), encoding="utf-8")

    console.print("\nBenchmark summary:")
    console.print_json(data=summary_payload)
    console.print(f"\nSaved benchmark results to: {output}")
    console.print(f"Saved benchmark summary to: {summary_path}")
    console.print(f"Saved benchmark report to: {report_path}")


@app.command()
def chart(
    question: str,
    output_path: str = "data/processed/latest_chart.png",
) -> None:
    """Run a supported query and save a chart for trend/comparison style outputs."""
    settings = load_agent_settings()
    agent = AnalyticsAgent(settings)

    response = agent.answer(question)
    plan = build_chart_plan(response.columns, response.rows, response.provenance)

    if plan is None:
        console.print("[yellow]No supported chart shape was produced for this query.[/yellow]")
        console.print("Try a team trend, team comparison, or season-grouped player stat query.")
        return

    chart_path = save_line_chart(
        plan.dataframe,
        x=plan.x,
        y=plan.y,
        title=plan.title,
        output_path=Path(output_path),
    )
    console.print(f"[green]Saved chart to:[/green] {chart_path}")


if __name__ == "__main__":
    app()
