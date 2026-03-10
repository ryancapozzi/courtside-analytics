from pathlib import Path

import pytest

from data_ingestion.profile_source import _derive_season_label
from data_ingestion.profile_source import profile_raw_source


def test_profile_source_from_sample_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    sample_dir = root / "fixtures" / "sample"

    profile = profile_raw_source(sample_dir)

    assert profile.games_rows == 2
    assert profile.player_game_stats_rows == 6
    assert profile.distinct_seasons == ["2023-24"]
    assert profile.first_game_date == "2023-10-25"
    assert profile.last_game_date == "2023-11-15"
    assert profile.games_file == "games.csv"
    assert profile.player_game_stats_file == "player_game_stats.csv"


def test_derive_season_label_boundary_dates() -> None:
    assert _derive_season_label("2024-06-30") == "2023-24"
    assert _derive_season_label("2024-07-01") == "2024-25"


def test_profile_source_missing_files_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        profile_raw_source(tmp_path)
