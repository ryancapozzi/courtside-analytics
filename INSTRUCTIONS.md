# INSTRUCTIONS.md

## Purpose
This repository is an NBA analytics assistant that answers natural-language questions using PostgreSQL-backed SQL (template-first, LLM fallback).

This file is designed for AI agents (Claude/GPT/Gemini) to quickly understand how to set up, run, and test the project.

## Tech Stack
- Python `>=3.11`
- PostgreSQL (recommended via Docker)
- Ollama (local LLM runtime)
- CLI entrypoint: `courtside`

## Repository Layout
- `agent/` core NL-to-SQL pipeline (intent, entities, SQL generation, validation, insights)
- `cli/` Typer CLI app
- `data_ingestion/` source profiling + ETL
- `database/` schema and DB setup scripts
- `tests/` pytest suite
- `data/` raw input, processed artifacts, benchmarks/results

## Environment Setup
1. Create and activate virtualenv:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install project + dev deps:
```bash
make install
```

3. Create env file:
```bash
cp .env.example .env
```

4. Ensure `.env` contains:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/courtside
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_SQL_MODEL=llama3.1:8b
OLLAMA_SUMMARY_MODEL=llama3.1:8b
SQL_MAX_ROWS=500
SQL_TIMEOUT_SECONDS=30
```

## External Services

### PostgreSQL (Docker)
Start once:
```bash
docker run --name courtside-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=courtside \
  -p 5432:5432 \
  -d postgres:16
```

Start existing container:
```bash
docker start courtside-postgres
```

### Ollama
Start server (if not running):
```bash
ollama serve
```

Pull model once:
```bash
ollama pull llama3.1:8b
```

## Data Preparation
Input CSVs go in `data/raw/`.

Accepted files:
- games: `games.csv` or `Games.csv`
- player stats: `player_game_stats.csv` / `PlayerStatistics.csv` / `PlayerGameStats.csv`
- optional refs: `teams.csv` / `players.csv`

Optional local sample data:
```bash
make sample-data
```

## Build / Initialize Database
Run from repo root with venv active:
```bash
make profile-source
make setup-db
make load-data
make audit-db
```

## Run the App
Single query via CLI:
```bash
courtside ask "How did the Atlanta Hawks perform when Trae Young scored more than 25 points?"
```

Convenience target:
```bash
make run-cli
```

## Test and Lint
Run tests:
```bash
make test
```

Run lint:
```bash
make lint
```

## Benchmark Evaluation
Run benchmark set:
```bash
courtside evaluate \
  --benchmark-path data/benchmarks/questions.json \
  --output-path data/benchmarks/results/latest.json
```

Expected artifacts:
- `data/benchmarks/results/latest.json`
- `data/benchmarks/results/latest_summary.json`
- `data/benchmarks/results/latest_report.md`

## AI Agent Workflow (Recommended)
1. Read this file, then `README.md`.
2. Verify `.env` and services (Postgres + Ollama).
3. Ensure data exists in `data/raw/` (or run `make sample-data`).
4. Execute DB pipeline: `make profile-source && make setup-db && make load-data && make audit-db`.
5. Run `make test`.
6. Validate behavior with at least one `courtside ask` query.

## Common Failure Checks
- DB connection errors: confirm `docker ps` and `DATABASE_URL`.
- Ollama errors: confirm `ollama serve` and model pulled.
- Missing CLI/module issues: reactivate venv and rerun `make install`.
