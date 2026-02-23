# Data Ingestion

This project uses a dataset-first ingestion path. Place raw CSV files in `data/raw/` using these filenames:

- `teams.csv`
- `players.csv`
- `games.csv`
- `player_game_stats.csv`

Then run:
- `python3 -m data_ingestion.run_etl`

The loader handles common column aliases and upserts rows into PostgreSQL.
