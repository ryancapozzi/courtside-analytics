from __future__ import annotations

import json

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
