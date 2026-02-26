from __future__ import annotations

import re
from dataclasses import dataclass

import psycopg
from rapidfuzz import fuzz, process

from .intents import (
    detect_against_mode,
    extract_game_scope,
    extract_primary_metric,
    extract_ranking_metric,
    extract_ranking_limit,
    extract_stat_operation,
    extract_season_mentions,
    extract_thresholds,
)
from .types import ResolvedContext, ResolvedEntity

YEAR_RANGE_RE = re.compile(
    r"(?:from\s+)?(20\d{2})\s*(?:-|to|through|thru|until)\s*(20\d{2})",
    re.IGNORECASE,
)
SEASON_LABEL_RANGE_RE = re.compile(
    r"(20\d{2}-\d{2})\s*(?:to|through|thru|until)\s*(20\d{2}-\d{2})",
    re.IGNORECASE,
)


@dataclass
class Catalog:
    teams: list[tuple[str, str, str | None]]
    players: list[tuple[str, str]]
    seasons: list[str]


class EntityResolver:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def resolve(self, question: str) -> ResolvedContext:
        catalog = self._load_catalog()

        context = ResolvedContext()
        context.teams = self._resolve_teams(question, catalog)
        context.players = self._resolve_players(question, catalog)
        context.seasons = self._resolve_seasons(question, catalog.seasons)
        context.thresholds = extract_thresholds(question)
        context.game_scope = extract_game_scope(question)
        context.primary_metric = extract_primary_metric(question)
        context.stat_operation = extract_stat_operation(question, context.primary_metric)
        context.ranking_metric = extract_ranking_metric(question)
        context.ranking_limit = extract_ranking_limit(question)
        context.against_mode = detect_against_mode(question)

        lower_q = question.lower()
        if "when" in lower_q and context.thresholds and not context.players:
            context.ambiguities.append("No player detected for conditional query.")
        if (
            any(token in lower_q for token in ["how many times", "how many games", "how often", "count"])
            and context.thresholds
            and not context.players
        ):
            context.ambiguities.append("No player detected in threshold count query.")
        if (
            any(token in lower_q for token in ["average", "avg", "per game", "career high", "stat line"])
            and not context.players
        ):
            context.ambiguities.append("No player detected for player analytics query.")
        if (
            (
                "head to head" in lower_q
                or " against " in f" {lower_q} "
                or " vs " in f" {lower_q} "
                or " versus " in f" {lower_q} "
            )
            and not context.teams
            and not context.players
        ):
            context.ambiguities.append("No team detected for team analytics query.")

        return context

    def _load_catalog(self) -> Catalog:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT team_id, team_name, abbreviation FROM teams")
                teams = cur.fetchall()

                cur.execute("SELECT player_id, player_name FROM players")
                players = cur.fetchall()

                cur.execute("SELECT season_label FROM seasons ORDER BY start_year")
                seasons = [row[0] for row in cur.fetchall()]

        return Catalog(teams=teams, players=players, seasons=seasons)

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
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        deduped: list[ResolvedEntity] = []
        for entity in entities:
            normalized_name = entity.name.strip().lower()
            if entity.id in seen_ids or normalized_name in seen_names:
                continue
            seen_ids.add(entity.id)
            seen_names.add(normalized_name)
            deduped.append(entity)
        return deduped

    def _resolve_seasons(self, question: str, available_seasons: list[str]) -> list[str]:
        if not available_seasons:
            return extract_season_mentions(question)

        explicit_tokens = extract_season_mentions(question)
        normalized: list[str] = []
        available_set = set(available_seasons)
        season_index = {label: idx for idx, label in enumerate(available_seasons)}

        for token in explicit_tokens:
            if token in available_set:
                normalized.append(token)
                continue

            if len(token) == 4 and token.isdigit():
                mapped = self._map_year_to_season(int(token), available_seasons)
                if mapped:
                    normalized.append(mapped)

        for start_label, end_label in self._extract_season_label_ranges(question):
            if start_label not in season_index or end_label not in season_index:
                continue
            start_idx = season_index[start_label]
            end_idx = season_index[end_label]
            lo = min(start_idx, end_idx)
            hi = max(start_idx, end_idx)
            normalized.extend(available_seasons[lo : hi + 1])

        for start_year, end_year in self._extract_year_ranges(question):
            year_start = min(start_year, end_year)
            year_end = max(start_year, end_year)
            expanded = [
                label
                for label in available_seasons
                if year_start <= self._season_start_year(label) <= year_end
            ]
            normalized.extend(expanded)

        lower_q = question.lower()
        if not normalized and ("this season" in lower_q or "current season" in lower_q):
            normalized.append(available_seasons[-1])
        if not normalized and ("last season" in lower_q or "previous season" in lower_q):
            if len(available_seasons) >= 2:
                normalized.append(available_seasons[-2])

        seen: set[str] = set()
        deduped: list[str] = []
        for label in normalized:
            if label in seen:
                continue
            seen.add(label)
            deduped.append(label)
        deduped.sort(key=lambda label: season_index.get(label, 10**9))
        return deduped

    def _map_year_to_season(self, year: int, available_seasons: list[str]) -> str | None:
        start_year_match = [label for label in available_seasons if label.startswith(f"{year}-")]
        if start_year_match:
            return start_year_match[-1]

        two_digit_year = str(year)[2:]
        end_year_match = [label for label in available_seasons if label.endswith(two_digit_year)]
        if end_year_match:
            return end_year_match[-1]

        return None

    def _extract_year_ranges(self, question: str) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for match in YEAR_RANGE_RE.finditer(question):
            start = int(match.group(1))
            end = int(match.group(2))
            out.append((start, end))
        return out

    def _extract_season_label_ranges(self, question: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for match in SEASON_LABEL_RANGE_RE.finditer(question):
            out.append((match.group(1), match.group(2)))
        return out

    def _season_start_year(self, season_label: str) -> int:
        start = season_label.split("-", 1)[0]
        return int(start)
