from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

import pandas as pd


@dataclass(frozen=True)
class ChartPlan:
    dataframe: pd.DataFrame
    x: str
    y: str | list[str]
    title: str
    kind: str = "line"
    y_label: str = "Value"


def build_chart_plan(
    columns: list[str],
    rows: list[dict[str, object]],
    provenance: dict[str, object] | None = None,
) -> ChartPlan | None:
    if not rows or "season_label" not in columns:
        return None

    provenance = provenance or {}
    teams = [str(team) for team in provenance.get("teams", []) if team]
    players = [str(player) for player in provenance.get("players", []) if player]

    if {"season_label", "team_name", "win_pct"}.issubset(columns):
        return _build_team_comparison_plan(rows, teams)

    if {"season_label", "win_pct"}.issubset(columns):
        return _build_trend_plan(rows, teams)

    if {"season_label", "requested_value", "metric_name"}.issubset(columns):
        return _build_player_stat_plan(rows, players)

    if {"season_label", "avg_points", "avg_rebounds", "avg_assists"}.issubset(columns):
        return _build_player_profile_plan(rows, players)

    return None


def save_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str,
    output_path: Path,
    kind: str = "line",
    y_label: str = "Value",
) -> Path:
    """Save a chart for a supported query result."""
    try:
        cache_dir = Path(tempfile.gettempdir()) / "courtside-mpl-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))

        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt

        y_columns = [y] if isinstance(y, str) else list(y)
        fig, ax = plt.subplots()
        if kind == "bar":
            positions = list(range(len(df[x])))
            width = 0.8 / max(len(y_columns), 1)
            offsets = [
                (index - (len(y_columns) - 1) / 2) * width
                for index in range(len(y_columns))
            ]
            for offset, column in zip(offsets, y_columns):
                values = df[column].tolist()
                bars = ax.bar(
                    [position + offset for position in positions],
                    values,
                    width=width,
                    label=column,
                )
                for bar, value in zip(bars, values):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height(),
                        f"{float(value):.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )
            ax.set_xticks(positions)
            ax.set_xticklabels(df[x].tolist())
        else:
            for column in y_columns:
                ax.plot(df[x], df[column], marker="o", label=column)

        ax.set_title(title)
        ax.set_xlabel(x.replace("_", " ").title())
        ax.set_ylabel(y_label)
        if len(y_columns) > 1:
            ax.legend()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        return output_path
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Visualization requires matplotlib and valid chart data.") from exc


def _build_team_comparison_plan(rows: list[dict[str, object]], teams: list[str]) -> ChartPlan | None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return None

    chart_df = (
        frame[["season_label", "team_name", "win_pct"]]
        .pivot(index="season_label", columns="team_name", values="win_pct")
        .reset_index()
    )
    y_columns = [col for col in chart_df.columns if col != "season_label"]
    if not y_columns:
        return None

    title = "Team Win Percentage by Season"
    if teams:
        title = " vs ".join(teams) + " Win Percentage by Season"

    kind = "bar" if len(chart_df.index) == 1 else "line"

    return ChartPlan(
        dataframe=chart_df,
        x="season_label",
        y=y_columns,
        title=title,
        kind=kind,
        y_label="Win Percentage",
    )


def _build_trend_plan(rows: list[dict[str, object]], teams: list[str]) -> ChartPlan | None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return None

    title = "Team Trend by Season"
    if teams:
        title = f"{teams[0]} Win Percentage Trend"

    return ChartPlan(
        dataframe=frame[["season_label", "win_pct"]].copy(),
        x="season_label",
        y="win_pct",
        title=title,
        y_label="Win Percentage",
    )


def _build_player_stat_plan(rows: list[dict[str, object]], players: list[str]) -> ChartPlan | None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return None

    metric_name = str(frame.iloc[0].get("metric_name", "metric")).replace("_", " ").title()
    title = f"{metric_name} by Season"
    if players:
        title = f"{players[0]} {metric_name} by Season"

    return ChartPlan(
        dataframe=frame[["season_label", "requested_value"]].rename(columns={"requested_value": "metric_value"}),
        x="season_label",
        y="metric_value",
        title=title,
        y_label=metric_name,
    )


def _build_player_profile_plan(rows: list[dict[str, object]], players: list[str]) -> ChartPlan | None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return None

    title = "Player Profile by Season"
    if players:
        title = f"{players[0]} Profile by Season"

    return ChartPlan(
        dataframe=frame[["season_label", "avg_points", "avg_rebounds", "avg_assists"]].copy(),
        x="season_label",
        y=["avg_points", "avg_rebounds", "avg_assists"],
        title=title,
        y_label="Average Per Game",
    )
