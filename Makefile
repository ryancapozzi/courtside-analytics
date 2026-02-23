.PHONY: install lint test run-cli setup-db load-data audit-db profile-source sample-data

install:
	python3 -m pip install -e .[dev]

lint:
	ruff check .

test:
	pytest

run-cli:
	courtside ask "How did the Atlanta Hawks perform when Trae Young scored more than 25 points?"

setup-db:
	courtside setup-db

load-data:
	courtside load-data

audit-db:
	courtside audit-db

profile-source:
	python3 -m data_ingestion.profile_source

sample-data:
	python3 scripts/bootstrap_sample_data.py
