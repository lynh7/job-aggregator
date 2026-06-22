.PHONY: install dev crawler-dev test lint search candidate-dev candidate-worker build-job-api build-candidate-api build-candidate-worker build-crawler-api build-agent build-agent-daemon

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev,crawler]"

dev:
	.venv/bin/uvicorn app.main:app --reload

crawler-dev:
	.venv/bin/uvicorn crawler_service.main:app --reload --port 8200

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

build-crawler-api:
	docker build -f docker/crawler-api.Dockerfile -t job-aggregator-crawler-api:latest .

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

search:
	.venv/bin/job-aggregator search --keywords "python,backend" --location "remote"

build-agent:
	python3 scripts/build_agent.py --mode once

build-agent-daemon:
	python3 scripts/build_agent.py --mode daemon
