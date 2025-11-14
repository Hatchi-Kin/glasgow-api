import sqlite3
import os
from contextlib import contextmanager

from fastapi import HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.core.logging import get_logger
from app.services.minio.service import download_object

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


def migrate_music_data_from_sqlite(bucket_name: str = "megaset-sqlite", object_name: str = "music_vector_database.db"):
    """
    Migrate music data from a SQLite database stored in MinIO to PostgreSQL.
    """
    temp_db_path = f"/tmp/{object_name}"
    try:
        # Download the SQLite database from MinIO
        download_object(bucket_name, object_name, temp_db_path)

        # Connect to the downloaded SQLite database
        sqlite_conn = sqlite3.connect(temp_db_path)
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT id, filename, filepath, relative_path, album_folder, artist_folder, filesize, title, artist, album, year, tracknumber, genre, top_5_genres, created_at FROM songs")
        rows = sqlite_cursor.fetchall()
        sqlite_conn.close()

        # Clean data: Replace empty strings in integer columns with None
        cleaned_rows = []
        for row in rows:
            row_list = list(row)
            # year is at index 10, tracknumber is at index 11
            if row_list[10] == '':
                row_list[10] = None
            if row_list[11] == '':
                row_list[11] = None
            cleaned_rows.append(tuple(row_list))
        rows = cleaned_rows

    except HTTPException as e:
        # Re-raise HTTP exceptions from the download function
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read from SQLite database: {str(e)}")
    finally:
        # Ensure the temporary file is cleaned up
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

    # Connect to PostgreSQL and insert data
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Create table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS megaset (
                        id SERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        filepath TEXT NOT NULL UNIQUE,
                        relative_path TEXT NOT NULL,
                        album_folder TEXT,
                        artist_folder TEXT,
                        filesize REAL,
                        title TEXT,
                        artist TEXT,
                        album TEXT,
                        year INTEGER,
                        tracknumber INTEGER,
                        genre TEXT,
                        top_5_genres TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """
                )

                # Insert tracks
                insert_query = """
                    INSERT INTO megaset (id, filename, filepath, relative_path, album_folder, artist_folder, filesize, title, artist, album, year, tracknumber, genre, top_5_genres, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (filepath) DO NOTHING;
                """
                cursor.executemany(insert_query, rows)
                conn.commit()

                return {
                    "status": "success",
                    "message": f"Migrated {len(rows)} tracks from SQLite to PostgreSQL.",
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write to PostgreSQL: {str(e)}")


def query_megaset(limit: int = 100, offset: int = 0):
    """Query all music tracks from the megaset table."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM megaset ORDER BY artist, album, tracknumber LIMIT %s OFFSET %s;", (limit, offset))
                rows = cursor.fetchall()
                return {
                    "status": "success",
                    "count": len(rows),
                    "tracks": [dict(row) for row in rows],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_random_megaset_track():
    """Query a single random music track from the megaset table."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM megaset ORDER BY RANDOM() LIMIT 1;")
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="No tracks found in the database.")
                return dict(row)
    except Exception as e:
        # Re-raise HTTPException to preserve status code and detail
        if isinstance(e, HTTPException):
            raise e
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