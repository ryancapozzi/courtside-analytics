# Demo Runbook

This runbook is the fastest path to a clean end-to-end demo of Courtside Analytics.

## Prerequisites

- Python 3.11+
- Docker Desktop running
- Ollama installed
- Local NBA CSVs copied into `data/raw/`

Minimum required source files:

- `Games.csv` or `games.csv`
- `PlayerStatistics.csv` or `player_game_stats.csv`

## One-Time Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

Edit `.env` if your local ports or model names differ from the defaults.

## Start Required Services

Start PostgreSQL with Docker:

```bash
docker run --name courtside-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=courtside \
  -p 5432:5432 \
  -d postgres:16
```

If the container already exists:

```bash
docker start courtside-postgres
```

Start Ollama:

```bash
ollama serve
```

In another terminal, make sure the model exists:

```bash
ollama pull llama3.1:8b
ollama list
```

## Load and Validate Data

```bash
source .venv/bin/activate
make check-data
make profile-source
make setup-db
make load-data
make audit-db
```

## Demo Flow

### 1. Ask a representative team-condition question

```bash
courtside ask "How did the Atlanta Hawks perform when Trae Young scored more than 25 points?"
```

### 2. Ask a ranking question

```bash
courtside ask "Who are the top players by average assists in 2023-24?"
```

### 3. Ask a trend/comparison question

```bash
courtside ask "Compare the Lakers and Warriors by season win percentage."
```

### 4. Run the benchmark workflow

```bash
courtside evaluate \
  --benchmark-path data/benchmarks/questions.json \
  --output-path data/benchmarks/results/latest.json
```

Expected outputs:

- `data/benchmarks/results/latest.json`
- `data/benchmarks/results/latest_summary.json`
- `data/benchmarks/results/latest_report.md`

### 5. Generate a chart artifact

```bash
courtside chart "Compare the Lakers and Warriors by season win percentage."
```

## What to Show During the Demo

- the natural-language question
- the grounded answer
- the SQL/provenance information
- the benchmark workflow output path
- at least one generated chart

## Troubleshooting

If Postgres is unreachable:

```bash
docker ps
docker start courtside-postgres
```

If Ollama is unreachable:

```bash
curl http://127.0.0.1:11434/api/tags
ollama serve
```

If the CLI cannot find data:

```bash
make check-data
```

If the environment is missing dependencies:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
```
