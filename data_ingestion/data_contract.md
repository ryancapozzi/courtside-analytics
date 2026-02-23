# Data Contract (CSV Inputs)

Place files in `data/raw/` with these canonical columns (aliases supported by loader):

## teams.csv
- `team_id` (required)
- `team_name` (required)
- `abbreviation`
- `city`
- `conference`
- `division`

## players.csv
- `player_id` (required)
- `player_name` (required)
- `first_name`
- `last_name`
- `position`

## games.csv
- `game_id` (required)
- `season_label` (required, e.g. `2023-24`)
- `game_date` (required, `YYYY-MM-DD`)
- `home_team_id` (required)
- `away_team_id` (required)
- `home_points`
- `away_points`
- `winner_team_id`
- `game_type`

## player_game_stats.csv
- `game_id` (required)
- `player_id` (required)
- `team_id` (required)
- Optional box score columns:
  - `minutes`, `points`, `rebounds`, `assists`, `steals`, `blocks`,
    `turnovers`, `fouls`, `plus_minus`, `fg_made`, `fg_attempts`,
    `three_made`, `three_attempts`, `ft_made`, `ft_attempts`,
    `offensive_rebounds`, `defensive_rebounds`

Notes:
- If `teams.csv` is missing, teams are derived from game rows.
- If `players.csv` is missing, players are derived from stat rows.
