FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/crawler-common.txt ./requirements/crawler-common.txt
RUN pip install --no-cache-dir -r ./requirements/crawler-common.txt

COPY app ./app
COPY crawler_service ./crawler_service
COPY shared ./shared

EXPOSE 8200
CMD ["uvicorn", "crawler_service.main:app", "--host", "0.0.0.0", "--port", "8200"]
