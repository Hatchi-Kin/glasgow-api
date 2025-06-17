import os

import psycopg2


def get_postgres_connection():
    """Create and return a PostgreSQL connection."""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        raise RuntimeError(f"Failed to create PostgreSQL connection: {str(e)}")


def get_postgres_version():
    """Get the PostgreSQL server version."""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"status": "connected", "db_version": version[0]}
    except Exception as e:
        return {"status": "error", "message": str(e)}
