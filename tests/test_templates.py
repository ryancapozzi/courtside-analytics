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
