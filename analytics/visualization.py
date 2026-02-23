from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_line_chart(df: pd.DataFrame, x: str, y: str, title: str, output_path: Path) -> Path:
    """Optional stretch visualization helper.

    Uses pandas plotting backend only if matplotlib is installed. This module is intentionally
    unprioritized for MVP and should not block language-output development.
    """
    try:
        ax = df.plot(x=x, y=y, kind="line", title=title)
        fig = ax.get_figure()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path)
        return output_path
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Visualization requires matplotlib and valid chart data.") from exc
