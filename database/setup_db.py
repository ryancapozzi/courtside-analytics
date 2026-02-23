from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


DEFAULT_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def apply_schema(schema_path: Path = DEFAULT_SCHEMA_PATH) -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and configure it.")

    schema_sql = schema_path.read_text(encoding="utf-8")

    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)


if __name__ == "__main__":
    apply_schema()
    print("Schema applied successfully.")
