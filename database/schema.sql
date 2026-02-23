-- Core schema for courtside-analytics MVP

CREATE TABLE IF NOT EXISTS seasons (
  season_id SERIAL PRIMARY KEY,
  season_label TEXT NOT NULL UNIQUE,
  start_year INTEGER NOT NULL,
  end_year INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teams (
  team_id TEXT PRIMARY KEY,
  team_name TEXT NOT NULL,
  abbreviation TEXT,
  city TEXT,
  conference TEXT,
  division TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS players (
  player_id TEXT PRIMARY KEY,
  player_name TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  position TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS games (
  game_id TEXT PRIMARY KEY,
  season_id INTEGER NOT NULL REFERENCES seasons(season_id),
  game_date DATE NOT NULL,
  game_type TEXT NOT NULL DEFAULT 'regular',
  home_team_id TEXT NOT NULL REFERENCES teams(team_id),
  away_team_id TEXT NOT NULL REFERENCES teams(team_id),
  home_points INTEGER,
  away_points INTEGER,
  winner_team_id TEXT REFERENCES teams(team_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (home_team_id <> away_team_id)
);

CREATE TABLE IF NOT EXISTS player_game_stats (
  game_id TEXT NOT NULL REFERENCES games(game_id),
  player_id TEXT NOT NULL REFERENCES players(player_id),
  team_id TEXT NOT NULL REFERENCES teams(team_id),
  starter BOOLEAN,
  minutes NUMERIC(6,2),
  points INTEGER,
  rebounds INTEGER,
  assists INTEGER,
  steals INTEGER,
  blocks INTEGER,
  turnovers INTEGER,
  fouls INTEGER,
  plus_minus INTEGER,
  fg_made INTEGER,
  fg_attempts INTEGER,
  three_made INTEGER,
  three_attempts INTEGER,
  ft_made INTEGER,
  ft_attempts INTEGER,
  offensive_rebounds INTEGER,
  defensive_rebounds INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (game_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_games_season ON games(season_id);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_game_stats(team_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_points ON player_game_stats(points);

-- View to simplify team-level game outcomes.
CREATE OR REPLACE VIEW team_game_results AS
SELECT
  g.game_id,
  g.season_id,
  g.game_date,
  g.game_type,
  g.home_team_id AS team_id,
  g.away_team_id AS opponent_team_id,
  g.home_points AS team_points,
  g.away_points AS opponent_points,
  CASE
    WHEN g.home_points > g.away_points THEN 1
    ELSE 0
  END AS is_win,
  TRUE AS is_home
FROM games g
UNION ALL
SELECT
  g.game_id,
  g.season_id,
  g.game_date,
  g.game_type,
  g.away_team_id AS team_id,
  g.home_team_id AS opponent_team_id,
  g.away_points AS team_points,
  g.home_points AS opponent_points,
  CASE
    WHEN g.away_points > g.home_points THEN 1
    ELSE 0
  END AS is_win,
  FALSE AS is_home
FROM games g;
