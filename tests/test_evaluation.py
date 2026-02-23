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
