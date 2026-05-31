# Dockerfile para mercaintelligence-backend en Hugging Face Spaces
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV INGESTA_SKIP_ES=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/

EXPOSE 7860

CMD ["sh", "-c", "gunicorn src.api.app:app --bind 0.0.0.0:${PORT} --workers 1 --timeout 120"]
