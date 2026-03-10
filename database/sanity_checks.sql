-- Lightweight read-only sanity checks for courtside-analytics.
-- Run with: psql "$DATABASE_URL" -f database/sanity_checks.sql

-- 1) Core table row counts
SELECT 'seasons' AS table_name, COUNT(*) AS row_count FROM seasons
UNION ALL
SELECT 'teams', COUNT(*) FROM teams
UNION ALL
SELECT 'players', COUNT(*) FROM players
UNION ALL
SELECT 'games', COUNT(*) FROM games
UNION ALL
SELECT 'player_game_stats', COUNT(*) FROM player_game_stats;

-- 2) Date and season coverage
SELECT
  MIN(g.game_date) AS min_game_date,
  MAX(g.game_date) AS max_game_date,
  COUNT(DISTINCT s.season_label) AS season_count
FROM games g
JOIN seasons s ON s.season_id = g.season_id;

-- 3) Games with identical home/away team (should be 0)
SELECT COUNT(*) AS invalid_same_team_games
FROM games
WHERE home_team_id = away_team_id;

-- 4) Stats rows with team not in game participants (should be 0)
SELECT COUNT(*) AS stats_team_not_in_game
FROM player_game_stats pgs
JOIN games g ON g.game_id = pgs.game_id
WHERE pgs.team_id NOT IN (g.home_team_id, g.away_team_id);

-- 5) Stats rows with null/blank IDs (should be 0)
SELECT COUNT(*) AS stats_missing_required_ids
FROM player_game_stats
WHERE game_id IS NULL OR player_id IS NULL OR team_id IS NULL
   OR TRIM(game_id) = '' OR TRIM(player_id) = '' OR TRIM(team_id) = '';

-- 6) Games missing points (helps spot partial loads)
SELECT COUNT(*) AS games_missing_score
FROM games
WHERE home_points IS NULL OR away_points IS NULL;

-- 7) team_game_results consistency check (should equal games * 2)
SELECT
  (SELECT COUNT(*) FROM games) AS game_count,
  (SELECT COUNT(*) FROM team_game_results) AS team_game_results_count,
  (SELECT COUNT(*) FROM games) * 2 AS expected_team_game_results_count;
