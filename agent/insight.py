from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from .metrics import render_metric_context
from .ollama_client import OllamaClient
from .types import QueryResult


class InsightGenerator:
    def __init__(self, ollama: OllamaClient, model: str):
        self.ollama = ollama
        self.model = model

    def summarize(self, question: str, result: QueryResult) -> str:
        if not result.rows:
            return "No rows matched the requested criteria. Try broadening filters or clarifying the question."

        templated = self._deterministic_summary(result)
        if templated is not None:
            return templated

        sample_rows = result.rows[:10]

        system_prompt = (
            "You are a basketball analytics writer. "
            "Write concise analyst-style insights grounded only in provided rows. "
            "Do not invent data."
        )
        user_prompt = "\n".join(
            [
                f"Question: {question}",
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

    def _deterministic_summary(self, result: QueryResult) -> str | None:
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

            return (
                f"When {player} scores more than the requested threshold for the {team}, "
                f"the team is {wins}-{losses} across {games} games "
                f"({win_pct:.2f}% win rate). "
                f"In those games, {player} averages {avg_player_points:.2f} points and "
                f"the {team} average {avg_team_points:.2f} points."
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
            threshold_display = f"{threshold_value:g}"

            summary = (
                f"{player} has {games} games meeting the condition "
                f"({stat} {operator} {threshold_display})."
            )
            if avg_stat_value is not None:
                summary += (
                    f" In those games, {player} averaged "
                    f"{self._as_float(avg_stat_value):.2f} {stat}."
                )
            return summary

        ranking_cols = {"player_name", "avg_points"}
        if ranking_cols.issubset(cols) and result.rows:
            top = result.rows[:3]
            parts = []
            for idx, row in enumerate(top, start=1):
                name = self._as_text(row.get("player_name"))
                metric_value = self._as_float(row.get("metric_value", row.get("avg_points")))
                parts.append(f"{idx}) {name} ({metric_value:.2f})")
            return "Top players from this query: " + ", ".join(parts) + "."

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
