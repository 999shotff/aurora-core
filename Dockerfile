FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY .env.example .env.example

ENV AURORA_HOST=0.0.0.0
ENV AURORA_PORT=8000
ENV AURORA_DATA_MODE=demo
ENV AURORA_DEBUG=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "-m", "aurora.market.server"]
