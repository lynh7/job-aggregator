.PHONY: install dev test lint search candidate-dev candidate-worker build-job-api build-candidate-api build-candidate-worker

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

dev:
	.venv/bin/uvicorn app.main:app --reload

candidate-dev:
	.venv/bin/uvicorn candidate_service.main:app --reload --port 8100

candidate-worker:
	.venv/bin/candidate-worker

build-job-api:
	docker build -f docker/job-api.Dockerfile -t job-aggregator-api:latest .

build-candidate-api:
	docker build -f docker/candidate-api.Dockerfile -t job-aggregator-candidate-api:latest .

build-candidate-worker:
	docker build -f docker/candidate-worker.Dockerfile -t job-aggregator-candidate-worker:latest .

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

search:
	.venv/bin/job-aggregator search --keywords "python,backend" --location "remote"
