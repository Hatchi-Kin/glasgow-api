from contextlib import contextmanager

from fastapi import HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("postgres")


@contextmanager
def get_postgres_connection(use_admin_db: bool = False):
    """Context manager for PostgreSQL connections."""
    conn = None
    try:
        dsn = settings.postgres_admin_dsn if use_admin_db else settings.postgres_dsn
        logger.debug(f"Connecting to PostgreSQL: {'admin' if use_admin_db else 'app'} database")
        conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        yield conn
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL connection: {str(e)}")
        raise RuntimeError(f"Failed to create PostgreSQL connection: {str(e)}")
    finally:
        if conn:
            conn.close()


def setup_music_db():
    """Create music table and fill it with Graceland tracks in one go."""
    tracks = [
        ("The Boy in the Bubble", "Paul Simon / Paul Simon - Forere Motlhoheloa", 1),
        ("Graceland", "Paul Simon", 2),
        (
            "I Know What I Know",
            "Paul Simon / Paul Simon - General Mikhatshani Daniel Shirinda",
            3,
        ),
        ("Gumboots", "Paul Simon / Paul Simon - Lulu Masilela - Johnson Mkhalali", 4),
        ("Diamonds on the Soles of Her Shoes", "Paul Simon - Joseph Shabalala", 5),
        ("You Can Call Me Al", "Paul Simon", 6),
        ("Under African Skies", "Paul Simon", 7),
        ("Homeless", "Paul Simon - Joseph Shabalala", 8),
        ("Crazy Love Vol II", "Paul Simon", 9),
        ("That Was Your Mother", "Paul Simon", 10),
        ("All Around the World or the Myth of Fingerprints", "Paul Simon", 11),
    ]

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Create table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS music (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        artist VARCHAR(255) NOT NULL,
                        album VARCHAR(255) DEFAULT 'Graceland',
                        track_number INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """
                )

                # Clear existing Graceland data
                cursor.execute("DELETE FROM music WHERE album = 'Graceland';")

                # Insert tracks
                cursor.executemany(
                    """
                    INSERT INTO music (title, artist, track_number)
                    VALUES (%s, %s, %s);
                """,
                    tracks,
                )

                conn.commit()

                return {
                    "status": "success",
                    "message": f"Music table created and populated with {len(tracks)} Graceland tracks",
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def query_music():
    """Query all music tracks."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM music ORDER BY track_number;")
                rows = cursor.fetchall()
                return {
                    "status": "success",
                    "count": len(rows),
                    "tracks": [dict(row) for row in rows],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def list_all_dbs_from_postgres():
    """List all databases in the PostgreSQL instance."""
    try:
        with get_postgres_connection(use_admin_db=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT datname FROM pg_database WHERE datistemplate = false;"
                )
                dbs = cursor.fetchall()
                return {"status": "success", "databases": [db["datname"] for db in dbs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def list_tables_in_db(db_name: str):
    """List all tables in the specified PostgreSQL database."""
    try:
        # Create a custom DSN for the specific database
        dsn = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{db_name}"
        with psycopg2.connect(dsn, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """
                )
                tables = cursor.fetchall()
                return {
                    "status": "success",
                    "database": db_name,
                    "tables": [t["table_name"] for t in tables],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def health_check():
    """Simple health check for database connection."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}