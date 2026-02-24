from __future__ import annotations

import re

from .metrics import render_metric_context
from .ollama_client import OllamaClient
from .types import ResolvedContext, SQLPlan


SQL_BLOCK_RE = re.compile(r"```sql\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


class SQLFallbackGenerator:
    def __init__(self, ollama: OllamaClient, model: str):
        self.ollama = ollama
        self.model = model

    def build_plan(
        self,
        question: str,
        context: ResolvedContext,
        schema_context: str,
        max_rows: int,
    ) -> SQLPlan | None:
        system_prompt = (
            "You are a PostgreSQL SQL assistant. "
            "Return one read-only SQL query only. "
            f"Always include LIMIT {max_rows} unless grouped results are clearly small."
        )

        user_prompt = "\n".join(
            [
                f"Question: {question}",
                schema_context,
                render_metric_context(),
                f"Resolved teams: {[team.name for team in context.teams]}",
                f"Resolved players: {[player.name for player in context.players]}",
                f"Resolved seasons: {context.seasons}",
                f"Thresholds: {context.thresholds}",
                f"Primary metric: {context.primary_metric}",
                f"Ranking metric: {context.ranking_metric}",
                f"Ranking limit: {context.ranking_limit}",
                f"Against mode: {context.against_mode}",
                "Allowed tables: teams, players, seasons, games, player_game_stats, team_game_results.",
                "Return SQL only.",
            ]
        )

        content = self.ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )

        sql = self._extract_sql(content)
        if not sql:
            return None

        return SQLPlan(sql=sql, params=(), source="llm_fallback", notes=[])

    def _extract_sql(self, content: str) -> str | None:
        match = SQL_BLOCK_RE.search(content)
        if match:
            return match.group(1).strip()

        text = content.strip()
        if text.lower().startswith("select") or text.lower().startswith("with"):
            return text

        return None
