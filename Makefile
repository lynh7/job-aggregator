.PHONY: install dev test lint search candidate-dev candidate-worker

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

dev:
	.venv/bin/uvicorn app.main:app --reload

candidate-dev:
	.venv/bin/uvicorn candidate_service.main:app --reload --port 8100

candidate-worker:
	.venv/bin/candidate-worker

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

search:
	.venv/bin/job-aggregator search --keywords "python,backend" --location "remote"
