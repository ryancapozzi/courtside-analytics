from __future__ import annotations


METRIC_DEFINITIONS = {
    "win_pct": "(wins / total_games) * 100",
    "avg_points": "average points scored across selected games",
    "avg_assists": "average assists across selected games",
    "avg_rebounds": "average rebounds across selected games",
}


def render_metric_context() -> str:
    lines = ["Metric definitions:"]
    for metric, definition in METRIC_DEFINITIONS.items():
        lines.append(f"- {metric}: {definition}")
    return "\n".join(lines)
