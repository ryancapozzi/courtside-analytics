from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    CONDITIONAL_TEAM_PERFORMANCE = "conditional_team_performance"
    PLAYER_THRESHOLD_COUNT = "player_threshold_count"
    PLAYER_PROFILE_SUMMARY = "player_profile_summary"
    PLAYER_SINGLE_GAME_HIGH = "player_single_game_high"
    TEAM_COMPARISON = "team_comparison"
    TEAM_TREND = "team_trend"
    TEAM_RECORD_SUMMARY = "team_record_summary"
    TEAM_HEAD_TO_HEAD = "team_head_to_head"
    TEAM_RANKING = "team_ranking"
    PLAYER_RANKING = "player_ranking"
    UNKNOWN = "unknown"


@dataclass
class ResolvedEntity:
    id: str
    name: str
    score: float = 1.0


@dataclass
class ResolvedContext:
    teams: list[ResolvedEntity] = field(default_factory=list)
    players: list[ResolvedEntity] = field(default_factory=list)
    seasons: list[str] = field(default_factory=list)
    thresholds: dict[str, float] = field(default_factory=dict)
    game_scope: str = "regular"
    primary_metric: str = "points"
    ranking_metric: str = "points"
    ranking_limit: int = 15
    against_mode: bool = False
    ambiguities: list[str] = field(default_factory=list)


@dataclass
class SQLPlan:
    sql: str
    params: tuple[Any, ...]
    source: str
    notes: list[str] = field(default_factory=list)


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass
class AgentResponse:
    answer: str
    intent: IntentType
    sql: str
    sql_source: str
    columns: list[str]
    rows: list[dict[str, Any]]
    provenance: dict[str, Any]
