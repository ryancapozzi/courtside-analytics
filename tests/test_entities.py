from agent.entities import EntityResolver


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
