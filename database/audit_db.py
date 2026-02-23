from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

import psycopg
from dotenv import load_dotenv


@dataclass
class TableCounts:
    seasons: int
    teams: int
    players: int
    games: int
    player_game_stats: int


@dataclass
class Coverage:
    first_game_date: str | None
    last_game_date: str | None
    season_count: int


@dataclass
class AuditReport:
    table_counts: TableCounts
    coverage: Coverage
    orphan_player_game_stats: int
    games_missing_scores: int



def run_audit(database_url: str) -> AuditReport:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM seasons),
                  (SELECT COUNT(*) FROM teams),
                  (SELECT COUNT(*) FROM players),
                  (SELECT COUNT(*) FROM games),
                  (SELECT COUNT(*) FROM player_game_stats)
                """
            )
            counts = cur.fetchone()
            table_counts = TableCounts(
                seasons=counts[0],
                teams=counts[1],
                players=counts[2],
                games=counts[3],
                player_game_stats=counts[4],
            )

            cur.execute(
                """
                SELECT MIN(game_date)::text, MAX(game_date)::text, COUNT(DISTINCT season_id)
                FROM games
                """
            )
            first_game_date, last_game_date, season_count = cur.fetchone()
            coverage = Coverage(
                first_game_date=first_game_date,
                last_game_date=last_game_date,
                season_count=season_count,
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM player_game_stats pgs
                LEFT JOIN games g ON g.game_id = pgs.game_id
                WHERE g.game_id IS NULL
                """
            )
            orphan_player_game_stats = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM games
                WHERE home_points IS NULL OR away_points IS NULL
                """
            )
            games_missing_scores = cur.fetchone()[0]

    return AuditReport(
        table_counts=table_counts,
        coverage=coverage,
        orphan_player_game_stats=orphan_player_game_stats,
        games_missing_scores=games_missing_scores,
    )


if __name__ == "__main__":
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")

    report = run_audit(url)
    print(json.dumps(asdict(report), indent=2))
