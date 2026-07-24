#!/bin/bash
# Horizon-Archives entrypoint — seed on first run, then start server

SEED_FLAG="/app/data/.seeded"

if [ ! -f "$SEED_FLAG" ]; then
    echo "First run: seeding database..."
    python seed_data.py
    touch "$SEED_FLAG"
fi

# Build static site
python -m static_site.generator

# Enable SQLite WAL for performance
python -c "import sqlite3;c=sqlite3.connect('/app/data/library.db');c.execute('PRAGMA journal_mode=WAL');c.close()"

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
