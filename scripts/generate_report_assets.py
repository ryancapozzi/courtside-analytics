from __future__ import annotations

import ast
import json
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/courtside-mpl-cache")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from data_ingestion.column_aliases import COLUMN_ALIASES
from data_ingestion.normalize import apply_aliases, normalize_columns


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = REPO_ROOT / "report"
IMAGES_DIR = REPORT_ROOT / "images"


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    games = _load_games()
    benchmark_questions = json.loads((REPO_ROOT / "data/benchmarks/questions.json").read_text())
    test_counts = _collect_test_counts()
    artifact_counts = _collect_artifact_counts()

    _plot_system_architecture(IMAGES_DIR / "system_architecture.png")
    _plot_technology_architecture(IMAGES_DIR / "technology_architecture_overview.png")
    _plot_dataset_overview(games, IMAGES_DIR / "dataset_overview.png")
    _plot_team_demo(games, IMAGES_DIR / "team_trend_demo.png")
    _plot_validation_overview(benchmark_questions, test_counts, IMAGES_DIR / "validation_overview.png")
    _plot_artifact_footprint(artifact_counts, IMAGES_DIR / "artifact_footprint.png")

    print(f"Saved report assets to {IMAGES_DIR}")


def _load_games() -> pd.DataFrame:
    games_path = REPO_ROOT / "data/raw/games.csv"
    games = pd.read_csv(games_path, low_memory=False)
    games = normalize_columns(games)
    games = apply_aliases(games, COLUMN_ALIASES["games"])

    games["game_date"] = pd.to_datetime(games["game_date"], errors="coerce")
    games = games.dropna(subset=["game_date"]).copy()

    games["season_label"] = games["game_date"].apply(_derive_season_label)
    games["game_type"] = games["game_type"].fillna("regular").astype(str).str.lower()
    games["game_type"] = (
        games["game_type"]
        .str.replace(" season", "", regex=False)
        .str.replace("_", " ", regex=False)
        .str.strip()
    )
    games["winner_team_id"] = games["winner_team_id"].astype(str)
    games["home_team_id"] = games["home_team_id"].astype(str)
    games["away_team_id"] = games["away_team_id"].astype(str)
    games["home_team_name"] = games["home_team_name"].fillna(games["home_team_id"]).astype(str)
    games["away_team_name"] = games["away_team_name"].fillna(games["away_team_id"]).astype(str)
    return games


def _derive_season_label(ts: pd.Timestamp) -> str:
    start_year = ts.year if ts.month >= 10 else ts.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def _collect_test_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted((REPO_ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        count = sum(
            isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            for node in tree.body
        )
        counts[path.stem.replace("test_", "")] = count
    return counts


def _collect_artifact_counts() -> dict[str, int]:
    targets = ["agent", "analytics", "cli", "data_ingestion", "database", "tests", "docs", "scripts"]
    counts: dict[str, int] = {}
    for name in targets:
        counts[name] = len(list((REPO_ROOT / name).glob("*.py"))) + len(
            list((REPO_ROOT / name).glob("*.md"))
        ) + len(list((REPO_ROOT / name).glob("*.sql"))) + len(list((REPO_ROOT / name).glob("*.json")))
    return counts


def _plot_system_architecture(output_path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.axis("off")

    steps = [
        "User Question",
        "Intent +\nEntity Resolver",
        "Query Spec +\nSQL Builder",
        "SQL Guardrails",
        "PostgreSQL\nExecution",
        "Insight +\nCLI Output",
    ]
    colors = ["#113F67", "#34699A", "#58A0C8", "#9FD3C7", "#F6AE2D", "#F26419"]

    x_positions = [0.02, 0.18, 0.35, 0.52, 0.69, 0.86]
    width = 0.11
    height = 0.32

    for idx, (label, color, xpos) in enumerate(zip(steps, colors, x_positions, strict=True)):
        rect = plt.Rectangle((xpos, 0.36), width, height, color=color, alpha=0.95, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(
            xpos + width / 2,
            0.52,
            label,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=12,
            color="white",
            weight="bold",
        )
        if idx < len(steps) - 1:
            ax.annotate(
                "",
                xy=(x_positions[idx + 1] - 0.01, 0.52),
                xytext=(xpos + width + 0.01, 0.52),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", lw=2.2, color="#263238"),
            )

    ax.text(
        0.5,
        0.84,
        "Courtside Analytics End-to-End Pipeline",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=18,
        weight="bold",
        color="#102A43",
    )
    ax.text(
        0.5,
        0.16,
        "Template-first query generation, schema-constrained execution, and analyst-style answer generation",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=11,
        color="#334E68",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_technology_architecture(output_path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(13.4, 7.2))
    ax.axis("off")

    def add_box(
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        color: str,
        *,
        text_color: str = "white",
        fontsize: int = 11,
    ) -> tuple[float, float, float, float]:
        patch = matplotlib.patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.6,
            edgecolor="#243B53",
            facecolor=color,
            alpha=0.97,
            transform=ax.transAxes,
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2,
            y + h / 2,
            label,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=fontsize,
            color=text_color,
            weight="bold",
        )
        return x, y, w, h

    def point(box: tuple[float, float, float, float], anchor: str) -> tuple[float, float]:
        x, y, w, h = box
        anchors = {
            "left": (x, y + h / 2),
            "right": (x + w, y + h / 2),
            "top": (x + w / 2, y + h),
            "bottom": (x + w / 2, y),
        }
        return anchors[anchor]

    def connect(
        src: tuple[float, float, float, float],
        src_anchor: str,
        dst: tuple[float, float, float, float],
        dst_anchor: str,
        *,
        style: str = "-",
        color: str = "#243B53",
        curve: float = 0.0,
    ) -> None:
        start = point(src, src_anchor)
        end = point(dst, dst_anchor)
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            xycoords=ax.transAxes,
            textcoords=ax.transAxes,
            arrowprops=dict(
                arrowstyle="->",
                lw=2.0,
                linestyle=style,
                color=color,
                connectionstyle=f"arc3,rad={curve}",
            ),
        )

    user_cli = add_box(0.04, 0.74, 0.18, 0.13, "User + CLI\nTyper / Rich", "#0B6E4F")
    orchestrator = add_box(0.30, 0.74, 0.2, 0.13, "Python Orchestration\npipeline.py", "#1D6996")
    output_box = add_box(0.76, 0.74, 0.2, 0.13, "Grounded Output\nanswer + SQL + provenance", "#C05621")

    deterministic = add_box(
        0.05,
        0.46,
        0.24,
        0.15,
        "Deterministic Query Layer\nentities.py, spec_builder.py,\nspec_sql.py",
        "#2F855A",
    )
    guardrails = add_box(
        0.35,
        0.46,
        0.19,
        0.15,
        "Safety + SQL Parsing\nsql_validator.py\nSQLGlot",
        "#805AD5",
    )
    ollama = add_box(
        0.61,
        0.46,
        0.26,
        0.15,
        "LLM Support\nOllama local models\nSQL fallback + rewrite review",
        "#D69E2E",
        text_color="#102A43",
    )

    raw_data = add_box(
        0.14,
        0.18,
        0.22,
        0.15,
        "Raw CSV Dataset\nGames.csv +\nPlayerStatistics.csv",
        "#4C956C",
    )
    postgres = add_box(0.42, 0.18, 0.2, 0.15, "PostgreSQL\nschema + execution", "#1F4E79")
    analytics = add_box(
        0.67,
        0.18,
        0.18,
        0.15,
        "Analytics Layer\nMatplotlib +\nevaluation",
        "#118AB2",
    )
    support = add_box(
        0.87,
        0.44,
        0.09,
        0.19,
        "Repo\nDocs +\nTests",
        "#4A5568",
    )

    assurance = add_box(
        0.06,
        0.03,
        0.88,
        0.08,
        "Supporting assurance around the pipeline: pytest suites, benchmark prompts, README, architecture notes, source setup guide, and demo runbook",
        "#E2E8F0",
        text_color="#102A43",
        fontsize=10,
    )

    connect(user_cli, "right", orchestrator, "left")
    connect(orchestrator, "bottom", deterministic, "top")
    connect(deterministic, "right", guardrails, "left")
    connect(guardrails, "bottom", postgres, "top")
    connect(raw_data, "right", postgres, "left")
    connect(postgres, "right", analytics, "left")
    connect(analytics, "top", output_box, "bottom")
    connect(orchestrator, "right", ollama, "top", style="--", curve=0.18)
    connect(ollama, "left", guardrails, "right", style="--")

    ax.text(
        0.56,
        0.39,
        "read-only,\nschema-valid SQL",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9.5,
        color="#334E68",
    )
    ax.text(
        0.73,
        0.66,
        "optional fallback /\nrewrite support",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9.5,
        color="#334E68",
    )
    ax.text(
        0.74,
        0.37,
        "charts + benchmark\nartifacts",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9.5,
        color="#334E68",
    )

    ax.text(
        0.5,
        0.95,
        "Technology Architecture Overview",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=19,
        weight="bold",
        color="#102A43",
    )
    ax.text(
        0.5,
        0.91,
        "How the repo's technologies interact to turn raw NBA data and natural-language questions into usable analytics output",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=11,
        color="#486581",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_dataset_overview(games: pd.DataFrame, output_path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    season_counts = games.groupby("season_label").size().sort_index()
    recent_seasons = season_counts.tail(20)
    axes[0].plot(recent_seasons.index, recent_seasons.values, marker="o", color="#1D6996", linewidth=2.2)
    axes[0].set_title("Games per Season (Recent 20 Seasons)")
    axes[0].set_ylabel("Games")
    axes[0].tick_params(axis="x", rotation=45)

    game_type_counts = (
        games["game_type"]
        .replace({"all star": "all-star", "commissioner's cup": "special"})
        .value_counts()
        .sort_values(ascending=False)
    )
    game_type_counts = game_type_counts[game_type_counts > 0].head(5)
    axes[1].bar(game_type_counts.index, game_type_counts.values, color=["#F26419", "#0096C7", "#2A9D8F", "#8D99AE"])
    axes[1].set_title("Game Type Distribution")
    axes[1].set_ylabel("Games")
    axes[1].tick_params(axis="x", rotation=25)

    fig.suptitle("Historical NBA Dataset Coverage", fontsize=17, weight="bold", color="#102A43")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_team_demo(games: pd.DataFrame, output_path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    regular = games[games["game_type"] == "regular"].copy()
    teams = ["Lakers", "Warriors"]
    regular = regular[
        regular["home_team_name"].isin(teams) | regular["away_team_name"].isin(teams)
    ].copy()

    records: list[dict[str, object]] = []
    for _, row in regular.iterrows():
        for team_name_col, team_id_col in [
            ("home_team_name", "home_team_id"),
            ("away_team_name", "away_team_id"),
        ]:
            team_name = row[team_name_col]
            if team_name not in teams:
                continue
            records.append(
                {
                    "season_label": row["season_label"],
                    "team_name": team_name,
                    "is_win": int(row["winner_team_id"] == row[team_id_col]),
                }
            )

    frame = pd.DataFrame(records)
    summary = (
        frame.groupby(["season_label", "team_name"])["is_win"]
        .mean()
        .mul(100)
        .reset_index(name="win_pct")
    )
    summary["season_start"] = summary["season_label"].str[:4].astype(int)
    summary = summary[summary["season_start"] >= 2016]

    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    palette = {"Lakers": "#552583", "Warriors": "#1D428A"}
    for team in teams:
        team_df = summary[summary["team_name"] == team].sort_values("season_start")
        ax.plot(
            team_df["season_label"],
            team_df["win_pct"],
            marker="o",
            linewidth=2.5,
            color=palette[team],
            label=team,
        )

    ax.set_title("Regular-Season Win Percentage Demo Query: Lakers vs Warriors")
    ax.set_ylabel("Win Percentage")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_validation_overview(
    benchmark_questions: list[dict[str, object]],
    test_counts: dict[str, int],
    output_path: Path,
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    intent_counts = Counter(str(item["expected_intent"]) for item in benchmark_questions)
    intent_labels = [label.replace("_", "\n") for label, _ in intent_counts.most_common()]
    intent_values = [value for _, value in intent_counts.most_common()]
    axes[0].bar(intent_labels, intent_values, color="#3A86FF")
    axes[0].set_title("30-Question Benchmark Coverage")
    axes[0].set_ylabel("Questions")
    axes[0].tick_params(axis="x", rotation=0, labelsize=9)

    ordered_tests = sorted(test_counts.items(), key=lambda item: item[1])
    labels = [name.replace("_", " ") for name, _ in ordered_tests]
    values = [value for _, value in ordered_tests]
    axes[1].barh(labels, values, color="#FB8500")
    axes[1].set_title("Regression Tests by Suite")
    axes[1].set_xlabel("Test Count")

    fig.suptitle("Evaluation and Validation Footprint", fontsize=17, weight="bold", color="#102A43")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_artifact_footprint(artifact_counts: dict[str, int], output_path: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    ordered = sorted(artifact_counts.items(), key=lambda item: item[1], reverse=True)
    labels = [name.replace("_", "\n") for name, _ in ordered]
    values = [value for _, value in ordered]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    bars = ax.bar(labels, values, color=["#0B6E4F", "#1F78B4", "#6A4C93", "#FFB703", "#E36414", "#2A9D8F", "#8E9AAF", "#577590"])
    ax.set_title("Repository Artifact Footprint by Module")
    ax.set_ylabel("Tracked Source / Documentation Files")
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.15,
            str(value),
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
