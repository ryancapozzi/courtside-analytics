from agent.query_spec import QueryFamily
from agent.spec_builder import QuerySpecBuilder
from agent.types import IntentType, ResolvedContext, ResolvedEntity


def test_query_spec_builder_player_stat_sum() -> None:
    builder = QuerySpecBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="2544", name="LeBron James")],
        seasons=["2014-15", "2015-16"],
        primary_metric="assists",
        stat_operation="sum",
    )

    spec = builder.build("How many assists did LeBron James have from 2014 to 2015?", context)

    assert spec.family == QueryFamily.PLAYER_STAT
    assert spec.intent == IntentType.PLAYER_PROFILE_SUMMARY
    assert spec.metric == "assists"
    assert spec.operation == "sum"


def test_query_spec_builder_player_stat_by_season() -> None:
    builder = QuerySpecBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="2544", name="LeBron James")],
        primary_metric="assists",
        metric_explicit=True,
        stat_operation="avg",
        operation_explicit=False,
    )

    spec = builder.build("Show LeBron James assists by season", context)

    assert spec.family == QueryFamily.PLAYER_STAT
    assert spec.group_by == "season"
    assert spec.operation == "sum"


def test_query_spec_builder_team_comparison_sets_grouping() -> None:
    builder = QuerySpecBuilder()
    context = ResolvedContext(
        teams=[
            ResolvedEntity(id="1610612747", name="Lakers"),
            ResolvedEntity(id="1610612744", name="Warriors"),
        ]
    )

    spec = builder.build("Compare the Lakers and Warriors by season win percentage.", context)

    assert spec.family == QueryFamily.TEAM_COMPARISON
    assert spec.group_by == "season"


def test_query_spec_builder_broad_player_prompt_uses_profile_mode() -> None:
    builder = QuerySpecBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="201939", name="Stephen Curry")],
        teams=[ResolvedEntity(id="1610612747", name="Lakers")],
        against_mode=True,
        profile_request=True,
    )

    spec = builder.build("How does Stephen Curry perform against the Lakers in the playoffs?", context)

    assert spec.family == QueryFamily.PLAYER_STAT
    assert spec.response_mode == "profile"
