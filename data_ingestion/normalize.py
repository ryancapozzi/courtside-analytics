from __future__ import annotations

import re
from typing import Mapping

import pandas as pd


SNAKE_CASE_RE = re.compile(r"[^a-z0-9]+")



def to_snake_case(value: str) -> str:
    normalized = SNAKE_CASE_RE.sub("_", value.strip().lower()).strip("_")
    return normalized



def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: to_snake_case(str(col)) for col in df.columns}
    return df.rename(columns=renamed)



def apply_aliases(df: pd.DataFrame, aliases: Mapping[str, list[str]]) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    cols = set(df.columns)

    for canonical, candidates in aliases.items():
        for candidate in candidates:
            candidate_snake = to_snake_case(candidate)
            if candidate_snake in cols:
                rename_map[candidate_snake] = canonical
                break

    return df.rename(columns=rename_map)
