from agent.templates import TemplateSQLBuilder
from agent.types import IntentType, ResolvedContext, ResolvedEntity



def test_conditional_template_defaults_regular_scope() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        teams=[ResolvedEntity(id="1610612737", name="Hawks")],
        players=[ResolvedEntity(id="1629027.0", name="Trae Young")],
        game_scope="regular",
        thresholds={"points_more_than": 25.0},
    )

    plan = builder.build(IntentType.CONDITIONAL_TEAM_PERFORMANCE, context)

    assert plan is not None
    assert "g.game_type = 'regular'" in plan.sql
    assert plan.params[-1] == 25.0



def test_conditional_template_with_season_filter_joins_seasons() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        teams=[ResolvedEntity(id="1610612747", name="Lakers")],
        players=[ResolvedEntity(id="2544", name="LeBron James")],
        game_scope="regular",
        seasons=["2023-24"],
        thresholds={"points_over": 30.0},
    )

    plan = builder.build(IntentType.CONDITIONAL_TEAM_PERFORMANCE, context)

    assert plan is not None
    assert "JOIN seasons s ON s.season_id = g.season_id" in plan.sql
    assert "s.season_label = %s" in plan.sql


def test_ranking_template_uses_metric() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(ranking_metric="assists", ranking_limit=10)

    plan = builder.build(IntentType.PLAYER_RANKING, context)

    assert plan is not None
    assert "ORDER BY avg_assists DESC" in plan.sql
    assert "LIMIT 10" in plan.sql


def test_player_threshold_count_template() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="201566", name="Russell Westbrook")],
        game_scope="regular",
        thresholds={"points_at_least": 25.0},
    )

    plan = builder.build(IntentType.PLAYER_THRESHOLD_COUNT, context)

    assert plan is not None
    assert "games_meeting_threshold" in plan.sql
    assert "pgs.points >=" in plan.sql
    assert plan.params[-1] == 25.0


def test_player_profile_summary_with_opponent_filter() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="201566", name="Russell Westbrook")],
        teams=[ResolvedEntity(id="1610612744", name="Warriors")],
        against_mode=True,
        game_scope="playoffs",
        primary_metric="assists",
        stat_operation="sum",
    )

    plan = builder.build(IntentType.PLAYER_PROFILE_SUMMARY, context)

    assert plan is not None
    assert "g.away_team_id = %s" in plan.sql
    assert "g.game_type = 'playoffs'" in plan.sql
    assert "SUM(COALESCE(pgs.assists, 0))" in plan.sql
    assert "requested_value" in plan.sql


def test_player_single_game_high_template() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="201939", name="Stephen Curry")],
        primary_metric="points",
        game_scope="regular",
    )

    plan = builder.build(IntentType.PLAYER_SINGLE_GAME_HIGH, context)

    assert plan is not None
    assert "ORDER BY pgs.points DESC" in plan.sql
    assert "LIMIT 1" in plan.sql


def test_team_record_summary_template() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        teams=[ResolvedEntity(id="1610612747", name="Lakers")],
        seasons=["2023-24"],
    )

    plan = builder.build(IntentType.TEAM_RECORD_SUMMARY, context)

    assert plan is not None
    assert "SUM(CASE WHEN tgr.is_win = 0 THEN 1 ELSE 0 END) AS losses" in plan.sql
    assert "s.season_label = %s" in plan.sql
    assert plan.params[-1] == "2023-24"


def test_team_head_to_head_template() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        teams=[
            ResolvedEntity(id="1610612747", name="Lakers"),
            ResolvedEntity(id="1610612738", name="Celtics"),
        ],
        game_scope="all",
    )

    plan = builder.build(IntentType.TEAM_HEAD_TO_HEAD, context)

    assert plan is not None
    assert "team_a_wins" in plan.sql
    assert "g.home_team_id = %s AND g.away_team_id = %s" in plan.sql


def test_team_ranking_template() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(primary_metric="opponent_points", ranking_limit=5)

    plan = builder.build(IntentType.TEAM_RANKING, context)

    assert plan is not None
    assert "ORDER BY metric_value ASC" in plan.sql
    assert "LIMIT 5" in plan.sql


def test_player_profile_summary_uses_season_range_clause() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(
        players=[ResolvedEntity(id="2544", name="LeBron James")],
        primary_metric="assists",
        stat_operation="sum",
        seasons=["2014-15", "2015-16", "2016-17"],
    )

    plan = builder.build(IntentType.PLAYER_PROFILE_SUMMARY, context)

    assert plan is not None
    assert "s.season_label IN (%s, %s, %s)" in plan.sql
    assert plan.params[-3:] == ("2014-15", "2015-16", "2016-17")
