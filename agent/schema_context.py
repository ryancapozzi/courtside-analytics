from __future__ import annotations

from typing import Iterable

import psycopg


def fetch_schema_context(database_url: str, allowed_tables: Iterable[str]) -> str:
    table_set = set(allowed_tables)

    sql = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
    """

    lines: list[str] = ["Schema context:"]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    grouped: dict[str, list[tuple[str, str]]] = {}
    for table_name, column_name, data_type in rows:
        if table_name not in table_set:
            continue
        grouped.setdefault(table_name, []).append((column_name, data_type))

    for table_name, cols in grouped.items():
        column_render = ", ".join(f"{name} ({dtype})" for name, dtype in cols)
        lines.append(f"- {table_name}: {column_render}")

    if len(lines) == 1:
        lines.append("- (no schema metadata found)")

    return "\n".join(lines)
