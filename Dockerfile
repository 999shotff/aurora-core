FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/
COPY .env.example .env.example

# Production defaults (overridable via environment)
ENV AURORA_HOST=0.0.0.0
ENV AURORA_PORT=8000
ENV AURORA_DATA_MODE=demo
ENV AURORA_DEBUG=false
ENV AURORA_LOG_LEVEL=info

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${AURORA_PORT:-8000}/health')"

CMD ["python", "-m", "aurora.market.server"]
