from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import psycopg

from .column_aliases import COLUMN_ALIASES
from .normalize import apply_aliases, normalize_columns


@dataclass
class ETLReport:
    teams_loaded: int = 0
    players_loaded: int = 0
    seasons_loaded: int = 0
    games_loaded: int = 0
    player_game_stats_loaded: int = 0


class ETLLoader:
    def __init__(self, database_url: str, raw_data_dir: Path):
        self.database_url = database_url
        self.raw_data_dir = raw_data_dir

    def run(self) -> ETLReport:
        report = ETLReport()
        with psycopg.connect(self.database_url) as conn:
            teams_df = self._maybe_read("teams.csv", "teams")
            players_df = self._maybe_read("players.csv", "players")
            games_df = self._required_read("games.csv", "games")
            stats_df = self._required_read("player_game_stats.csv", "player_game_stats")

            if teams_df.empty:
                teams_df = self._derive_teams_from_games(games_df)
            if players_df.empty:
                players_df = self._derive_players_from_stats(stats_df)

            seasons_df = self._derive_seasons(games_df)

            self._upsert_teams(conn, teams_df)
            report.teams_loaded = len(teams_df)

            self._upsert_players(conn, players_df)
            report.players_loaded = len(players_df)

            self._upsert_seasons(conn, seasons_df)
            report.seasons_loaded = len(seasons_df)

            games_with_season = self._attach_season_ids(conn, games_df)
            self._upsert_games(conn, games_with_season)
            report.games_loaded = len(games_with_season)

            self._upsert_player_game_stats(conn, stats_df)
            report.player_game_stats_loaded = len(stats_df)

            conn.commit()

        return report

    def _maybe_read(self, file_name: str, alias_key: str) -> pd.DataFrame:
        path = self.raw_data_dir / file_name
        if not path.exists():
            return pd.DataFrame()
        return self._read_with_aliases(path, alias_key)

    def _required_read(self, file_name: str, alias_key: str) -> pd.DataFrame:
        path = self.raw_data_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")
        return self._read_with_aliases(path, alias_key)

    def _read_with_aliases(self, path: Path, alias_key: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        df = normalize_columns(df)
        df = apply_aliases(df, COLUMN_ALIASES[alias_key])
        return df

    def _derive_teams_from_games(self, games_df: pd.DataFrame) -> pd.DataFrame:
        home_teams = games_df[["home_team_id"]].rename(columns={"home_team_id": "team_id"})
        away_teams = games_df[["away_team_id"]].rename(columns={"away_team_id": "team_id"})
        teams = pd.concat([home_teams, away_teams], ignore_index=True).drop_duplicates()
        teams["team_name"] = teams["team_id"].astype(str)
        teams["abbreviation"] = None
        teams["city"] = None
        teams["conference"] = None
        teams["division"] = None
        return teams

    def _derive_players_from_stats(self, stats_df: pd.DataFrame) -> pd.DataFrame:
        players = stats_df[["player_id"]].drop_duplicates().copy()
        players["player_name"] = stats_df.get("player_name", stats_df["player_id"]).astype(str)
        players["first_name"] = None
        players["last_name"] = None
        players["position"] = None
        return players

    def _derive_seasons(self, games_df: pd.DataFrame) -> pd.DataFrame:
        labels = games_df["season_label"].astype(str).dropna().drop_duplicates()
        rows: list[dict[str, object]] = []
        for label in labels:
            start_year, end_year = self._parse_season_years(label)
            rows.append(
                {
                    "season_label": label,
                    "start_year": start_year,
                    "end_year": end_year,
                }
            )
        return pd.DataFrame(rows)

    def _parse_season_years(self, season_label: str) -> tuple[int, int]:
        text = season_label.strip()
        if "-" in text:
            left, right = text.split("-", maxsplit=1)
            start_year = int(left)
            if len(right) == 2:
                end_year = int(f"{left[:2]}{right}")
            else:
                end_year = int(right)
            return start_year, end_year

        if len(text) == 4 and text.isdigit():
            year = int(text)
            return year, year + 1

        raise ValueError(f"Unsupported season format: {season_label}")

    def _upsert_teams(self, conn: psycopg.Connection, teams_df: pd.DataFrame) -> None:
        required = ["team_id", "team_name"]
        self._ensure_columns(teams_df, required, "teams")

        rows = teams_df[
            ["team_id", "team_name", "abbreviation", "city", "conference", "division"]
        ].fillna(value=pd.NA)

        sql = """
        INSERT INTO teams (team_id, team_name, abbreviation, city, conference, division)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (team_id)
        DO UPDATE SET
          team_name = EXCLUDED.team_name,
          abbreviation = EXCLUDED.abbreviation,
          city = EXCLUDED.city,
          conference = EXCLUDED.conference,
          division = EXCLUDED.division;
        """

        self._executemany(conn, sql, rows.itertuples(index=False, name=None))

    def _upsert_players(self, conn: psycopg.Connection, players_df: pd.DataFrame) -> None:
        required = ["player_id", "player_name"]
        self._ensure_columns(players_df, required, "players")

        rows = players_df[["player_id", "player_name", "first_name", "last_name", "position"]].fillna(
            value=pd.NA
        )

        sql = """
        INSERT INTO players (player_id, player_name, first_name, last_name, position)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (player_id)
        DO UPDATE SET
          player_name = EXCLUDED.player_name,
          first_name = EXCLUDED.first_name,
          last_name = EXCLUDED.last_name,
          position = EXCLUDED.position;
        """

        self._executemany(conn, sql, rows.itertuples(index=False, name=None))

    def _upsert_seasons(self, conn: psycopg.Connection, seasons_df: pd.DataFrame) -> None:
        required = ["season_label", "start_year", "end_year"]
        self._ensure_columns(seasons_df, required, "seasons")

        rows = seasons_df[["season_label", "start_year", "end_year"]]

        sql = """
        INSERT INTO seasons (season_label, start_year, end_year)
        VALUES (%s, %s, %s)
        ON CONFLICT (season_label)
        DO UPDATE SET
          start_year = EXCLUDED.start_year,
          end_year = EXCLUDED.end_year;
        """

        self._executemany(conn, sql, rows.itertuples(index=False, name=None))

    def _attach_season_ids(self, conn: psycopg.Connection, games_df: pd.DataFrame) -> pd.DataFrame:
        with conn.cursor() as cur:
            cur.execute("SELECT season_id, season_label FROM seasons")
            season_map = {label: season_id for season_id, label in cur.fetchall()}

        df = games_df.copy()
        df["season_id"] = df["season_label"].astype(str).map(season_map)
        if df["season_id"].isna().any():
            missing = df[df["season_id"].isna()]["season_label"].unique()
            raise ValueError(f"Unresolved season labels in games data: {missing}")

        return df

    def _upsert_games(self, conn: psycopg.Connection, games_df: pd.DataFrame) -> None:
        required = ["game_id", "season_id", "game_date", "home_team_id", "away_team_id"]
        self._ensure_columns(games_df, required, "games")

        df = games_df.copy()
        if "game_type" not in df.columns:
            df["game_type"] = "regular"
        if "winner_team_id" not in df.columns:
            df["winner_team_id"] = None
        if "home_points" not in df.columns:
            df["home_points"] = None
        if "away_points" not in df.columns:
            df["away_points"] = None

        df["game_date"] = df["game_date"].apply(self._normalize_date)

        rows = df[
            [
                "game_id",
                "season_id",
                "game_date",
                "game_type",
                "home_team_id",
                "away_team_id",
                "home_points",
                "away_points",
                "winner_team_id",
            ]
        ]

        sql = """
        INSERT INTO games (
          game_id,
          season_id,
          game_date,
          game_type,
          home_team_id,
          away_team_id,
          home_points,
          away_points,
          winner_team_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (game_id)
        DO UPDATE SET
          season_id = EXCLUDED.season_id,
          game_date = EXCLUDED.game_date,
          game_type = EXCLUDED.game_type,
          home_team_id = EXCLUDED.home_team_id,
          away_team_id = EXCLUDED.away_team_id,
          home_points = EXCLUDED.home_points,
          away_points = EXCLUDED.away_points,
          winner_team_id = EXCLUDED.winner_team_id;
        """

        self._executemany(conn, sql, rows.itertuples(index=False, name=None))

    def _upsert_player_game_stats(self, conn: psycopg.Connection, stats_df: pd.DataFrame) -> None:
        required = ["game_id", "player_id", "team_id"]
        self._ensure_columns(stats_df, required, "player_game_stats")

        df = stats_df.copy()
        for optional_col in [
            "starter",
            "minutes",
            "points",
            "rebounds",
            "assists",
            "steals",
            "blocks",
            "turnovers",
            "fouls",
            "plus_minus",
            "fg_made",
            "fg_attempts",
            "three_made",
            "three_attempts",
            "ft_made",
            "ft_attempts",
            "offensive_rebounds",
            "defensive_rebounds",
        ]:
            if optional_col not in df.columns:
                df[optional_col] = None

        rows = df[
            [
                "game_id",
                "player_id",
                "team_id",
                "starter",
                "minutes",
                "points",
                "rebounds",
                "assists",
                "steals",
                "blocks",
                "turnovers",
                "fouls",
                "plus_minus",
                "fg_made",
                "fg_attempts",
                "three_made",
                "three_attempts",
                "ft_made",
                "ft_attempts",
                "offensive_rebounds",
                "defensive_rebounds",
            ]
        ]

        sql = """
        INSERT INTO player_game_stats (
          game_id,
          player_id,
          team_id,
          starter,
          minutes,
          points,
          rebounds,
          assists,
          steals,
          blocks,
          turnovers,
          fouls,
          plus_minus,
          fg_made,
          fg_attempts,
          three_made,
          three_attempts,
          ft_made,
          ft_attempts,
          offensive_rebounds,
          defensive_rebounds
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (game_id, player_id)
        DO UPDATE SET
          team_id = EXCLUDED.team_id,
          starter = EXCLUDED.starter,
          minutes = EXCLUDED.minutes,
          points = EXCLUDED.points,
          rebounds = EXCLUDED.rebounds,
          assists = EXCLUDED.assists,
          steals = EXCLUDED.steals,
          blocks = EXCLUDED.blocks,
          turnovers = EXCLUDED.turnovers,
          fouls = EXCLUDED.fouls,
          plus_minus = EXCLUDED.plus_minus,
          fg_made = EXCLUDED.fg_made,
          fg_attempts = EXCLUDED.fg_attempts,
          three_made = EXCLUDED.three_made,
          three_attempts = EXCLUDED.three_attempts,
          ft_made = EXCLUDED.ft_made,
          ft_attempts = EXCLUDED.ft_attempts,
          offensive_rebounds = EXCLUDED.offensive_rebounds,
          defensive_rebounds = EXCLUDED.defensive_rebounds;
        """

        self._executemany(conn, sql, rows.itertuples(index=False, name=None))

    def _ensure_columns(self, df: pd.DataFrame, required_cols: list[str], dataset_name: str) -> None:
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Dataset '{dataset_name}' missing required columns: {missing}")

    def _normalize_date(self, value: object) -> str:
        if value is None:
            raise ValueError("game_date cannot be null")

        text = str(value)
        if len(text) >= 10:
            text = text[:10]
        datetime.strptime(text, "%Y-%m-%d")
        return text

    def _executemany(self, conn: psycopg.Connection, sql: str, rows: Iterable[tuple]) -> None:
        with conn.cursor() as cur:
            cur.executemany(sql, list(rows))
