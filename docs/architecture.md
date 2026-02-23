# System Architecture

## End-to-end Flow

User Question
-> Intent Classifier
-> Entity Resolver
-> Template SQL Builder
-> (Fallback) LLM SQL Generator
-> SQL Guardrails
-> PostgreSQL Execution
-> Insight Generator
-> CLI Output (answer + provenance)

## Design Principles
- Prefer deterministic query generation via templates.
- Use LLM SQL only as fallback.
- Never generate answer text without query execution results.
- Keep SQL execution constrained and auditable.
- Optimize for language quality and analytical clarity.

## Data Model (MVP)
- `teams`
- `players`
- `seasons`
- `games`
- `player_game_stats`

## Safety Guardrails
- Allow only `SELECT` statements.
- Disallow mutation keywords (`INSERT`, `UPDATE`, `DELETE`, `ALTER`, etc.).
- Restrict accessible tables/columns to project schema.
- Apply max-row and timeout limits.
