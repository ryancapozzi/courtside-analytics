from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .normalize import apply_aliases, normalize_columns
from .column_aliases import COLUMN_ALIASES


@dataclass
class SourceProfile:
    games_rows: int
    player_game_stats_rows: int
    distinct_seasons: list[str]
    first_game_date: str | None
    last_game_date: str | None



def profile_raw_source(raw_data_dir: Path) -> SourceProfile:
    games_path = raw_data_dir / "games.csv"
    pgs_path = raw_data_dir / "player_game_stats.csv"

    if not games_path.exists() or not pgs_path.exists():
        raise FileNotFoundError(
            "Expected games.csv and player_game_stats.csv in data/raw/."
        )

    games_df = pd.read_csv(games_path)
    games_df = normalize_columns(games_df)
    games_df = apply_aliases(games_df, COLUMN_ALIASES["games"])

    pgs_df = pd.read_csv(pgs_path)

    if "season_label" not in games_df.columns:
        raise ValueError("games.csv must contain season label (or alias).")

    if "game_date" not in games_df.columns:
        raise ValueError("games.csv must contain game date (or alias).")

    date_series = games_df["game_date"].astype(str).str[:10]

    seasons = sorted(games_df["season_label"].dropna().astype(str).unique().tolist())

    return SourceProfile(
        games_rows=len(games_df),
        player_game_stats_rows=len(pgs_df),
        distinct_seasons=seasons,
        first_game_date=date_series.min() if not date_series.empty else None,
        last_game_date=date_series.max() if not date_series.empty else None,
    )


if __name__ == "__main__":
    raw_dir = Path("data/raw")
    profile = profile_raw_source(raw_dir)
    print(json.dumps(asdict(profile), indent=2))
