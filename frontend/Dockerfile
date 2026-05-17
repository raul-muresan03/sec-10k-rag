FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/ /app/frontend/
COPY config.py /app/

ENV PYTHONPATH=/app

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "frontend/main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
