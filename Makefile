.PHONY: install lint test run-cli

install:
	python3 -m pip install -e .[dev]

lint:
	ruff check .

test:
	pytest

run-cli:
	courtside ask "How did the Atlanta Hawks perform when Trae Young scored more than 25 points?"
