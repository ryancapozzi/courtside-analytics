from __future__ import annotations

from .config import AgentSettings
from .db import QueryExecutor
from .entities import EntityResolver
from .insight import InsightGenerator
from .intents import classify_intent
from .ollama_client import OllamaClient
from .schema_context import fetch_schema_context
from .sql_fallback import SQLFallbackGenerator
from .sql_validator import SQLGuardrails, SQLValidationError
from .templates import TemplateSQLBuilder
from .types import AgentResponse, SQLPlan


ALLOWED_TABLES = {
    "teams",
    "players",
    "seasons",
    "games",
    "player_game_stats",
    "team_game_results",
}


class AnalyticsAgent:
    def __init__(self, settings: AgentSettings):
        self.settings = settings

        self.executor = QueryExecutor(settings.database_url)
        self.resolver = EntityResolver(settings.database_url)
        self.templates = TemplateSQLBuilder()

        ollama = OllamaClient(settings.ollama_base_url)
        self.fallback = SQLFallbackGenerator(ollama, settings.ollama_sql_model)
        self.insights = InsightGenerator(ollama, settings.ollama_summary_model)

        self.guardrails = SQLGuardrails(
            allowed_tables=ALLOWED_TABLES,
            max_rows=settings.sql_max_rows,
        )

    def answer(self, question: str) -> AgentResponse:
        resolved = self.resolver.resolve(question)
        intent = classify_intent(
            question,
            team_count=len(resolved.teams),
            player_count=len(resolved.players),
        )

        plan = self.templates.build(intent, resolved)

        if plan is None:
            plan = self._fallback_plan(question, resolved)
            if plan is None:
                clarification = ""
                if resolved.ambiguities:
                    clarification = f" Clarifications needed: {' '.join(resolved.ambiguities)}"
                return AgentResponse(
                    answer=(
                        "Could not map the question to a safe query."
                        " Please rephrase with a clear player/team and metric."
                        f"{clarification}"
                    ),
                    intent=intent,
                    sql="",
                    sql_source="none",
                    columns=[],
                    rows=[],
                    provenance={
                        "intent": intent.value,
                        "ambiguities": resolved.ambiguities,
                    },
                )

        try:
            safe_sql = self.guardrails.validate_and_rewrite(plan.sql)
        except SQLValidationError as exc:
            return AgentResponse(
                answer=f"Query rejected by guardrails: {exc}",
                intent=intent,
                sql=plan.sql,
                sql_source=plan.source,
                columns=[],
                rows=[],
                provenance={
                    "intent": intent.value,
                    "notes": plan.notes,
                },
            )

        result = self.executor.run(safe_sql, plan.params)
        answer = self.insights.summarize(question, result)

        provenance = {
            "intent": intent.value,
            "source": plan.source,
            "teams": [team.name for team in resolved.teams],
            "players": [player.name for player in resolved.players],
            "seasons": resolved.seasons,
            "thresholds": resolved.thresholds,
            "game_scope": resolved.game_scope,
            "primary_metric": resolved.primary_metric,
            "ranking_metric": resolved.ranking_metric,
            "ranking_limit": resolved.ranking_limit,
            "against_mode": resolved.against_mode,
            "notes": plan.notes,
            "ambiguities": resolved.ambiguities,
            "row_count": len(result.rows),
        }

        return AgentResponse(
            answer=answer,
            intent=intent,
            sql=safe_sql,
            sql_source=plan.source,
            columns=result.columns,
            rows=result.rows,
            provenance=provenance,
        )

    def _fallback_plan(self, question: str, resolved) -> SQLPlan | None:
        schema = fetch_schema_context(self.settings.database_url, ALLOWED_TABLES)

        try:
            return self.fallback.build_plan(
                question=question,
                context=resolved,
                schema_context=schema,
                max_rows=self.settings.sql_max_rows,
            )
        except Exception:
            return None
