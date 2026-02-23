from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from .column_aliases import COLUMN_ALIASES
from .file_discovery import DATASET_FILE_CANDIDATES, find_existing_file
from .normalize import apply_aliases, normalize_columns


@dataclass
class SourceProfile:
    games_rows: int
    player_game_stats_rows: int
    distinct_seasons: list[str]
    first_game_date: str | None
    last_game_date: str | None
    games_file: str
    player_game_stats_file: str



def _derive_season_label(game_date: str) -> str:
    dt = datetime.strptime(game_date[:10], "%Y-%m-%d")
    start_year = dt.year if dt.month >= 7 else dt.year - 1
    end_year = (start_year + 1) % 100
    return f"{start_year}-{end_year:02d}"



def profile_raw_source(raw_data_dir: Path) -> SourceProfile:
    games_path = find_existing_file(raw_data_dir, "games")
    pgs_path = find_existing_file(raw_data_dir, "player_game_stats")

    if games_path is None or pgs_path is None:
        game_names = ", ".join(DATASET_FILE_CANDIDATES["games"])
        stats_names = ", ".join(DATASET_FILE_CANDIDATES["player_game_stats"])
        raise FileNotFoundError(
            f"Expected one games file ({game_names}) and one stats file ({stats_names}) in {raw_data_dir}."
        )

    games_df = pd.read_csv(games_path, low_memory=False)
    games_df = normalize_columns(games_df)
    games_df = apply_aliases(games_df, COLUMN_ALIASES["games"])

    pgs_df = pd.read_csv(pgs_path, low_memory=False)

    if "game_date" not in games_df.columns:
        raise ValueError("Games file must contain game date (or alias).")

    date_series = games_df["game_date"].astype(str).str[:10]

    if "season_label" in games_df.columns:
        season_series = games_df["season_label"].astype(str)
        empty = season_series.str.strip().eq("") | season_series.str.lower().eq("nan")
        season_series.loc[empty] = date_series.loc[empty].apply(_derive_season_label)
    else:
        season_series = date_series.apply(_derive_season_label)

    seasons = sorted(season_series.dropna().astype(str).unique().tolist())

    return SourceProfile(
        games_rows=len(games_df),
        player_game_stats_rows=len(pgs_df),
        distinct_seasons=seasons,
        first_game_date=date_series.min() if not date_series.empty else None,
        last_game_date=date_series.max() if not date_series.empty else None,
        games_file=games_path.name,
        player_game_stats_file=pgs_path.name,
    )


if __name__ == "__main__":
    raw_dir = Path("data/raw")
    profile = profile_raw_source(raw_dir)
    print(json.dumps(asdict(profile), indent=2))
