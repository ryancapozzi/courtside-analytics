from agent.entities import Catalog, EntityResolver
from agent.types import ResolvedEntity


def test_resolve_seasons_this_season() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2022-23", "2023-24", "2024-25"]

    resolved = resolver._resolve_seasons("How are the Lakers doing this season?", seasons)

    assert resolved == ["2024-25"]


def test_resolve_seasons_last_season() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2022-23", "2023-24", "2024-25"]

    resolved = resolver._resolve_seasons("What was the Lakers record last season?", seasons)

    assert resolved == ["2023-24"]


def test_resolve_seasons_numeric_year_maps_to_label() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2022-23", "2023-24", "2024-25"]

    resolved = resolver._resolve_seasons("How did they do in 2024?", seasons)

    assert resolved == ["2024-25"]


def test_resolve_seasons_expands_year_range() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18"]

    resolved = resolver._resolve_seasons(
        "How many assists has LeBron James had from 2014 to 2016?",
        seasons,
    )

    assert resolved == ["2014-15", "2015-16", "2016-17"]


def test_resolve_seasons_expands_season_label_range() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18"]

    resolved = resolver._resolve_seasons(
        "How many assists from 2014-15 to 2016-17?",
        seasons,
    )

    assert resolved == ["2014-15", "2015-16", "2016-17"]


def test_resolve_seasons_numeric_year_can_map_from_end_year() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2022-23", "2023-24", "2024-25"]

    resolved = resolver._resolve_seasons("How did they do in 2025?", seasons)

    assert resolved == ["2024-25"]


def test_resolve_seasons_unknown_year_returns_empty() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    seasons = ["2022-23", "2023-24", "2024-25"]

    resolved = resolver._resolve_seasons("How did they do in 2035?", seasons)

    assert resolved == []


def test_resolve_players_skips_fuzzy_boston_match_for_team_comparison() -> None:
    resolver = EntityResolver(database_url="postgresql://unused")
    catalog = Catalog(
        teams=[],
        players=[
            ("213471", "Brandon Boston Jr."),
            ("203530", "Lawrence Boston"),
        ],
        seasons=[],
    )
    matched_teams = [
        ResolvedEntity(id="ATL", name="Atlanta Hawks"),
        ResolvedEntity(id="BOS", name="Boston Celtics"),
    ]

    resolved = resolver._resolve_players(
        "Compare the Atlanta Hawks and Boston Celtics by season win percentage.",
        catalog,
        matched_teams,
    )

    assert resolved == []
