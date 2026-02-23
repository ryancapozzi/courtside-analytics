from __future__ import annotations

from typing import Any

import psycopg

from .types import QueryResult


class QueryExecutor:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def run(self, sql: str, params: tuple[Any, ...]) -> QueryResult:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                columns = [desc.name for desc in cur.description]

        mapped_rows = [dict(zip(columns, row, strict=False)) for row in rows]
        return QueryResult(columns=columns, rows=mapped_rows)
