from types import SimpleNamespace

from agent.pipeline import AnalyticsAgent
from agent.query_spec import QueryFamily, QuerySpec
from agent.types import IntentType, ResolvedContext


class DummyResolver:
    def __init__(self, context: ResolvedContext):
        self.context = context

    def resolve(self, question: str) -> ResolvedContext:
        return self.context


class DummySpecBuilder:
    def __init__(self, spec: QuerySpec):
        self.spec = spec

    def build(self, question: str, context: ResolvedContext) -> QuerySpec:
        return self.spec


class FailingQueries:
    def build(self, spec: QuerySpec, context: ResolvedContext):
        raise AssertionError("SQL builder should not run when clarification is required.")


def test_agent_returns_clarification_before_query_planning() -> None:
    context = ResolvedContext(ambiguities=["No player detected for conditional query."])
    spec = QuerySpec(
        family=QueryFamily.CONDITIONAL_TEAM_PERFORMANCE,
        intent=IntentType.CONDITIONAL_TEAM_PERFORMANCE,
    )

    agent = AnalyticsAgent.__new__(AnalyticsAgent)
    agent.settings = SimpleNamespace()
    agent.resolver = DummyResolver(context)
    agent.spec_builder = DummySpecBuilder(spec)
    agent.queries = FailingQueries()

    response = AnalyticsAgent.answer(agent, "How did the Hawks do when he scored 30?")

    assert response.sql == ""
    assert response.sql_source == "none"
    assert response.provenance["clarification_required"] is True
    assert "No player detected" in response.answer
