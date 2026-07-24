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

# Create data dirs
RUN mkdir -p /app/data/files /app/dist

EXPOSE 8000

# Start: init DB, seed, build static site, then run server
CMD ["sh", "-c", "\
    python seed_data.py && \
    python -m static_site.generator && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000"]
