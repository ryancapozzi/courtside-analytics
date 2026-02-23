from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class IngestionSettings:
    database_url: str
    raw_data_dir: Path



def load_settings() -> IngestionSettings:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Configure it in .env.")

    raw_dir = Path(os.getenv("RAW_DATA_DIR", "data/raw")).resolve()
    return IngestionSettings(database_url=database_url, raw_data_dir=raw_dir)
