from __future__ import annotations

from .intents import TREND_RE, classify_intent
from .query_spec import QueryFamily, QuerySpec
from .types import IntentType, ResolvedContext


class QuerySpecBuilder:
    def build(self, question: str, context: ResolvedContext) -> QuerySpec:
        intent = classify_intent(
            question,
            team_count=len(context.teams),
            player_count=len(context.players),
        )

        threshold_stat, threshold_operator, threshold_value = self._extract_threshold(context)
        group_by = self._detect_grouping(question, context)
        operation = self._resolve_operation(question, context, group_by)
        response_mode = self._resolve_response_mode(context)

        family_map = {
            IntentType.CONDITIONAL_TEAM_PERFORMANCE: QueryFamily.CONDITIONAL_TEAM_PERFORMANCE,
            IntentType.PLAYER_THRESHOLD_COUNT: QueryFamily.PLAYER_THRESHOLD_COUNT,
            IntentType.PLAYER_PROFILE_SUMMARY: QueryFamily.PLAYER_STAT,
            IntentType.PLAYER_SINGLE_GAME_HIGH: QueryFamily.PLAYER_SINGLE_GAME_HIGH,
            IntentType.PLAYER_RANKING: QueryFamily.PLAYER_RANKING,
            IntentType.TEAM_COMPARISON: QueryFamily.TEAM_COMPARISON,
            IntentType.TEAM_TREND: QueryFamily.TEAM_TREND,
            IntentType.TEAM_RECORD_SUMMARY: QueryFamily.TEAM_STAT,
            IntentType.TEAM_HEAD_TO_HEAD: QueryFamily.TEAM_HEAD_TO_HEAD,
            IntentType.TEAM_RANKING: QueryFamily.TEAM_RANKING,
            IntentType.UNKNOWN: QueryFamily.UNKNOWN,
        }
        family = family_map[intent]

        # Prefer structured stat queries over broad profile behavior whenever a player metric is present.
        if context.players and family == QueryFamily.UNKNOWN:
            family = QueryFamily.PLAYER_STAT
            intent = IntentType.PLAYER_PROFILE_SUMMARY

        if context.players and family == QueryFamily.PLAYER_SINGLE_GAME_HIGH:
            group_by = "none"

        if family != QueryFamily.PLAYER_STAT:
            response_mode = "single_metric"

        if context.players and group_by == "season" and family == QueryFamily.PLAYER_STAT:
            notes = ["Player stat query grouped by season."]
        elif context.teams and group_by == "season" and family in {
            QueryFamily.TEAM_COMPARISON,
            QueryFamily.TEAM_TREND,
        }:
            notes = ["Team query grouped by season."]
        else:
            notes = []

        return QuerySpec(
            family=family,
            intent=intent,
            metric=context.primary_metric,
            operation=operation,
            response_mode=response_mode,
            game_scope=context.game_scope,
            group_by=group_by,
            against_mode=context.against_mode,
            ranking_limit=context.ranking_limit,
            threshold_stat=threshold_stat,
            threshold_operator=threshold_operator,
            threshold_value=threshold_value,
            notes=notes,
        )

    def _detect_grouping(self, question: str, context: ResolvedContext) -> str:
        text = question.lower()
        if TREND_RE.search(question) or "by season" in text or "per season" in text:
            return "season"
        if len(context.teams) >= 2 and any(token in text for token in ["compare", "vs", "versus"]):
            return "season"
        return "none"

    def _resolve_operation(self, question: str, context: ResolvedContext, group_by: str) -> str:
        if (
            context.players
            and group_by == "season"
            and context.metric_explicit
            and not context.operation_explicit
            and not context.profile_request
        ):
            text = question.lower()
            if any(token in text for token in ["show", "list", "break down", "breakdown", "by season", "per season"]):
                return "sum"

        return context.stat_operation

    def _resolve_response_mode(self, context: ResolvedContext) -> str:
        if context.players and context.profile_request:
            return "profile"
        return "single_metric"

    def _extract_threshold(self, context: ResolvedContext) -> tuple[str | None, str | None, float | None]:
        comparator_map = {
            "more_than": ">",
            "over": ">",
            "above": ">",
            "greater_than": ">",
            "at_least": ">=",
            "less_than": "<",
            "under": "<",
            "exactly": "=",
        }
        metric_priority = ["points", "rebounds", "assists", "steals", "blocks", "turnovers"]

        for stat in metric_priority:
            for suffix, op in comparator_map.items():
                key = f"{stat}_{suffix}"
                if key in context.thresholds:
                    return stat, op, context.thresholds[key]

        return None, None, None
