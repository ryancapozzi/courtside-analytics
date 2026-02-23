from pathlib import Path

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
