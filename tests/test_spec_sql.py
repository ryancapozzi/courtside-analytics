from agent.query_spec import QueryFamily, QuerySpec
from agent.spec_sql import QuerySQLBuilder
from agent.types import IntentType, ResolvedContext, ResolvedEntity


def test_player_stat_query_by_season_groups_rows() -> None:
    builder = QuerySQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="2544", name="LeBron James")],
        seasons=["2014-15", "2015-16", "2016-17"],
    )
    spec = QuerySpec(
        family=QueryFamily.PLAYER_STAT,
        intent=IntentType.PLAYER_PROFILE_SUMMARY,
        metric="assists",
        operation="sum",
        group_by="season",
    )

    plan = builder.build(spec, context)

    assert plan is not None
    assert "s.season_label" in plan.sql
    assert "GROUP BY p.player_name, s.start_year, s.season_label" in plan.sql
    assert "IN (%s, %s, %s)" in plan.sql


def test_player_stat_query_uses_query_spec_source() -> None:
    builder = QuerySQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="201939", name="Stephen Curry")],
        primary_metric="points",
    )
    spec = QuerySpec(
        family=QueryFamily.PLAYER_STAT,
        intent=IntentType.PLAYER_PROFILE_SUMMARY,
        metric="points",
        operation="avg",
    )

    plan = builder.build(spec, context)

    assert plan is not None
    assert plan.source == "query_spec"
    assert "requested_value" in plan.sql


def test_player_profile_query_returns_multi_metric_profile_shape() -> None:
    builder = QuerySQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="201939", name="Stephen Curry")],
        teams=[ResolvedEntity(id="1610612747", name="Lakers")],
        against_mode=True,
    )
    spec = QuerySpec(
        family=QueryFamily.PLAYER_STAT,
        intent=IntentType.PLAYER_PROFILE_SUMMARY,
        response_mode="profile",
        game_scope="playoffs",
        against_mode=True,
    )

    plan = builder.build(spec, context)

    assert plan is not None
    assert "avg_points" in plan.sql
    assert "avg_rebounds" in plan.sql
    assert "avg_assists" in plan.sql
    assert "fg_pct" in plan.sql
    assert "requested_value" not in plan.sql
