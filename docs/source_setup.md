# Source Setup

## Recommended path (dataset-first)

1. Pick a free NBA game-level dataset with:
   - games (one row per game)
   - player game stats (one row per player per game)
   - optional teams and players reference tables
2. Export CSVs into `data/raw/` with names:
   - `games.csv`
   - `player_game_stats.csv`
   - optional: `teams.csv`, `players.csv`

## Validate source coverage
Run:
- `make profile-source`

This prints season list and date range so scope automatically matches dataset coverage.

## Load and audit database
Run:
- `make setup-db`
- `make load-data`
- `make audit-db`

Audit checks include:
- table row counts
- date coverage
- number of distinct seasons
- orphan stat rows
- games missing scores
