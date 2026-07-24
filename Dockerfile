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
COPY docker-entrypoint.sh .

# Create data dirs + non-root user
RUN mkdir -p /app/data/files /app/dist \
    && useradd -m -u 1000 library \
    && chown -R library:library /app

USER library

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://127.0.0.1:8000/api/me || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
