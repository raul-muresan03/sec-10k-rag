FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY etl_pipeline/requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt

COPY api ./api
COPY etl_pipeline ./etl_pipeline
COPY eval/corpus_manifest.v1.json ./eval/corpus_manifest.v1.json

RUN useradd --uid 10001 --create-home app && mkdir -p /app/data && chown app:app /app/data
USER app

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
