from analytics.evaluation import evaluate_results


def test_evaluate_results_counts_findings() -> None:
    questions = [
        {"id": 1, "expected_intent": "team_trend", "expected_min_rows": 1},
        {"id": 2, "expected_intent": "team_comparison", "expected_min_rows": 2},
    ]
    results = [
        {
            "id": 1,
            "intent": "team_trend",
            "sql": "SELECT 1",
            "row_count": 1,
            "sql_source": "template",
            "answer": "Across 2022-23 to 2023-24, win rate moved up by 4.00 percentage points.",
            "provenance": {
                "intent": "team_trend",
                "query_family": "team_trend",
                "source": "template",
                "row_count": 1,
                "clarification_required": False,
            },
        },
        {
            "id": 2,
            "intent": "team_trend",
            "sql": "",
            "row_count": 1,
            "sql_source": "none",
            "answer": "",
            "provenance": {"intent": "team_trend"},
        },
    ]

    summary, findings = evaluate_results(questions, results)

    assert summary.total_questions == 2
    assert summary.sql_generated == 1
    assert summary.non_empty_results == 1
    assert summary.intent_matches == 1
    assert summary.answers_generated == 1
    assert summary.answers_with_numeric_support == 1
    assert summary.answers_with_scope_or_caveat == 1
    assert summary.provenance_complete == 1
    assert len(findings) == 1
    assert findings[0]["id"] == 2


def test_evaluate_results_handles_empty_inputs() -> None:
    summary, findings = evaluate_results([], [])

    assert summary.total_questions == 0
    assert summary.sql_generated == 0
    assert summary.non_empty_results == 0
    assert summary.intent_matches == 0
    assert summary.template_ratio == 0.0
    assert summary.answers_generated == 0
    assert summary.answers_with_numeric_support == 0
    assert summary.answers_with_scope_or_caveat == 0
    assert summary.provenance_complete == 0
    assert findings == []


def test_evaluate_results_treats_missing_expected_intent_as_match() -> None:
    questions = [{"id": 1, "expected_min_rows": 1}]
    results = [
        {
            "id": 1,
            "intent": "unknown",
            "sql": "SELECT 1",
            "row_count": 1,
            "sql_source": "llm_fallback",
            "answer": "The top result shows 42.0 in this sample.",
            "provenance": {
                "intent": "unknown",
                "query_family": "unknown",
                "source": "llm_fallback",
                "row_count": 1,
                "clarification_required": False,
            },
        }
    ]

    summary, findings = evaluate_results(questions, results)

    assert summary.intent_matches == 1
    assert summary.sql_generated == 1
    assert summary.non_empty_results == 1
    assert summary.answers_generated == 1
    assert summary.answers_with_numeric_support == 1
    assert summary.provenance_complete == 1
    assert findings == []


def test_evaluate_results_counts_query_spec_as_deterministic() -> None:
    questions = [{"id": 1, "expected_intent": "player_ranking", "expected_min_rows": 1}]
    results = [
        {
            "id": 1,
            "intent": "player_ranking",
            "sql": "SELECT 1",
            "row_count": 5,
            "sql_source": "query_spec",
            "answer": "Nikola Jokic leads this result set at 10.52, ahead of Cade Cunningham by 0.76.",
            "provenance": {
                "intent": "player_ranking",
                "query_family": "player_ranking",
                "source": "query_spec",
                "row_count": 5,
                "clarification_required": False,
            },
        }
    ]

    summary, findings = evaluate_results(questions, results)

    assert summary.template_ratio == 1.0
    assert findings == []


def test_evaluate_results_flags_answer_quality_gaps() -> None:
    questions = [{"id": 1, "expected_intent": "team_record_summary", "expected_min_rows": 1}]
    results = [
        {
            "id": 1,
            "intent": "team_record_summary",
            "sql": "SELECT 1",
            "row_count": 1,
            "sql_source": "query_spec",
            "answer": "The Lakers did well.",
            "provenance": {
                "intent": "team_record_summary",
                "query_family": "team_stat",
                "source": "query_spec",
                "row_count": 1,
                "clarification_required": False,
            },
        }
    ]

    summary, findings = evaluate_results(questions, results)

    assert summary.answers_generated == 1
    assert summary.answers_with_numeric_support == 0
    assert len(findings) == 1
    assert findings[0]["has_numeric_support"] is False
