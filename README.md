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

## Repo Structure
- `data_ingestion/`: ingestion and ETL scripts
- `database/`: schema and database setup
- `agent/`: intent, entity, SQL generation, guardrails, insights
- `analytics/`: optional visualization and stats helpers
- `cli/`: command-line interface
- `data/benchmarks/`: benchmark prompts and evaluation artifacts
- `docs/`: architecture and planning docs

## Quickstart
1. Create and activate a virtual environment.
2. Install dependencies:
   - `make install`
3. Copy environment template:
   - `cp .env.example .env`
4. Ensure PostgreSQL is running and update `DATABASE_URL`.
5. Ensure Ollama is running and the configured model is available.

## Current Status
This repository is now scaffolded for the agreed Plan v4 and ready for iterative implementation and evaluation.
