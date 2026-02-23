from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agent.config import load_agent_settings
from agent.pipeline import AnalyticsAgent
from database.audit_db import run_audit


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


@app.command("audit-db")
def audit_db() -> None:
    """Audit loaded data quality and coverage."""
    settings = load_agent_settings()
    report = run_audit(settings.database_url)
    console.print_json(data={
        "table_counts": report.table_counts.__dict__,
        "coverage": report.coverage.__dict__,
        "orphan_player_game_stats": report.orphan_player_game_stats,
        "games_missing_scores": report.games_missing_scores,
    })


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

    console.print(f"\nSaved benchmark results to: {output}")


if __name__ == "__main__":
    app()
