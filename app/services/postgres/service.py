import sqlite3
import os
import json
import numpy as np
import tempfile
import shutil
import pickle
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


def add_embedding_512_column():
    """Add the embedding_512_vector column to the megaset table."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE megaset ADD COLUMN embedding_512_vector vector(512);"
                )
                conn.commit()
                return {"status": "success", "message": "Added embedding_512_vector column to megaset table."}
    except psycopg2.errors.DuplicateColumn:
        return {"status": "info", "message": "embedding_512_vector column already exists."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add embedding_512_vector column: {str(e)}")


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


def bulk_insert_512_embeddings(embeddings_bucket_name: str = "megaset"):
    """
    Bulk insert 512-dimensional embeddings and update metadata into the megaset table.
    Embeddings and metadata are read from .pkl files in the specified MinIO bucket.
    """
    processed_count = 0
    failed_count = 0
    temp_dir = None

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Get all song IDs and filepaths from PostgreSQL
                # We fetch all to ensure we can update metadata even if embeddings exist
                cursor.execute("SELECT id, filepath, filename, title, artist, album, year, tracknumber, genre, filesize FROM megaset;")
                songs_in_postgres = cursor.fetchall()
                logger.info(f"Found {len(songs_in_postgres)} songs in PostgreSQL to process for embeddings and metadata.")

                if not songs_in_postgres:
                    return {"status": "info", "message": "No songs found in PostgreSQL to process."}

                temp_dir = tempfile.mkdtemp()
                logger.info(f"Created temporary directory: {temp_dir}")

                for song_data in songs_in_postgres:
                    song_id = song_data["id"]
                    filepath = song_data["filepath"]
                    
                    # Existing metadata from PostgreSQL
                    existing_filename = song_data["filename"]
                    existing_title = song_data["title"]
                    existing_artist = song_data["artist"]
                    existing_album = song_data["album"]
                    existing_year = song_data["year"]
                    existing_tracknumber = song_data["tracknumber"]
                    existing_genre = song_data["genre"]
                    existing_filesize = song_data["filesize"]

                    local_pkl_path = None
                    try:
                        # 2. Construct MinIO object name for .pkl
                        # Example: /path/to/song.mp3 -> path/to/song.pkl
                        object_name = filepath.lstrip('/').rsplit('.', 1)[0] + '.pkl'
                        local_pkl_path = os.path.join(temp_dir, os.path.basename(object_name))

                        # 3. Download .pkl from MinIO
                        logger.debug(f"Downloading {object_name} from {embeddings_bucket_name} to {local_pkl_path}")
                        download_object(embeddings_bucket_name, object_name, local_pkl_path)

                        # 4. Load data from .pkl
                        with open(local_pkl_path, 'rb') as f:
                            pkl_data = pickle.load(f)

                        embedding_512 = pkl_data.get('embedding_512')
                        if embedding_512 is not None and (not isinstance(embedding_512, np.ndarray) or embedding_512.shape != (512,)):
                            raise ValueError(f"Invalid embedding_512 format or shape for {object_name}")
                        
                        # Extract metadata from pkl_data, prioritizing existing non-NULL values
                        update_fields = []
                        update_values = []

                        if embedding_512 is not None:
                            update_fields.append("embedding_512_vector = %s")
                            update_values.append(embedding_512.tolist())

                        # Update metadata only if it's None or empty in PostgreSQL
                        if not existing_filename and pkl_data.get('filename'):
                            update_fields.append("filename = %s")
                            update_values.append(pkl_data['filename'])
                        if not existing_title and pkl_data.get('title'):
                            update_fields.append("title = %s")
                            update_values.append(pkl_data['title'])
                        if not existing_artist and pkl_data.get('artist'):
                            update_fields.append("artist = %s")
                            update_values.append(pkl_data['artist'])
                        if not existing_album and pkl_data.get('album'):
                            update_fields.append("album = %s")
                            update_values.append(pkl_data['album'])
                        if not existing_year and pkl_data.get('year') is not None:
                            update_fields.append("year = %s")
                            update_values.append(pkl_data['year'])
                        if not existing_tracknumber and pkl_data.get('tracknumber') is not None:
                            update_fields.append("tracknumber = %s")
                            update_values.append(pkl_data['tracknumber'])
                        if not existing_genre and pkl_data.get('genre'):
                            update_fields.append("genre = %s")
                            update_values.append(pkl_data['genre'])
                        if not existing_filesize and pkl_data.get('filesize') is not None:
                            update_fields.append("filesize = %s")
                            update_values.append(pkl_data['filesize'])

                        if update_fields:
                            update_query = f"UPDATE megaset SET {', '.join(update_fields)} WHERE id = %s;"
                            cursor.execute(update_query, (*update_values, song_id))
                            processed_count += 1
                        else:
                            logger.debug(f"No updates needed for song ID {song_id}")

                    except Exception as e:
                        logger.error(f"Failed to process song ID {song_id} (filepath: {filepath}): {str(e)}")
                        failed_count += 1
                    finally:
                        if local_pkl_path and os.path.exists(local_pkl_path):
                            os.remove(local_pkl_path)

                conn.commit()
                return {
                    "status": "success",
                    "message": f"Bulk insert completed. Processed: {processed_count}, Failed: {failed_count}",
                }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk insert failed: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")


def find_similar_tracks_by_512_embedding(query_embedding: list[float], limit: int = 10):
    """
    Find similar tracks using 512-dimensional vector embeddings.
    """
    if not query_embedding or len(query_embedding) != 512:
        raise HTTPException(status_code=400, detail="Invalid query embedding. Must be a list of 512 floats.")

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Use the <-> operator for L2 distance (Euclidean distance)
                # or <=> for cosine distance (if you prefer that)
                query = """
                    SELECT id, filename, filepath, title, artist, album, (embedding_512_vector <-> %s) AS distance
                    FROM megaset
                    WHERE embedding_512_vector IS NOT NULL
                    ORDER BY distance
                    LIMIT %s;
                """
                cursor.execute(query, (query_embedding, limit))
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    results.append({
                        "id": row["id"],
                        "filename": row["filename"],
                        "filepath": row["filepath"],
                        "title": row["title"],
                        "artist": row["artist"],
                        "album": row["album"],
                        "distance": row["distance"],
                        "similarity_score": 1 - (row["distance"] / 2) # Simple normalization for L2 distance
                    })
                return {"status": "success", "tracks": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")


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