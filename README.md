# courtside-analytics

Agentic NBA analytics assistant that answers natural-language basketball questions with database-grounded analysis.

## Scope (Locked)
- NBA game-level analytics (no play-by-play for MVP)
- Season window determined by the selected free dataset
- Hybrid NL pipeline: templates first, LLM SQL fallback second
- Local Ollama for LLM components
- Visualization as optional, unprioritized stretch

## Core Pipeline
1. Intent classification
2. Entity resolution (teams, players, seasons)
3. Template SQL builder (primary path)
4. LLM SQL fallback (only if no template match)
5. SQL guardrails + execution
6. Insight generation from computed results

Default behavior:
- Queries use `regular` season games unless the prompt explicitly asks for `playoffs`, `preseason`, or `all games`.

## Repo Structure
- `data_ingestion/`: ingestion and ETL scripts
- `database/`: schema and database setup
- `agent/`: intent, entity, SQL generation, guardrails, insights
- `analytics/`: optional visualization and stats helpers
- `cli/`: command-line interface
- `data/benchmarks/`: benchmark prompts and evaluation artifacts
- `docs/`: architecture and planning docs

## Prerequisites
Install these once on your Mac:
1. Docker Desktop (for PostgreSQL)
2. Python 3.11+ (3.14 works)
3. Ollama (local LLM runtime)

Optional install via Homebrew:
```bash
brew install python
brew install --cask docker
brew install --cask ollama
```

## One-Time Setup
1. Clone and enter the repo:
```bash
git clone git@github.com:ryancapozzi/courtside-analytics.git
cd /Users/ryancapozzi/courtside-analytics
```

2. Create and activate virtualenv:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
python -m pip install -e '.[dev]'
```

4. Create local env config:
```bash
cp .env.example .env
```

5. Edit `.env` with:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/courtside
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_SQL_MODEL=llama3.1:8b
OLLAMA_SUMMARY_MODEL=llama3.1:8b
SQL_MAX_ROWS=500
SQL_TIMEOUT_SECONDS=30
```

## Start PostgreSQL (Docker)
Open Docker Desktop once and keep it running.

Create and start a persistent local container:
```bash
docker run --name courtside-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=courtside \
  -p 5432:5432 \
  -d postgres:16
```

If container already exists:
```bash
docker start courtside-postgres
```

Check status:
```bash
docker ps
```

## Start Ollama
If Ollama app is not already running:
```bash
ollama serve
```

In another terminal, pull model once:
```bash
ollama pull llama3.1:8b
ollama list
```

Health check:
```bash
curl http://127.0.0.1:11434/api/tags
```

## Data Input
Use one of these paths:
1. Real dataset (recommended): place CSVs in `data/raw/`
2. Sample dataset: run `make sample-data`

Accepted source filenames include:
- Games: `games.csv` or `Games.csv`
- Player stats: `player_game_stats.csv`, `PlayerStatistics.csv`, `PlayerGameStats.csv`
- Optional refs: `teams.csv` / `players.csv`

See details in `docs/source_setup.md` and `data_ingestion/data_contract.md`.

## First Run (Build DB + Load Data)
From repo root with virtualenv active:
```bash
make profile-source
make setup-db
make load-data
make audit-db
```

Expected ETL behavior:
- Some legacy/special-event rows may be dropped when they cannot be joined safely.
- This is intentional and prevents full-load failures.

## Ask Questions
With virtualenv active:
```bash
courtside ask "How did the Atlanta Hawks perform when Trae Young scored more than 25 points?"
```

Examples:
```bash
courtside ask "How did the Hawks perform in the playoffs when Trae Young scored more than 25 points?"
courtside ask "Who are the top players by average assists in 2023-24?"
courtside ask "Compare the Lakers and Warriors by season win percentage."
```

## Benchmark Evaluation
Run full 30-question benchmark:
```bash
courtside evaluate \
  --benchmark-path data/benchmarks/questions.json \
  --output-path data/benchmarks/results/latest.json
```

Outputs:
- `data/benchmarks/results/latest.json`
- `data/benchmarks/results/latest_summary.json`
- `data/benchmarks/results/latest_report.md`

Question set location:
- `data/benchmarks/questions.json`

## Typical Daily Workflow
1. Start Docker Desktop
2. `docker start courtside-postgres` (if needed)
3. Start Ollama app or `ollama serve`
4. `cd /Users/ryancapozzi/courtside-analytics`
5. `source .venv/bin/activate`
6. Run `courtside ask "..."`

## Stop Services
```bash
docker stop courtside-postgres
```

If running `ollama serve` in terminal, stop with `Ctrl+C`.

## Troubleshooting
`ModuleNotFoundError` when running `courtside`:
```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Cannot connect to Postgres on `localhost:5432`:
```bash
docker ps
docker start courtside-postgres
```

Ollama not responding:
```bash
ollama serve
curl http://127.0.0.1:11434/api/tags
```

No data in DB after load:
```bash
make profile-source
make load-data
make audit-db
```

## Current Status
Core MVP is implemented with end-to-end CLI querying, guarded SQL execution, real dataset ETL, and benchmark evaluation artifacts.
