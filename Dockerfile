FROM python:3.12-slim

WORKDIR /app

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

COPY groundbook ./groundbook
COPY seed ./seed

# Persistent application data is mounted here; configuration is supplied at runtime.
RUN mkdir -p /data
VOLUME ["/data"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn groundbook.app:app --host \"${HOST:-0.0.0.0}\" --port \"${PORT:-8080}\""]
