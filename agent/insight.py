from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

from .metrics import render_metric_context
from .ollama_client import OllamaClient
from .query_spec import QuerySpec
from .types import QueryResult


class InsightGenerator:
    def __init__(self, ollama: OllamaClient, model: str):
        self.ollama = ollama
        self.model = model

    def summarize(self, question: str, result: QueryResult, spec: QuerySpec | None = None) -> str:
        if not result.rows:
            return "No rows matched the requested criteria. Try broadening filters or clarifying the question."

        templated = self._deterministic_summary(result, spec)
        if templated is not None:
            return templated

        sample_rows = result.rows[:10]

        system_prompt = (
            "You are a basketball analytics writer. "
            "Write concise analyst-style insights grounded only in provided rows. "
            "Answer the exact question asked. Do not invent data or mention unrelated metrics."
        )
        user_prompt = "\n".join(
            [
                f"Question: {question}",
                f"Structured spec: {spec.describe_from_result(result) if spec is not None else 'none'}",
                render_metric_context(),
                f"Columns: {result.columns}",
                f"Rows (sample): {json.dumps(sample_rows, default=str)}",
                "Write 1 short paragraph with key stats and one caveat if relevant.",
            ]
        )

        try:
            return self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except Exception:
            first = sample_rows[0]
            return (
                f"Found {len(result.rows)} matching rows. "
                f"Top row summary: {first}. "
                "Run with a local Ollama model for richer narrative output."
            )

    def _deterministic_summary(self, result: QueryResult, spec: QuerySpec | None = None) -> str | None:
        cols = set(result.columns)

        conditional_cols = {
            "team_name",
            "player_name",
            "games",
            "wins",
            "win_pct",
            "avg_player_points",
            "avg_team_points",
        }
        if conditional_cols.issubset(cols) and result.rows:
            row = result.rows[0]
            team = self._as_text(row.get("team_name"))
            player = self._as_text(row.get("player_name"))
            games = self._as_int(row.get("games"))
            wins = self._as_int(row.get("wins"))
            losses = max(games - wins, 0)
            win_pct = self._as_float(row.get("win_pct"))
            avg_player_points = self._as_float(row.get("avg_player_points"))
            avg_team_points = self._as_float(row.get("avg_team_points"))
            threshold_phrase = self._threshold_phrase(spec)

            return (
                f"When {player} gets to {threshold_phrase} for the {team}, "
                f"the team is {wins}-{losses} across {games} games "
                f"({win_pct:.2f}% win rate). "
                f"In that sample, {player} averages {avg_player_points:.2f} points and "
                f"their team averages {avg_team_points:.2f} points per game."
            )

        threshold_count_cols = {
            "player_name",
            "threshold_stat",
            "threshold_operator",
            "threshold_value",
            "games_meeting_threshold",
        }
        if threshold_count_cols.issubset(cols) and result.rows:
            row = result.rows[0]
            player = self._as_text(row.get("player_name"))
            stat = self._as_text(row.get("threshold_stat"))
            operator = self._as_text(row.get("threshold_operator"))
            threshold_value = self._as_float(row.get("threshold_value"))
            games = self._as_int(row.get("games_meeting_threshold"))
            avg_stat_value = row.get("avg_stat_value")
            threshold_display = self._format_threshold_condition(stat, operator, threshold_value)

            summary = f"{player} cleared {threshold_display} in {games} games."
            if avg_stat_value is not None:
                summary += (
                    f" In those games, {player} averaged "
                    f"{self._as_float(avg_stat_value):.2f} {stat}."
                )
            caveat = self._sample_size_caveat(games)
            if caveat:
                summary += f" {caveat}"
            return summary

        player_profile_view_cols = {
            "player_name",
            "games",
            "avg_points",
            "avg_rebounds",
            "avg_assists",
            "avg_minutes",
            "fg_pct",
            "three_pct",
            "ft_pct",
        }
        if player_profile_view_cols.issubset(cols) and result.rows and "metric_value" not in cols:
            if "season_label" in cols and len(result.rows) > 1:
                return self._player_profile_season_group_summary(result)
            return self._player_profile_view_summary(result)

        player_profile_cols = {
            "player_name",
            "metric_name",
            "stat_operation",
            "games",
            "requested_value",
        }
        if player_profile_cols.issubset(cols) and result.rows:
            if "season_label" in cols and len(result.rows) > 1:
                return self._player_season_group_summary(result)
            row = result.rows[0]
            player = self._as_text(row.get("player_name"))
            metric = self._as_text(row.get("metric_name")) or "points"
            operation = self._as_text(row.get("stat_operation")) or "avg"
            games = self._as_int(row.get("games"))
            requested_value = row.get("requested_value")
            per_game_value = row.get("per_game_value")

            if requested_value is None:
                return f"{player} has no recorded {metric} values in this scope."

            if operation == "sum":
                total_value = self._as_float(requested_value)
                per_game = self._as_float(per_game_value) if per_game_value is not None else None
                summary = (
                    f"{player} recorded {self._fmt_number(total_value)} total {metric} "
                    f"across {games} games."
                )
                if per_game is not None:
                    summary += f" That is {per_game:.2f} {metric} per game."
                caveat = self._sample_size_caveat(games)
                if caveat:
                    summary += f" {caveat}"
                return summary

            if operation == "count":
                count_value = self._as_int(requested_value)
                return (
                    f"{player} has {count_value} games with recorded {metric} "
                    f"(across {games} total games)."
                )

            if operation == "max":
                max_value = self._as_float(requested_value)
                return (
                    f"{player}'s highest single-game {metric} in this scope is "
                    f"{self._fmt_number(max_value)}."
                )

            if operation == "min":
                min_value = self._as_float(requested_value)
                return (
                    f"{player}'s lowest single-game {metric} in this scope is "
                    f"{self._fmt_number(min_value)}."
                )

            avg_value = self._as_float(requested_value)
            summary = (
                f"{player} averaged {avg_value:.2f} {metric} across {games} games."
            )
            caveat = self._sample_size_caveat(games)
            if caveat:
                summary += f" {caveat}"
            return summary

        single_game_high_cols = {"player_name", "metric_name", "metric_value", "game_date"}
        if single_game_high_cols.issubset(cols) and result.rows:
            row = result.rows[0]
            player = self._as_text(row.get("player_name"))
            metric = self._as_text(row.get("metric_name")) or "points"
            value = self._as_float(row.get("metric_value"))
            game_date = self._as_text(row.get("game_date"))
            season = self._as_text(row.get("season_label"))
            opponent = self._as_text(row.get("opponent_team"))
            return (
                f"{player}'s top single-game {metric} output in this scope is {value:.0f}, "
                f"recorded on {game_date} in {season} against {opponent}."
            )

        team_record_cols = {"team_name", "games", "wins", "losses", "win_pct"}
        if team_record_cols.issubset(cols) and result.rows:
            row = result.rows[0]
            team = self._as_text(row.get("team_name"))
            games = self._as_int(row.get("games"))
            wins = self._as_int(row.get("wins"))
            losses = self._as_int(row.get("losses"))
            win_pct = self._as_float(row.get("win_pct"))
            avg_points = self._as_float(row.get("avg_points", 0.0))
            avg_points_allowed = self._as_float(row.get("avg_points_allowed", 0.0))
            return (
                f"{team} are {wins}-{losses} across {games} games ({win_pct:.2f}% win rate), "
                f"averaging {avg_points:.2f} points scored and {avg_points_allowed:.2f} allowed."
            )

        team_h2h_cols = {"team_a", "team_b", "games", "team_a_wins", "team_b_wins", "team_a_win_pct"}
        if team_h2h_cols.issubset(cols) and result.rows:
            row = result.rows[0]
            team_a = self._as_text(row.get("team_a"))
            team_b = self._as_text(row.get("team_b"))
            games = self._as_int(row.get("games"))
            team_a_wins = self._as_int(row.get("team_a_wins"))
            team_b_wins = self._as_int(row.get("team_b_wins"))
            team_a_win_pct = self._as_float(row.get("team_a_win_pct"))
            return (
                f"In this scope, {team_a} vs {team_b} has produced {games} games. "
                f"{team_a} lead {team_a_wins}-{team_b_wins} "
                f"({team_a_win_pct:.2f}% win rate for {team_a})."
            )

        team_ranking_cols = {"team_name", "metric_value"}
        if team_ranking_cols.issubset(cols) and result.rows:
            top = result.rows[:3]
            parts = []
            for idx, row in enumerate(top, start=1):
                name = self._as_text(row.get("team_name"))
                metric_value = self._as_float(row.get("metric_value"))
                parts.append(f"{idx}) {name} ({metric_value:.2f})")
            label = self._ranking_label(spec, subject="team")
            return f"Leaders in this result set for {label}: " + ", ".join(parts) + "."

        ranking_cols = {"player_name", "avg_points"}
        if ranking_cols.issubset(cols) and result.rows:
            top = result.rows[:3]
            parts = []
            for idx, row in enumerate(top, start=1):
                name = self._as_text(row.get("player_name"))
                metric_value = self._as_float(row.get("metric_value", row.get("avg_points")))
                parts.append(f"{idx}) {name} ({metric_value:.2f})")
            label = self._ranking_label(spec, subject="player")
            return f"Leaders in this result set for {label}: " + ", ".join(parts) + "."

        comparison_cols = {"season_label", "team_name", "games", "wins", "win_pct"}
        if comparison_cols.issubset(cols) and result.rows:
            latest = self._latest_season_rows(result.rows)
            parts = []
            for row in latest:
                team = self._as_text(row.get("team_name"))
                wins = self._as_int(row.get("wins"))
                games = self._as_int(row.get("games"))
                win_pct = self._as_float(row.get("win_pct"))
                parts.append(f"{team}: {wins}-{max(games - wins, 0)} ({win_pct:.2f}%)")
            season = self._as_text(latest[0].get("season_label"))
            return f"In the latest season in this result set ({season}), " + "; ".join(parts) + "."

        trend_cols = {"season_label", "games", "wins", "win_pct", "avg_points"}
        if trend_cols.issubset(cols) and result.rows:
            first = result.rows[0]
            last = result.rows[-1]
            first_season = self._as_text(first.get("season_label"))
            last_season = self._as_text(last.get("season_label"))
            first_win = self._as_float(first.get("win_pct"))
            last_win = self._as_float(last.get("win_pct"))
            delta = last_win - first_win
            direction = "up" if delta >= 0 else "down"
            return (
                f"Across {first_season} to {last_season}, win rate moved {direction} by "
                f"{abs(delta):.2f} percentage points "
                f"({first_win:.2f}% to {last_win:.2f}%)."
            )

        return None

    def _as_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float, Decimal)):
            return int(value)
        return int(float(str(value)))

    def _as_float(self, value: Any) -> float:
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        return float(str(value))

    def _as_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _latest_season_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        latest = rows[-1].get("season_label")
        latest_rows = [row for row in rows if row.get("season_label") == latest]
        return latest_rows if latest_rows else rows[-2:]

    def _fmt_number(self, value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}"

    def _sample_size_caveat(self, games: int) -> str | None:
        if games < 5:
            return "Caveat: very small sample size."
        if games < 15:
            return "Caveat: small sample size."
        return None

    def _rewrite_with_ollama(
        self,
        question: str,
        factual_summary: str,
        spec: QuerySpec | None,
    ) -> str | None:
        system_prompt = (
            "You are an NBA analyst. Rewrite the factual summary in natural, concise analyst language. "
            "Use only the provided facts. Keep all numeric values exactly unchanged. "
            "Do not add or infer any new stats. Answer the user's actual question directly in the first sentence. "
            "Avoid robotic filler like 'in this scope' or 'requested threshold'."
        )
        user_prompt = "\n".join(
            [
                f"Question: {question}",
                f"Structured spec: {spec.describe_from_question() if spec is not None else 'none'}",
                f"Factual summary: {factual_summary}",
                "Return one short paragraph.",
            ]
        )

        try:
            candidate = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
        except Exception:
            return None

        if not candidate:
            return None

        if not self._preserves_numbers(factual_summary, candidate):
            return None

        return candidate

    def _review_with_ollama(
        self,
        question: str,
        factual_summary: str,
        candidate: str,
        spec: QuerySpec | None,
    ) -> str | None:
        system_prompt = (
            "You are an NBA analytics answer reviewer. "
            "Check whether the candidate answer directly answers the user's question and stays faithful to the facts. "
            "Return strict JSON only with keys approved, reason, revised_answer."
        )
        user_prompt = "\n".join(
            [
                f"Question: {question}",
                f"Structured spec: {spec.describe_from_question() if spec is not None else 'none'}",
                f"Factual summary: {factual_summary}",
                f"Candidate answer: {candidate}",
                (
                    'Return JSON like {"approved": true, "reason": "...", "revised_answer": ""}. '
                    "If the answer misses the actual question, set approved to false and provide a corrected answer."
                ),
            ]
        )

        try:
            content = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
        except Exception:
            return None

        payload = self._extract_json(content)
        if payload is None:
            return None

        approved = bool(payload.get("approved"))
        revised = str(payload.get("revised_answer", "")).strip()

        if approved:
            return candidate

        if revised and self._preserves_numbers(factual_summary, revised):
            return revised

        return factual_summary

    def _preserves_numbers(self, source: str, candidate: str) -> bool:
        source_numbers = self._normalize_number_tokens(source)
        if not source_numbers:
            return True
        candidate_numbers = set(self._normalize_number_tokens(candidate))
        return all(number in candidate_numbers for number in source_numbers)

    def _extract_json(self, content: str) -> dict[str, Any] | None:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            payload = json.loads(text)
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None
        return payload

    def _player_season_group_summary(self, result: QueryResult) -> str | None:
        if not result.rows:
            return None
        first = result.rows[0]
        last = result.rows[-1]
        player = self._as_text(first.get("player_name"))
        metric = self._as_text(first.get("metric_name")) or "points"
        operation = self._as_text(first.get("stat_operation")) or "avg"
        first_season = self._as_text(first.get("season_label"))
        last_season = self._as_text(last.get("season_label"))
        latest_value = self._as_float(last.get("requested_value"))
        peak_row = max(result.rows, key=lambda row: self._as_float(row.get("requested_value", 0)))
        peak_season = self._as_text(peak_row.get("season_label"))
        peak_value = self._as_float(peak_row.get("requested_value"))
        latest_phrase = self._operation_value_phrase(operation, metric, latest_value)
        peak_phrase = self._operation_value_phrase(operation, metric, peak_value)
        return (
            f"Here is the season-by-season {self._operation_label(operation)} for {player}'s {metric} "
            f"from {first_season} through {last_season}. "
            f"The latest season was {last_season} at {latest_phrase}, and the high-water mark was "
            f"{peak_season} at {peak_phrase}."
        )

    def _player_profile_view_summary(self, result: QueryResult) -> str:
        row = result.rows[0]
        player = self._as_text(row.get("player_name"))
        games = self._as_int(row.get("games"))
        avg_points = self._as_float(row.get("avg_points"))
        avg_rebounds = self._as_float(row.get("avg_rebounds"))
        avg_assists = self._as_float(row.get("avg_assists"))
        avg_minutes = self._as_float(row.get("avg_minutes"))
        summary = (
            f"Across {games} games in this sample, {player} averaged "
            f"{avg_points:.2f} points, {avg_rebounds:.2f} rebounds, and {avg_assists:.2f} assists "
            f"in {avg_minutes:.2f} minutes."
        )

        shooting_parts: list[str] = []
        for column, label in [
            ("fg_pct", "from the field"),
            ("three_pct", "from three"),
            ("ft_pct", "at the line"),
        ]:
            value = row.get(column)
            if value is None:
                continue
            shooting_parts.append(f"{self._as_float(value):.2f}% {label}")
        if shooting_parts:
            summary += " Shooting splits: " + ", ".join(shooting_parts) + "."

        turnovers = row.get("avg_turnovers")
        if turnovers is not None:
            summary += f" {player} also averaged {self._as_float(turnovers):.2f} turnovers."

        caveat = self._sample_size_caveat(games)
        if caveat:
            summary += f" {caveat}"
        return summary

    def _player_profile_season_group_summary(self, result: QueryResult) -> str:
        first = result.rows[0]
        last = result.rows[-1]
        player = self._as_text(first.get("player_name"))
        first_season = self._as_text(first.get("season_label"))
        last_season = self._as_text(last.get("season_label"))
        latest_points = self._as_float(last.get("avg_points"))
        latest_rebounds = self._as_float(last.get("avg_rebounds"))
        latest_assists = self._as_float(last.get("avg_assists"))
        peak_scoring_row = max(result.rows, key=lambda row: self._as_float(row.get("avg_points", 0)))
        peak_assist_row = max(result.rows, key=lambda row: self._as_float(row.get("avg_assists", 0)))
        peak_scoring_season = self._as_text(peak_scoring_row.get("season_label"))
        peak_assist_season = self._as_text(peak_assist_row.get("season_label"))
        peak_scoring = self._as_float(peak_scoring_row.get("avg_points"))
        peak_assists = self._as_float(peak_assist_row.get("avg_assists"))
        return (
            f"Here is the season-by-season profile for {player} from {first_season} through {last_season}. "
            f"In the latest season, he posted {latest_points:.2f} points, {latest_rebounds:.2f} rebounds, "
            f"and {latest_assists:.2f} assists per game. "
            f"His best scoring season in this sample was {peak_scoring_season} at {peak_scoring:.2f} points per game, "
            f"and his best playmaking season was {peak_assist_season} at {peak_assists:.2f} assists per game."
        )

    def _threshold_phrase(self, spec: QuerySpec | None) -> str:
        if spec is None or spec.threshold_stat is None or spec.threshold_value is None:
            return "the line"
        operator = spec.threshold_operator or ">="
        return self._format_threshold_condition(spec.threshold_stat, operator, spec.threshold_value)

    def _format_threshold_condition(self, stat: str, operator: str, value: float) -> str:
        display = f"{value:g}"
        if operator == ">=":
            return f"{display}+ {stat}"
        if operator == ">":
            return f"more than {display} {stat}"
        if operator == "<=":
            return f"{display} or fewer {stat}"
        if operator == "<":
            return f"fewer than {display} {stat}"
        if operator == "=":
            return f"exactly {display} {stat}"
        return f"{stat} {operator} {display}"

    def _ranking_label(self, spec: QuerySpec | None, subject: str) -> str:
        if spec is None:
            return f"{subject} value"
        if spec.metric == "win_pct":
            return "win percentage"
        if spec.metric == "opponent_points":
            if spec.operation == "min":
                return "fewest points allowed"
            return "points allowed"
        return spec.metric.replace("_", " ")

    def _operation_label(self, operation: str) -> str:
        mapping = {
            "sum": "total",
            "avg": "average",
            "max": "peak",
            "min": "low",
            "count": "count",
        }
        return mapping.get(operation, operation)

    def _operation_value_phrase(self, operation: str, metric: str, value: float) -> str:
        number = self._fmt_number(value)
        if operation == "sum":
            return f"{number} total {metric}"
        if operation == "avg":
            return f"{number} {metric} per game"
        if operation == "count":
            return f"{number} games"
        if operation == "max":
            return f"{number} {metric}"
        if operation == "min":
            return f"{number} {metric}"
        return f"{number} {metric}"

    def _normalize_number_tokens(self, text: str) -> list[str]:
        tokens = re.findall(r"\d+(?:\.\d+)?", text)
        normalized: list[str] = []
        for token in tokens:
            value = float(token)
            if value.is_integer():
                normalized.append(str(int(value)))
            else:
                normalized.append(f"{value:.2f}".rstrip("0").rstrip("."))
        return normalized
