from __future__ import annotations

from pathlib import Path


DATASET_FILE_CANDIDATES: dict[str, list[str]] = {
    "games": ["games.csv", "Games.csv"],
    "player_game_stats": [
        "player_game_stats.csv",
        "PlayerGameStats.csv",
        "PlayerStatistics.csv",
        "playerstatistics.csv",
    ],
    "teams": ["teams.csv", "Teams.csv"],
    "players": ["players.csv", "Players.csv"],
}



def find_existing_file(raw_data_dir: Path, dataset_key: str) -> Path | None:
    for candidate in DATASET_FILE_CANDIDATES[dataset_key]:
        path = raw_data_dir / candidate
        if path.exists():
            return path
    return None
