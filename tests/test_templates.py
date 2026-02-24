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



def test_ranking_template_uses_metric() -> None:
    builder = TemplateSQLBuilder()
    context = ResolvedContext(ranking_metric="assists")

    plan = builder.build(IntentType.PLAYER_RANKING, context)

    assert plan is not None
    assert "ORDER BY avg_assists DESC" in plan.sql


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
