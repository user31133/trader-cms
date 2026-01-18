#!/bin/bash

set -e

echo "Running Alembic migrations..."

# Check if running inside Docker
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container"
    alembic revision --autogenerate -m "auto migration"
    alembic upgrade head
else
    echo "Running locally"

    # Load environment variables from .env if it exists
    if [ -f .env ]; then
        export $(cat .env | grep -v '#' | xargs)
    fi

    alembic revision --autogenerate -m "auto migration"
    alembic upgrade head
fi

echo "Migration completed successfully!"
