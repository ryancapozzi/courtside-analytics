from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import islice
from pathlib import Path
from typing import Iterable

import pandas as pd
import psycopg

from .column_aliases import COLUMN_ALIASES
from .file_discovery import DATASET_FILE_CANDIDATES, find_existing_file
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
            teams_df = self._maybe_read("teams")
            players_df = self._maybe_read("players")
            games_df = self._required_read("games")
            stats_df = self._required_read("player_game_stats")

            games_df = self._prepare_games(games_df)

            if teams_df.empty:
                teams_df = self._derive_teams_from_games(games_df)
            teams_df = self._prepare_teams(teams_df)

            if players_df.empty:
                players_df = self._derive_players_from_stats(stats_df)
            players_df = self._prepare_players(players_df)

            stats_df = self._prepare_player_stats(stats_df, teams_df, games_df)
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

    def _maybe_read(self, dataset_key: str) -> pd.DataFrame:
        path = find_existing_file(self.raw_data_dir, dataset_key)
        if path is None:
            return pd.DataFrame()
        return self._read_with_aliases(path, dataset_key)

    def _required_read(self, dataset_key: str) -> pd.DataFrame:
        path = find_existing_file(self.raw_data_dir, dataset_key)
        if path is None:
            candidates = ", ".join(DATASET_FILE_CANDIDATES[dataset_key])
            raise FileNotFoundError(
                f"Missing required dataset '{dataset_key}' in {self.raw_data_dir}. "
                f"Accepted names: {candidates}"
            )
        return self._read_with_aliases(path, dataset_key)

    def _read_with_aliases(self, path: Path, alias_key: str) -> pd.DataFrame:
        df = pd.read_csv(path, low_memory=False)
        df = normalize_columns(df)
        df = apply_aliases(df, COLUMN_ALIASES[alias_key])
        return df

    def _prepare_games(self, games_df: pd.DataFrame) -> pd.DataFrame:
        required = ["game_id", "game_date", "home_team_id", "away_team_id"]
        self._ensure_columns(games_df, required, "games")

        df = games_df.copy()
        df["game_id"] = df["game_id"].astype(str)
        df["home_team_id"] = df["home_team_id"].astype(str)
        df["away_team_id"] = df["away_team_id"].astype(str)

        if "season_label" not in df.columns:
            df["season_label"] = df["game_date"].apply(self._derive_season_label_from_date)
        else:
            mask = df["season_label"].isna() | (df["season_label"].astype(str).str.strip() == "")
            df.loc[mask, "season_label"] = df.loc[mask, "game_date"].apply(
                self._derive_season_label_from_date
            )
            df["season_label"] = df["season_label"].astype(str)

        if "game_type" not in df.columns:
            df["game_type"] = "regular"
        df["game_type"] = df["game_type"].apply(self._normalize_game_type)

        if "home_points" in df.columns:
            df["home_points"] = pd.to_numeric(df["home_points"], errors="coerce")
        if "away_points" in df.columns:
            df["away_points"] = pd.to_numeric(df["away_points"], errors="coerce")

        if "winner_team_id" not in df.columns:
            df["winner_team_id"] = None

        missing_winner = df["winner_team_id"].isna() | (df["winner_team_id"].astype(str).str.strip() == "")
        can_infer = df["home_points"].notna() & df["away_points"].notna()
        infer_mask = missing_winner & can_infer
        df.loc[infer_mask, "winner_team_id"] = df.loc[infer_mask].apply(
            lambda row: row["home_team_id"] if row["home_points"] > row["away_points"] else row["away_team_id"],
            axis=1,
        )

        if "winner_team_id" in df.columns:
            winner = df["winner_team_id"].astype(str)
            winner = winner.str.replace(r"\.0$", "", regex=True)
            df["winner_team_id"] = winner

        df["game_date"] = df["game_date"].apply(self._normalize_date)
        return df

    def _prepare_teams(self, teams_df: pd.DataFrame) -> pd.DataFrame:
        required = ["team_id", "team_name"]
        self._ensure_columns(teams_df, required, "teams")

        df = teams_df.copy()
        for optional_col in ["abbreviation", "city", "conference", "division"]:
            if optional_col not in df.columns:
                df[optional_col] = None

        df["team_id"] = df["team_id"].astype(str)
        df["team_name"] = df["team_name"].astype(str)
        df = df.drop_duplicates(subset=["team_id"], keep="first")
        return df

    def _derive_teams_from_games(self, games_df: pd.DataFrame) -> pd.DataFrame:
        home = pd.DataFrame(
            {
                "team_id": games_df["home_team_id"],
                "team_name": games_df.get("home_team_name", games_df["home_team_id"]).astype(str),
                "city": games_df.get("home_team_city"),
            }
        )
        away = pd.DataFrame(
            {
                "team_id": games_df["away_team_id"],
                "team_name": games_df.get("away_team_name", games_df["away_team_id"]).astype(str),
                "city": games_df.get("away_team_city"),
            }
        )

        teams = pd.concat([home, away], ignore_index=True)
        teams["team_id"] = teams["team_id"].astype(str)
        teams = teams.dropna(subset=["team_id"])

        teams["team_name"] = teams["team_name"].fillna(teams["team_id"]).astype(str)
        teams["abbreviation"] = None
        teams["conference"] = None
        teams["division"] = None

        teams = teams.drop_duplicates(subset=["team_id"], keep="first")
        return teams

    def _prepare_players(self, players_df: pd.DataFrame) -> pd.DataFrame:
        required = ["player_id", "player_name"]
        self._ensure_columns(players_df, required, "players")

        df = players_df.copy()
        for optional_col in ["first_name", "last_name", "position"]:
            if optional_col not in df.columns:
                df[optional_col] = None

        df["player_id"] = df["player_id"].astype(str)
        df["player_name"] = df["player_name"].astype(str)
        df = df.drop_duplicates(subset=["player_id"], keep="first")
        return df

    def _derive_players_from_stats(self, stats_df: pd.DataFrame) -> pd.DataFrame:
        df = stats_df.copy()
        if "player_name" not in df.columns:
            if "first_name" in df.columns and "last_name" in df.columns:
                full_name = df["first_name"].fillna("").astype(str).str.strip() + " "
                full_name += df["last_name"].fillna("").astype(str).str.strip()
                df["player_name"] = full_name.str.strip()
            else:
                df["player_name"] = df["player_id"].astype(str)

        players = (
            df[["player_id", "player_name", "first_name", "last_name"]]
            .drop_duplicates(subset=["player_id"], keep="first")
            .copy()
        )
        players["player_id"] = players["player_id"].astype(str)
        players["position"] = None
        return players

    def _prepare_player_stats(
        self,
        stats_df: pd.DataFrame,
        teams_df: pd.DataFrame,
        games_df: pd.DataFrame,
    ) -> pd.DataFrame:
        required = ["game_id", "player_id"]
        self._ensure_columns(stats_df, required, "player_game_stats")

        df = stats_df.copy()
        df["game_id"] = df["game_id"].astype(str)
        df["player_id"] = df["player_id"].astype(str)

        # Keep only stats rows that can join to a known game.
        game_ids = set(games_df["game_id"].astype(str))
        before_join_filter = len(df)
        df = df[df["game_id"].isin(game_ids)].copy()
        dropped_missing_games = before_join_filter - len(df)
        if dropped_missing_games:
            print(
                f"[ETL] Dropping {dropped_missing_games} player stat rows with game_id not found in games.csv"
            )

        if "player_name" not in df.columns:
            if "first_name" in df.columns and "last_name" in df.columns:
                full_name = df["first_name"].fillna("").astype(str).str.strip() + " "
                full_name += df["last_name"].fillna("").astype(str).str.strip()
                df["player_name"] = full_name.str.strip()
            else:
                df["player_name"] = df["player_id"]

        if "team_id" not in df.columns:
            df["team_id"] = None

        if "player_team_id" in df.columns:
            mask = df["team_id"].isna()
            df.loc[mask, "team_id"] = df.loc[mask, "player_team_id"]

        if {"player_team_name", "player_team_city"}.issubset(df.columns):
            team_map = {
                (
                    str(row.team_name).strip().lower(),
                    str(row.city).strip().lower() if pd.notna(row.city) else "",
                ): str(row.team_id)
                for row in teams_df.itertuples(index=False)
            }

            name_only: dict[str, str] = {}
            grouped = teams_df.groupby(teams_df["team_name"].astype(str).str.lower())["team_id"]
            for key, values in grouped:
                unique = values.astype(str).unique()
                if len(unique) == 1:
                    name_only[key] = unique[0]

            def resolve_team_id(row: pd.Series) -> str | None:
                if pd.notna(row.get("team_id")) and str(row.get("team_id")).strip() not in {"", "nan"}:
                    return str(row.get("team_id"))
                team_name = str(row.get("player_team_name", "")).strip().lower()
                team_city = str(row.get("player_team_city", "")).strip().lower()
                if not team_name:
                    return None
                exact = team_map.get((team_name, team_city))
                if exact:
                    return exact
                return name_only.get(team_name)

            df["team_id"] = df.apply(resolve_team_id, axis=1)

        if "is_home" in df.columns:
            game_side_map = games_df.set_index("game_id")[["home_team_id", "away_team_id"]].to_dict("index")

            def fill_team_from_home_flag(row: pd.Series) -> str | None:
                if pd.notna(row.get("team_id")) and str(row.get("team_id")).strip() not in {"", "nan"}:
                    return str(row.get("team_id"))
                game_id = str(row.get("game_id", ""))
                side = game_side_map.get(game_id)
                if side is None:
                    return None
                home_flag = pd.to_numeric(row.get("is_home"), errors="coerce")
                if pd.isna(home_flag):
                    return None
                if int(home_flag) == 1:
                    return str(side["home_team_id"])
                return str(side["away_team_id"])

            df["team_id"] = df.apply(fill_team_from_home_flag, axis=1)

        unresolved_mask = df["team_id"].isna() | (df["team_id"].astype(str).str.strip().isin({"", "nan"}))
        unresolved_count = int(unresolved_mask.sum())
        if unresolved_count:
            print(
                f"[ETL] Dropping {unresolved_count} player stat rows with unresolved team mapping"
            )
            df = df[~unresolved_mask].copy()

        df["team_id"] = df["team_id"].astype(str)

        for numeric_col in [
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
            if numeric_col in df.columns:
                df[numeric_col] = pd.to_numeric(df[numeric_col], errors="coerce")

        return df

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

    def _derive_season_label_from_date(self, value: object) -> str:
        game_date = datetime.strptime(self._normalize_date(value), "%Y-%m-%d")
        start_year = game_date.year if game_date.month >= 7 else game_date.year - 1
        end_year = (start_year + 1) % 100
        return f"{start_year}-{end_year:02d}"

    def _normalize_game_type(self, value: object) -> str:
        if value is None or str(value).strip() == "" or str(value).lower() == "nan":
            return "regular"

        text = str(value).strip().lower()
        if "regular" in text:
            return "regular"
        if "playoff" in text:
            return "playoffs"
        if "pre" in text:
            return "preseason"
        return text.replace(" ", "_")

    def _executemany(self, conn: psycopg.Connection, sql: str, rows: Iterable[tuple]) -> None:
        iterator = iter(rows)
        with conn.cursor() as cur:
            while True:
                batch = list(islice(iterator, 10_000))
                if not batch:
                    break
                cur.executemany(sql, batch)
