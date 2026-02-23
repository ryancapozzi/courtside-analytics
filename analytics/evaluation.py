from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkSummary:
    total_questions: int
    sql_generated: int
    non_empty_results: int
    intent_matches: int
    template_ratio: float



def evaluate_results(
    questions: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> tuple[BenchmarkSummary, list[dict[str, Any]]]:
    by_id = {item["id"]: item for item in questions}

    sql_generated = 0
    non_empty = 0
    intent_matches = 0
    sql_source_counter: Counter[str] = Counter()

    findings: list[dict[str, Any]] = []

    for result in results:
        q = by_id.get(result["id"], {})
        expected_intent = q.get("expected_intent")
        expected_min_rows = int(q.get("expected_min_rows", 1))

        has_sql = bool(result.get("sql"))
        row_count = int(result.get("row_count", 0))
        has_rows = row_count >= expected_min_rows
        actual_intent = result.get("intent")
        source = str(result.get("sql_source", "unknown"))
        sql_source_counter[source] += 1

        if has_sql:
            sql_generated += 1
        if has_rows:
            non_empty += 1

        intent_match = expected_intent is None or expected_intent == actual_intent
        if intent_match:
            intent_matches += 1

        if not has_sql or not has_rows or not intent_match:
            findings.append(
                {
                    "id": result["id"],
                    "question": result.get("question"),
                    "expected_intent": expected_intent,
                    "actual_intent": actual_intent,
                    "expected_min_rows": expected_min_rows,
                    "has_sql": has_sql,
                    "row_count": row_count,
                    "sql_source": source,
                }
            )

    total = len(results)
    template_count = sql_source_counter.get("template", 0)
    template_ratio = (template_count / total) if total else 0.0

    summary = BenchmarkSummary(
        total_questions=total,
        sql_generated=sql_generated,
        non_empty_results=non_empty,
        intent_matches=intent_matches,
        template_ratio=template_ratio,
    )

    return summary, findings



def render_markdown_report(
    summary: BenchmarkSummary,
    findings: list[dict[str, Any]],
) -> str:
    lines = [
        "# Benchmark Report",
        "",
        "## Summary",
        "",
        f"- Total questions: {summary.total_questions}",
        f"- SQL generated: {summary.sql_generated}",
        f"- Non-empty results: {summary.non_empty_results}",
        f"- Intent matches: {summary.intent_matches}",
        f"- Template ratio: {summary.template_ratio:.2%}",
        "",
        "## Findings",
        "",
    ]

    if not findings:
        lines.append("No failures detected in this run.")
        return "\n".join(lines)

    lines.extend(
        [
            "| ID | Expected Intent | Actual Intent | SQL | Rows | Min Rows | Source |",
            "|---:|---|---|---:|---:|---:|---|",
        ]
    )
    for item in findings:
        lines.append(
            "| {id} | {expected_intent} | {actual_intent} | {has_sql} | {row_count} | {expected_min_rows} | {sql_source} |".format(
                **item
            )
        )

    return "\n".join(lines)
