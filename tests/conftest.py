from __future__ import annotations

import pytest
from psycopg_pool import ConnectionPool
from pathlib import Path
from app.core.middleware import enable_rate_limiting
from app.db.session import init_db

# Disable rate limiting for tests
enable_rate_limiting(False)

TEST_DB_URL = "postgresql://neondb_owner:npg_Wu1npZ7lfgLh@ep-cool-hat-ayfzxo32.c-5.us-east-2.aws.neon.tech/sakhi_test?sslmode=require"

@pytest.fixture(scope="session")
def db_pool_session():
    pool = ConnectionPool(TEST_DB_URL, kwargs={"connect_timeout": 10, "autocommit": True}, check=ConnectionPool.check_connection)
    # Ensure SQLAlchemy also points to the same test DB
    init_db(TEST_DB_URL)
    yield pool
    pool.close()

@pytest.fixture(autouse=True)
def clean_db(db_pool_session):
    with db_pool_session.connection() as conn:
        # Retrieve all tables
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name != 'alembic_version';
            """)
            tables = [row[0] for row in cur.fetchall()]
            if tables:
                # Truncate all tables
                tables_str = ", ".join(f'"{t}"' for t in tables)
                cur.execute(f"TRUNCATE TABLE {tables_str} CASCADE;")
        conn.commit()

@pytest.fixture
def test_db_url():
    return TEST_DB_URL

