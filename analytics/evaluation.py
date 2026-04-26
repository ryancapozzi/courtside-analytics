from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any


@dataclass
class BenchmarkSummary:
    total_questions: int
    sql_generated: int
    non_empty_results: int
    intent_matches: int
    template_ratio: float
    answers_generated: int
    answers_with_numeric_support: int
    answers_with_scope_or_caveat: int
    provenance_complete: int



def evaluate_results(
    questions: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> tuple[BenchmarkSummary, list[dict[str, Any]]]:
    by_id = {item["id"]: item for item in questions}

    sql_generated = 0
    non_empty = 0
    intent_matches = 0
    answers_generated = 0
    answers_with_numeric_support = 0
    answers_with_scope_or_caveat = 0
    provenance_complete = 0
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
        answer = str(result.get("answer", "") or "").strip()
        provenance = result.get("provenance")
        has_answer = bool(answer)
        numeric_support = _answer_has_numeric_support(answer)
        scope_or_caveat = _answer_has_scope_or_caveat(answer)
        provenance_is_complete = _has_complete_provenance(has_sql, provenance)
        sql_source_counter[source] += 1

        if has_sql:
            sql_generated += 1
        if has_rows:
            non_empty += 1
        if has_answer:
            answers_generated += 1
        if numeric_support:
            answers_with_numeric_support += 1
        if scope_or_caveat:
            answers_with_scope_or_caveat += 1
        if provenance_is_complete:
            provenance_complete += 1

        intent_match = expected_intent is None or expected_intent == actual_intent
        if intent_match:
            intent_matches += 1

        quality_failure = has_rows and (not has_answer or not numeric_support or not provenance_is_complete)
        if not has_sql or not has_rows or not intent_match or quality_failure:
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
                    "has_answer": has_answer,
                    "has_numeric_support": numeric_support,
                    "has_scope_or_caveat": scope_or_caveat,
                    "provenance_complete": provenance_is_complete,
                }
            )

    total = len(results)
    template_count = sql_source_counter.get("template", 0) + sql_source_counter.get("query_spec", 0)
    template_ratio = (template_count / total) if total else 0.0

    summary = BenchmarkSummary(
        total_questions=total,
        sql_generated=sql_generated,
        non_empty_results=non_empty,
        intent_matches=intent_matches,
        template_ratio=template_ratio,
        answers_generated=answers_generated,
        answers_with_numeric_support=answers_with_numeric_support,
        answers_with_scope_or_caveat=answers_with_scope_or_caveat,
        provenance_complete=provenance_complete,
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
        f"- Answers generated: {summary.answers_generated}",
        f"- Answers with numeric support: {summary.answers_with_numeric_support}",
        f"- Answers with scope/caveat language: {summary.answers_with_scope_or_caveat}",
        f"- Results with complete provenance: {summary.provenance_complete}",
        "",
        "## Findings",
        "",
    ]

    if not findings:
        lines.append("No failures detected in this run.")
        return "\n".join(lines)

    lines.extend(
        [
            "| ID | Expected Intent | Actual Intent | SQL | Rows | Min Rows | Answer | Numeric | Scope/Caveat | Prov | Source |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for item in findings:
        lines.append(
            (
                "| {id} | {expected_intent} | {actual_intent} | {has_sql} | {row_count} | "
                "{expected_min_rows} | {has_answer} | {has_numeric_support} | "
                "{has_scope_or_caveat} | {provenance_complete} | {sql_source} |"
            ).format(
                **item
            )
        )

    return "\n".join(lines)


def _answer_has_numeric_support(answer: str) -> bool:
    return bool(re.search(r"\d", answer))


def _answer_has_scope_or_caveat(answer: str) -> bool:
    lowered = answer.lower()
    scope_markers = [
        "sample size",
        "caveat",
        "latest season",
        "in this sample",
        "across ",
        "from ",
        "playoffs",
        "regular season",
        "preseason",
    ]
    return any(marker in lowered for marker in scope_markers)


def _has_complete_provenance(has_sql: bool, provenance: Any) -> bool:
    if not isinstance(provenance, dict):
        return False

    if provenance.get("clarification_required"):
        required = {"intent", "ambiguities", "clarification_required"}
        return required.issubset(provenance)

    if has_sql:
        required = {"intent", "query_family", "source", "row_count", "clarification_required"}
        return required.issubset(provenance)

    required = {"intent", "clarification_required"}
    return required.issubset(provenance)
