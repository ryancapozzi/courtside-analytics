from __future__ import annotations

import re

import sqlglot
from sqlglot import exp


PROHIBITED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "alter",
    "drop",
    "truncate",
    "create",
    "grant",
    "revoke",
    "copy",
}


class SQLValidationError(ValueError):
    pass


class SQLGuardrails:
    def __init__(self, allowed_tables: set[str], max_rows: int):
        self.allowed_tables = allowed_tables
        self.max_rows = max_rows

    def validate_and_rewrite(self, sql: str) -> str:
        cleaned = sql.strip().rstrip(";")
        lowered = cleaned.lower()

        for keyword in PROHIBITED_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                raise SQLValidationError(f"Prohibited keyword detected: {keyword}")

        parse_sql = cleaned.replace("%s", "NULL")
        try:
            expression = sqlglot.parse_one(parse_sql, read="postgres")
        except Exception as exc:  # pragma: no cover
            raise SQLValidationError(f"SQL parse failed: {exc}") from exc

        if not isinstance(expression, (exp.Select, exp.With, exp.Subquery, exp.Union)):
            # Common query roots for read-only statements.
            if expression.key not in {"select", "with", "union"}:
                raise SQLValidationError("Only SELECT/CTE queries are allowed.")

        table_names = {table.name for table in expression.find_all(exp.Table)}
        invalid_tables = table_names - self.allowed_tables
        if invalid_tables:
            raise SQLValidationError(f"Query references disallowed tables: {sorted(invalid_tables)}")

        if "limit" not in lowered:
            cleaned = f"{cleaned}\nLIMIT {self.max_rows}"

        return cleaned + ";"
