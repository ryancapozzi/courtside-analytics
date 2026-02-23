# Data Ingestion

This project uses a dataset-first ingestion path. Place raw CSV files in `data/raw/`.

Accepted game filenames:
- `games.csv`
- `Games.csv`

Accepted player-stat filenames:
- `player_game_stats.csv`
- `PlayerStatistics.csv`
- `PlayerGameStats.csv`

Optional reference files:
- `teams.csv` / `Teams.csv`
- `players.csv` / `Players.csv`

Then run:
- `python3 -m data_ingestion.run_etl`

The loader handles common column aliases and upserts rows into PostgreSQL.
