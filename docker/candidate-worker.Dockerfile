FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY candidate_service ./candidate_service
COPY crawler_service ./crawler_service
RUN pip install --no-cache-dir '.[postgres]'

RUN mkdir -p /app/data/exports /app/data/candidates

CMD ["candidate-worker"]
