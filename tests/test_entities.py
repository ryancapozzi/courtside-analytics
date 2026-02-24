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

