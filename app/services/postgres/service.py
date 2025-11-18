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


def create_users_table():
    """Create the users table in the PostgreSQL database."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(255) UNIQUE,
                        hashed_password VARCHAR(255) NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        jti VARCHAR(36) UNIQUE,
                        jti_expires_at TIMESTAMP WITH TIME ZONE
                    );
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
                    CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
                    CREATE INDEX IF NOT EXISTS idx_users_jti ON users (jti);
                """)
                conn.commit()
        return {"status": "success", "message": "Users table created or already exists."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create users table: {str(e)}")


def create_favorites_and_playlists_tables():
    """Create the favorites, playlists, and playlist_tracks tables."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Favorites table
                    CREATE TABLE IF NOT EXISTS favorites (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        track_id INTEGER NOT NULL REFERENCES megaset(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, track_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
                    
                    -- Playlists table
                    CREATE TABLE IF NOT EXISTS playlists (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON playlists(user_id);
                    
                    -- Playlist tracks table
                    CREATE TABLE IF NOT EXISTS playlist_tracks (
                        id SERIAL PRIMARY KEY,
                        playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                        track_id INTEGER NOT NULL REFERENCES megaset(id) ON DELETE CASCADE,
                        position INTEGER NOT NULL,
                        added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        UNIQUE(playlist_id, track_id),
                        UNIQUE(playlist_id, position)
                    );
                    CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist_id ON playlist_tracks(playlist_id);
                """)
                conn.commit()
        return {"status": "success", "message": "Favorites and playlists tables created or already exist."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create favorites/playlists tables: {str(e)}")


# ============================================
# FAVORITES FUNCTIONS
# ============================================

def add_favorite(user_id: int, track_id: int):
    """Add a track to user's favorites (max 20)."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Check if user has reached the limit
                cursor.execute("SELECT COUNT(*) as count FROM favorites WHERE user_id = %s;", (user_id,))
                count = cursor.fetchone()["count"]
                
                if count >= 20:
                    raise HTTPException(status_code=400, detail="Maximum 20 favorites allowed")
                
                # Check if track exists
                cursor.execute("SELECT id FROM megaset WHERE id = %s;", (track_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Track not found")
                
                # Add favorite (ON CONFLICT DO NOTHING prevents duplicates)
                cursor.execute(
                    "INSERT INTO favorites (user_id, track_id) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id;",
                    (user_id, track_id)
                )
                result = cursor.fetchone()
                conn.commit()
                
                if result:
                    return {"status": "success", "message": "Track added to favorites"}
                else:
                    return {"status": "info", "message": "Track already in favorites"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add favorite: {str(e)}")


def remove_favorite(user_id: int, track_id: int):
    """Remove a track from user's favorites."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM favorites WHERE user_id = %s AND track_id = %s RETURNING id;",
                    (user_id, track_id)
                )
                result = cursor.fetchone()
                conn.commit()
                
                if result:
                    return {"status": "success", "message": "Track removed from favorites"}
                else:
                    raise HTTPException(status_code=404, detail="Favorite not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove favorite: {str(e)}")


def get_user_favorites(user_id: int):
    """Get all favorite tracks for a user."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT m.*, f.created_at as favorited_at
                    FROM favorites f
                    JOIN megaset m ON f.track_id = m.id
                    WHERE f.user_id = %s
                    ORDER BY f.created_at DESC;
                """, (user_id,))
                rows = cursor.fetchall()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) as count FROM favorites WHERE user_id = %s;", (user_id,))
                total = cursor.fetchone()["count"]
                
                return {
                    "tracks": [dict(row) for row in rows],
                    "total": total
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get favorites: {str(e)}")


def check_is_favorite(user_id: int, track_id: int):
    """Check if a track is in user's favorites."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM favorites WHERE user_id = %s AND track_id = %s;",
                    (user_id, track_id)
                )
                result = cursor.fetchone()
                return {"is_favorite": result is not None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check favorite: {str(e)}")


# ============================================
# PLAYLISTS FUNCTIONS
# ============================================

def create_playlist(user_id: int, name: str):
    """Create a new playlist for a user."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO playlists (user_id, name) VALUES (%s, %s) RETURNING id, name, created_at, updated_at;",
                    (user_id, name)
                )
                result = cursor.fetchone()
                conn.commit()
                
                return {
                    "id": result["id"],
                    "name": result["name"],
                    "track_count": 0,
                    "created_at": result["created_at"].isoformat(),
                    "updated_at": result["updated_at"].isoformat()
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create playlist: {str(e)}")


def get_user_playlists(user_id: int):
    """Get all playlists for a user with track counts."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id, 
                        p.name, 
                        p.created_at, 
                        p.updated_at,
                        COUNT(pt.id) as track_count
                    FROM playlists p
                    LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
                    WHERE p.user_id = %s
                    GROUP BY p.id, p.name, p.created_at, p.updated_at
                    ORDER BY p.updated_at DESC;
                """, (user_id,))
                rows = cursor.fetchall()
                
                playlists = []
                for row in rows:
                    playlists.append({
                        "id": row["id"],
                        "name": row["name"],
                        "track_count": row["track_count"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat()
                    })
                
                return {"playlists": playlists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playlists: {str(e)}")


def get_playlist_with_tracks(user_id: int, playlist_id: int):
    """Get a playlist with all its tracks."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Get playlist info
                cursor.execute(
                    "SELECT id, name, created_at, updated_at FROM playlists WHERE id = %s AND user_id = %s;",
                    (playlist_id, user_id)
                )
                playlist = cursor.fetchone()
                
                if not playlist:
                    raise HTTPException(status_code=404, detail="Playlist not found")
                
                # Get tracks
                cursor.execute("""
                    SELECT m.*, pt.position, pt.added_at
                    FROM playlist_tracks pt
                    JOIN megaset m ON pt.track_id = m.id
                    WHERE pt.playlist_id = %s
                    ORDER BY pt.position;
                """, (playlist_id,))
                tracks = cursor.fetchall()
                
                return {
                    "id": playlist["id"],
                    "name": playlist["name"],
                    "tracks": [dict(track) for track in tracks],
                    "created_at": playlist["created_at"].isoformat(),
                    "updated_at": playlist["updated_at"].isoformat()
                }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playlist: {str(e)}")


def update_playlist_name(user_id: int, playlist_id: int, new_name: str):
    """Update a playlist's name."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE playlists 
                    SET name = %s, updated_at = NOW() 
                    WHERE id = %s AND user_id = %s 
                    RETURNING id;
                """, (new_name, playlist_id, user_id))
                result = cursor.fetchone()
                conn.commit()
                
                if result:
                    return {"status": "success", "message": "Playlist name updated"}
                else:
                    raise HTTPException(status_code=404, detail="Playlist not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update playlist: {str(e)}")


def delete_playlist(user_id: int, playlist_id: int):
    """Delete a playlist."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM playlists WHERE id = %s AND user_id = %s RETURNING id;",
                    (playlist_id, user_id)
                )
                result = cursor.fetchone()
                conn.commit()
                
                if result:
                    return {"status": "success", "message": "Playlist deleted"}
                else:
                    raise HTTPException(status_code=404, detail="Playlist not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete playlist: {str(e)}")


def add_track_to_playlist(user_id: int, playlist_id: int, track_id: int):
    """Add a track to a playlist (max 20 tracks)."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Verify playlist belongs to user
                cursor.execute("SELECT id FROM playlists WHERE id = %s AND user_id = %s;", (playlist_id, user_id))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Playlist not found")
                
                # Check track count
                cursor.execute("SELECT COUNT(*) as count FROM playlist_tracks WHERE playlist_id = %s;", (playlist_id,))
                count = cursor.fetchone()["count"]
                
                if count >= 20:
                    raise HTTPException(status_code=400, detail="Maximum 20 tracks per playlist")
                
                # Check if track exists
                cursor.execute("SELECT id FROM megaset WHERE id = %s;", (track_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Track not found")
                
                # Get next position
                cursor.execute("SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM playlist_tracks WHERE playlist_id = %s;", (playlist_id,))
                next_position = cursor.fetchone()["next_pos"]
                
                # Add track
                cursor.execute(
                    "INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING RETURNING id;",
                    (playlist_id, track_id, next_position)
                )
                result = cursor.fetchone()
                
                # Update playlist updated_at
                cursor.execute("UPDATE playlists SET updated_at = NOW() WHERE id = %s;", (playlist_id,))
                conn.commit()
                
                if result:
                    return {"status": "success", "message": "Track added to playlist"}
                else:
                    return {"status": "info", "message": "Track already in playlist"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add track to playlist: {str(e)}")


def remove_track_from_playlist(user_id: int, playlist_id: int, track_id: int):
    """Remove a track from a playlist and reorder remaining tracks."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Verify playlist belongs to user
                cursor.execute("SELECT id FROM playlists WHERE id = %s AND user_id = %s;", (playlist_id, user_id))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Playlist not found")
                
                # Get the position of the track to remove
                cursor.execute(
                    "SELECT position FROM playlist_tracks WHERE playlist_id = %s AND track_id = %s;",
                    (playlist_id, track_id)
                )
                removed_track = cursor.fetchone()
                
                if not removed_track:
                    raise HTTPException(status_code=404, detail="Track not in playlist")
                
                removed_position = removed_track["position"]
                
                # Delete the track
                cursor.execute(
                    "DELETE FROM playlist_tracks WHERE playlist_id = %s AND track_id = %s;",
                    (playlist_id, track_id)
                )
                
                # Reorder remaining tracks (decrement positions after removed track)
                cursor.execute(
                    "UPDATE playlist_tracks SET position = position - 1 WHERE playlist_id = %s AND position > %s;",
                    (playlist_id, removed_position)
                )
                
                # Update playlist updated_at
                cursor.execute("UPDATE playlists SET updated_at = NOW() WHERE id = %s;", (playlist_id,))
                conn.commit()
                
                return {"status": "success", "message": "Track removed from playlist"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove track from playlist: {str(e)}")


# ============================================
# EXISTING FUNCTIONS (unchanged)
# ============================================

def insert_admin_user(email: str, username: str, hashed_password: str):
    """Insert an admin user into the database if they don't already exist."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Check if user already exists
                cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
                if cursor.fetchone():
                    return {"status": "info", "message": f"User with email {email} already exists."}

                cursor.execute(
                    """
                    INSERT INTO users (email, username, hashed_password, is_active, is_admin)
                    VALUES (%s, %s, %s, TRUE, TRUE)
                    RETURNING id;
                    """,
                    (email, username, hashed_password),
                )
                user_id = cursor.fetchone()["id"]
                conn.commit()
                return {"status": "success", "message": f"Admin user {email} created with ID {user_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create admin user: {str(e)}")


def update_user_password(email: str, hashed_password: str):
    """Update a user's password in the database."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET hashed_password = %s,
                        updated_at = NOW()
                    WHERE email = %s
                    RETURNING id;
                    """,
                    (hashed_password, email),
                )
                user_id = cursor.fetchone()
                if not user_id:
                    raise HTTPException(status_code=404, detail=f"User with email {email} not found.")
                conn.commit()
                return {"status": "success", "message": f"Password for user {email} updated successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user password: {str(e)}")


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
                            year_value = pkl_data['year']
                            if isinstance(year_value, str) and year_value == '':
                                year_value = None
                            update_fields.append("year = %s")
                            update_values.append(year_value)
                        if not existing_tracknumber and pkl_data.get('tracknumber') is not None:
                            tracknumber_value = pkl_data['tracknumber']
                            if isinstance(tracknumber_value, str) and tracknumber_value == '':
                                tracknumber_value = None
                            update_fields.append("tracknumber = %s")
                            update_values.append(tracknumber_value)
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
                    SELECT id, filename, filepath, title, artist, album, (embedding_512_vector <-> CAST(%s AS vector)) AS distance
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
                        "similarity_score": 1 / (1 + row["distance"]) # More appropriate normalization for L2 distance
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