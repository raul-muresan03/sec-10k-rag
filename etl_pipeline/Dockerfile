FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY etl_pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copying from root to include config.py
COPY etl_pipeline/ /app/etl_pipeline/
COPY config.py logger.py /app/

ENV PYTHONPATH=/app

CMD ["python", "etl_pipeline/main.py", "--help"]
