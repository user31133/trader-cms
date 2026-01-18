#!/usr/bin/env python
"""
Run Alembic migrations
"""

import subprocess
import sys
import os

def run_migrations():
    """Run alembic revision and upgrade commands"""

    # Load environment from .env if exists
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()

    try:
        print("Creating auto migration...")
        result = subprocess.run(
            ['alembic', 'revision', '--autogenerate', '-m', 'auto migration'],
            check=True
        )

        print("Applying migrations...")
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            check=True
        )

        print("✅ Migrations completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed with error: {e}")
        return 1
    except FileNotFoundError:
        print("❌ Alembic not found. Install with: pip install alembic")
        return 1

if __name__ == "__main__":
    sys.exit(run_migrations())
