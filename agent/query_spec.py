from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .types import IntentType, ResolvedContext


class QueryFamily(str, Enum):
    CONDITIONAL_TEAM_PERFORMANCE = "conditional_team_performance"
    PLAYER_THRESHOLD_COUNT = "player_threshold_count"
    PLAYER_STAT = "player_stat"
    PLAYER_SINGLE_GAME_HIGH = "player_single_game_high"
    PLAYER_RANKING = "player_ranking"
    TEAM_COMPARISON = "team_comparison"
    TEAM_TREND = "team_trend"
    TEAM_STAT = "team_stat"
    TEAM_HEAD_TO_HEAD = "team_head_to_head"
    TEAM_RANKING = "team_ranking"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class QuerySpec:
    family: QueryFamily
    intent: IntentType
    metric: str = "points"
    operation: str = "avg"
    response_mode: str = "single_metric"
    game_scope: str = "regular"
    group_by: str = "none"
    against_mode: bool = False
    ranking_limit: int = 15
    threshold_stat: str | None = None
    threshold_operator: str | None = None
    threshold_value: float | None = None
    notes: list[str] = field(default_factory=list)

    def describe(self, context: ResolvedContext) -> str:
        parts = [
            f"family={self.family.value}",
            f"intent={self.intent.value}",
            f"metric={self.metric}",
            f"operation={self.operation}",
            f"response_mode={self.response_mode}",
            f"scope={self.game_scope}",
            f"group_by={self.group_by}",
        ]

        if context.players:
            parts.append("players=" + ", ".join(player.name for player in context.players))
        if context.teams:
            parts.append("teams=" + ", ".join(team.name for team in context.teams))
        if context.seasons:
            parts.append("seasons=" + ", ".join(context.seasons))
        if self.threshold_stat and self.threshold_operator and self.threshold_value is not None:
            parts.append(
                f"threshold={self.threshold_stat} {self.threshold_operator} {self.threshold_value:g}"
            )
        if self.ranking_limit:
            parts.append(f"limit={self.ranking_limit}")

        return "; ".join(parts)

    def describe_from_question(self) -> str:
        parts = [
            f"family={self.family.value}",
            f"intent={self.intent.value}",
            f"metric={self.metric}",
            f"operation={self.operation}",
            f"response_mode={self.response_mode}",
            f"scope={self.game_scope}",
            f"group_by={self.group_by}",
        ]
        if self.threshold_stat and self.threshold_operator and self.threshold_value is not None:
            parts.append(
                f"threshold={self.threshold_stat} {self.threshold_operator} {self.threshold_value:g}"
            )
        if self.against_mode:
            parts.append("against_mode=true")
        if self.ranking_limit:
            parts.append(f"limit={self.ranking_limit}")
        return "; ".join(parts)

    def describe_from_result(self, _result: object) -> str:
        return self.describe_from_question()
