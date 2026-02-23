import pytest

from agent.sql_validator import SQLGuardrails, SQLValidationError


@pytest.fixture
def guardrails() -> SQLGuardrails:
    return SQLGuardrails(
        allowed_tables={"teams", "games", "players", "player_game_stats", "seasons", "team_game_results"},
        max_rows=100,
    )


def test_adds_limit_if_missing(guardrails: SQLGuardrails) -> None:
    rewritten = guardrails.validate_and_rewrite("SELECT * FROM teams")
    assert "LIMIT 100" in rewritten


def test_blocks_mutation_keywords(guardrails: SQLGuardrails) -> None:
    with pytest.raises(SQLValidationError):
        guardrails.validate_and_rewrite("DELETE FROM teams")


def test_blocks_disallowed_tables(guardrails: SQLGuardrails) -> None:
    with pytest.raises(SQLValidationError):
        guardrails.validate_and_rewrite("SELECT * FROM secret_table")
