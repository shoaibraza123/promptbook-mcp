# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . /app

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PROMPTS_DIR=/app/prompts \
    SESSIONS_DIR=/app/sessions \
    VECTOR_DB_DIR=/app/prompts/.vectordb

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

RUN mkdir -p "$PROMPTS_DIR" "$SESSIONS_DIR" \
    && chown -R app:app /app

USER app

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -m prompt_rag --health || exit 1

CMD ["python", "mcp_server.py"]
