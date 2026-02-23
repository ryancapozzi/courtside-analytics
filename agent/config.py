from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class AgentSettings:
    database_url: str
    ollama_base_url: str
    ollama_sql_model: str
    ollama_summary_model: str
    sql_max_rows: int



def load_agent_settings() -> AgentSettings:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return AgentSettings(
        database_url=database_url,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_sql_model=os.getenv("OLLAMA_SQL_MODEL", "llama3.1:8b"),
        ollama_summary_model=os.getenv("OLLAMA_SUMMARY_MODEL", "llama3.1:8b"),
        sql_max_rows=int(os.getenv("SQL_MAX_ROWS", "500")),
    )
