# Personal Library — FastAPI Docker image
FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app/ ./app/
COPY static_site/ ./static_site/
COPY static/ ./static/
COPY seed_data.py .

# Create data dirs and non-root user
RUN mkdir -p /app/data/files /app/dist && \
    useradd -r -u 1000 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/me', timeout=3)" || exit 1

# Start: seed only on first run (when DB is empty), build static site, then run server
CMD ["sh", "-c", "\
    if [ ! -f /app/data/library.db ]; then python seed_data.py; fi && \
    python -m static_site.generator && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000"]
