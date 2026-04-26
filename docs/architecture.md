# System Architecture

## Overview

Courtside Analytics is a constrained analytics assistant for NBA data. The system is designed to answer natural-language basketball questions with database-grounded outputs rather than free-form model responses. Its architecture emphasizes:

- deterministic query generation when possible
- LLM assistance only where it adds value
- SQL safety and schema validation before execution
- analyst-style conclusions backed by actual results

## End-to-End Flow

User Question
-> CLI entry point (`courtside ask`)
-> intent + entity resolution
-> structured `QuerySpec`
-> deterministic SQL builder
-> optional Ollama fallback for unmatched cases
-> SQL validation and guardrails
-> PostgreSQL execution
-> insight generation / optional charting
-> grounded output (answer + SQL + provenance)

## Technology Stack

### Interface Layer
- `Typer`: command-line commands for asking questions, loading data, auditing the database, evaluating the benchmark, and generating charts
- `Rich`: formatted terminal output for readable answers and summaries

### Application Layer
- `agent/pipeline.py`: orchestration of question understanding, SQL generation, validation, and answer production
- `agent/entities.py`: resolution of teams, players, seasons, and threshold references
- `agent/spec_builder.py`: conversion from natural-language intent into a structured `QuerySpec`
- `agent/spec_sql.py`: deterministic SQL generation for supported question families
- `agent/insight.py`: conclusion, evidence, and caveat generation from query results

### Safety and Reasoning Layer
- `SQLGlot`: parsing and validating generated SQL
- `agent/sql_validator.py`: read-only enforcement, table restrictions, and row limits
- Ollama local models: fallback SQL generation and controlled summary rewriting only when deterministic handling is insufficient

### Data and Execution Layer
- PostgreSQL: primary execution engine for normalized NBA analytics data
- `database/schema.sql`: schema for teams, players, seasons, games, and player-game statistics
- `data_ingestion/`: ETL, profiling, normalization, and source compatibility handling

### Analysis and Evaluation Layer
- `analytics/evaluation.py`: benchmark scoring and report generation
- `analytics/visualization.py`: chart support for supported result shapes
- `matplotlib`: rendering report figures and chart outputs
- `tests/`: regression coverage across parsing, SQL safety, insights, CLI behavior, and evaluation formatting

## How the Components Interact

1. The user asks a natural-language question through the CLI.
2. The agent resolves referenced teams, players, seasons, and thresholds.
3. The system converts the request into a `QuerySpec` so the intended analysis is explicit before SQL generation.
4. Supported query families are translated into deterministic SQL.
5. If a question does not match a supported template cleanly, the system can use Ollama as a constrained fallback rather than defaulting to unconstrained generation.
6. SQLGlot-based guardrails validate the statement before any execution occurs.
7. PostgreSQL runs the approved query against the ingested NBA dataset.
8. The resulting rows are converted into a concise answer with supporting evidence and caveats.
9. Optional evaluation and visualization layers provide benchmark artifacts and charts for reproducibility and presentation.

## Output Contract

The intended output is not just a table. A successful response should provide:

- a grounded analytical conclusion
- the core metric or comparison used
- enough evidence for the result to be interpretable
- SQL/provenance visibility when needed
- a clarification prompt when the request is too ambiguous to answer responsibly

## Design Principles

- Prefer deterministic behavior over opaque generation.
- Keep LLM usage behind explicit control points.
- Treat ambiguity as something to resolve, not ignore.
- Make outputs explainable enough for reports and demos.
- Preserve a clean separation between ingestion, planning, execution, and narration.

## Supporting Artifacts

These files are the main companion materials for understanding and reproducing the architecture:

- `README.md`
- `docs/source_setup.md`
- `docs/demo_runbook.md`
- `docs/plan_v4.md`
- `data/benchmarks/questions.json`
