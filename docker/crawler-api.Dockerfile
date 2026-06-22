FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY candidate_service ./candidate_service
COPY crawler_service ./crawler_service
RUN pip install --no-cache-dir '.[crawler]'     && python -m playwright install --with-deps chromium

EXPOSE 8200
CMD ["uvicorn", "crawler_service.main:app", "--host", "0.0.0.0", "--port", "8200"]
