#!/bin/sh
set -e
alembic upgrade head
python tests/seed_test_db.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
