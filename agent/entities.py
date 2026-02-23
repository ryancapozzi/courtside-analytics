from __future__ import annotations

from dataclasses import dataclass

import psycopg
from rapidfuzz import fuzz, process

from .intents import (
    extract_game_scope,
    extract_ranking_metric,
    extract_season_mentions,
    extract_thresholds,
)
from .types import ResolvedContext, ResolvedEntity


@dataclass
class Catalog:
    teams: list[tuple[str, str, str | None]]
    players: list[tuple[str, str]]


class EntityResolver:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def resolve(self, question: str) -> ResolvedContext:
        catalog = self._load_catalog()

        context = ResolvedContext()
        context.teams = self._resolve_teams(question, catalog)
        context.players = self._resolve_players(question, catalog)
        context.seasons = extract_season_mentions(question)
        context.thresholds = extract_thresholds(question)
        context.game_scope = extract_game_scope(question)
        context.ranking_metric = extract_ranking_metric(question)

        if not context.teams:
            context.ambiguities.append("No team detected in question.")
        if "when" in question.lower() and not context.players:
            context.ambiguities.append("No player detected for conditional query.")

        return context

    def _load_catalog(self) -> Catalog:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT team_id, team_name, abbreviation FROM teams")
                teams = cur.fetchall()

                cur.execute("SELECT player_id, player_name FROM players")
                players = cur.fetchall()

        return Catalog(teams=teams, players=players)

    def _resolve_teams(self, question: str, catalog: Catalog) -> list[ResolvedEntity]:
        lower_q = question.lower()
        matches: list[ResolvedEntity] = []

        for team_id, team_name, abbreviation in catalog.teams:
            if team_name and team_name.lower() in lower_q:
                matches.append(ResolvedEntity(id=team_id, name=team_name, score=1.0))
                continue

            if abbreviation and abbreviation.lower() in lower_q.split():
                matches.append(ResolvedEntity(id=team_id, name=team_name, score=0.98))

        if matches:
            return self._dedupe_entities(matches)

        choices = [team_name for _, team_name, _ in catalog.teams]
        best = process.extract(question, choices, scorer=fuzz.WRatio, limit=2)
        fuzzy_matches: list[ResolvedEntity] = []
        for choice, score, idx in best:
            if score < 78:
                continue
            team_id, team_name, _ = catalog.teams[idx]
            fuzzy_matches.append(ResolvedEntity(id=team_id, name=team_name, score=score / 100.0))

        return self._dedupe_entities(fuzzy_matches)

    def _resolve_players(self, question: str, catalog: Catalog) -> list[ResolvedEntity]:
        lower_q = question.lower()
        matches: list[ResolvedEntity] = []

        for player_id, player_name in catalog.players:
            if player_name and player_name.lower() in lower_q:
                matches.append(ResolvedEntity(id=player_id, name=player_name, score=1.0))

        if matches:
            return self._dedupe_entities(matches)

        choices = [player_name for _, player_name in catalog.players]
        best = process.extract(question, choices, scorer=fuzz.WRatio, limit=2)
        fuzzy_matches: list[ResolvedEntity] = []
        for choice, score, idx in best:
            if score < 82:
                continue
            player_id, player_name = catalog.players[idx]
            fuzzy_matches.append(ResolvedEntity(id=player_id, name=player_name, score=score / 100.0))

        return self._dedupe_entities(fuzzy_matches)

    def _dedupe_entities(self, entities: list[ResolvedEntity]) -> list[ResolvedEntity]:
        seen: set[str] = set()
        deduped: list[ResolvedEntity] = []
        for entity in entities:
            if entity.id in seen:
                continue
            seen.add(entity.id)
            deduped.append(entity)
        return deduped
