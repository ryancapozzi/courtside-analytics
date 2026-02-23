from __future__ import annotations

from .config import load_settings
from .loaders import ETLLoader


def main() -> None:
    settings = load_settings()
    loader = ETLLoader(database_url=settings.database_url, raw_data_dir=settings.raw_data_dir)
    report = loader.run()

    print("ETL complete")
    print(f"  teams: {report.teams_loaded}")
    print(f"  players: {report.players_loaded}")
    print(f"  seasons: {report.seasons_loaded}")
    print(f"  games: {report.games_loaded}")
    print(f"  player_game_stats: {report.player_game_stats_loaded}")


if __name__ == "__main__":
    main()
