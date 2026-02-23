from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "fixtures" / "sample"
RAW_DIR = ROOT / "data" / "raw"

FILES = ["teams.csv", "players.csv", "games.csv", "player_game_stats.csv"]


def bootstrap(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for name in FILES:
        src = SAMPLE_DIR / name
        dst = RAW_DIR / name

        if dst.exists() and not force:
            print(f"Skipping existing file: {dst}")
            continue

        shutil.copy2(src, dst)
        print(f"Copied {src} -> {dst}")


if __name__ == "__main__":
    bootstrap(force=False)
