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
        },
        {
            "id": 2,
            "intent": "team_trend",
            "sql": "",
            "row_count": 1,
            "sql_source": "none",
        },
    ]

    summary, findings = evaluate_results(questions, results)

    assert summary.total_questions == 2
    assert summary.sql_generated == 1
    assert summary.non_empty_results == 1
    assert summary.intent_matches == 1
    assert len(findings) == 1
    assert findings[0]["id"] == 2


def test_evaluate_results_handles_empty_inputs() -> None:
    summary, findings = evaluate_results([], [])

    assert summary.total_questions == 0
    assert summary.sql_generated == 0
    assert summary.non_empty_results == 0
    assert summary.intent_matches == 0
    assert summary.template_ratio == 0.0
    assert findings == []


def test_evaluate_results_treats_missing_expected_intent_as_match() -> None:
    questions = [{"id": 1, "expected_min_rows": 1}]
    results = [{"id": 1, "intent": "unknown", "sql": "SELECT 1", "row_count": 1, "sql_source": "llm_fallback"}]

    summary, findings = evaluate_results(questions, results)

    assert summary.intent_matches == 1
    assert summary.sql_generated == 1
    assert summary.non_empty_results == 1
    assert findings == []
