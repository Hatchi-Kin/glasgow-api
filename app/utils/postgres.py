import os
from contextlib import contextmanager

from fastapi import HTTPException, Query
import psycopg2
from psycopg2.extras import RealDictCursor

@contextmanager
def get_postgres_connection():
    """Context manager for PostgreSQL connections."""
    conn = None
    try:
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            cursor_factory=RealDictCursor
        )
        yield conn
    except Exception as e:
        raise RuntimeError(f"Failed to create PostgreSQL connection: {str(e)}")
    finally:
        if conn:
            conn.close()


def get_postgres_version():
    """Get the PostgreSQL server version."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                return {"status": "connected", "db_version": version["version"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def create_music_table():
    """Create the music table if it doesn't exist."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS music (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        artist VARCHAR(255) NOT NULL,
                        album VARCHAR(255) DEFAULT 'Graceland',
                        track_number INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                return {"status": "success", "message": "Music table created successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def insert_graceland_tracks():
    """Insert the Graceland album tracks."""
    tracks = [
        ("The Boy in the Bubble", "Paul Simon / Paul Simon - Forere Motlhoheloa", 1),
        ("Graceland", "Paul Simon", 2),
        ("I Know What I Know", "Paul Simon / Paul Simon - General Mikhatshani Daniel Shirinda", 3),
        ("Gumboots", "Paul Simon / Paul Simon - Lulu Masilela - Johnson Mkhalali", 4),
        ("Diamonds on the Soles of Her Shoes", "Paul Simon - Joseph Shabalala", 5),
        ("You Can Call Me Al", "Paul Simon", 6),
        ("Under African Skies", "Paul Simon", 7),
        ("Homeless", "Paul Simon - Joseph Shabalala", 8),
        ("Crazy Love Vol II", "Paul Simon", 9),
        ("That Was Your Mother", "Paul Simon", 10),
        ("All Around the World or the Myth of Fingerprints", "Paul Simon", 11)
    ]
    
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Check if tracks already exist
                cursor.execute("SELECT COUNT(*) FROM music WHERE album = 'Graceland';")
                count = cursor.fetchone()["count"]
                
                if count > 0:
                    return {"status": "info", "message": f"Graceland tracks already exist ({count} tracks found)"}
                
                # Insert tracks
                cursor.executemany("""
                    INSERT INTO music (title, artist, track_number)
                    VALUES (%s, %s, %s);
                """, tracks)
                conn.commit()
                
                return {"status": "success", "message": f"Successfully inserted {len(tracks)} Graceland tracks"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_all_tables():
    """List all tables in the database."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public';
                """)
                tables = cursor.fetchall()
                return {
                    "status": "success", 
                    "tables": [table["table_name"] for table in tables]
                }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_table_content(table_name: str, limit: int = 100, offset: int = 0):
    """Get content of a specific table with pagination."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Validate table name exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (table_name,))
                
                if not cursor.fetchone()["exists"]:
                    return {"status": "error", "message": f"Table '{table_name}' does not exist"}
                
                # Get total count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                total_count = cursor.fetchone()["count"]
                
                # Get table content with pagination
                cursor.execute(f"SELECT * FROM {table_name} LIMIT %s OFFSET %s;", (limit, offset))
                rows = cursor.fetchall()
                
                return {
                    "status": "success",
                    "table_name": table_name,
                    "total_rows": total_count,
                    "returned_rows": len(rows),
                    "limit": limit,
                    "offset": offset,
                    "data": [dict(row) for row in rows]
                }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def drop_table(table_name: str):
    """Drop a table (be careful with this!)."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                conn.commit()
                return {"status": "success", "message": f"Table '{table_name}' dropped successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    


def setup_database():
    """Create music table and insert Graceland tracks."""
    table_result = create_music_table()
    if table_result["status"] == "error":
        raise HTTPException(status_code=500, detail=table_result["message"])
    
    tracks_result = insert_graceland_tracks()
    
    return {
        "table_creation": table_result,
        "data_insertion": tracks_result
    }

def create_music_table_safe():
    """Create the music table with error handling."""
    result = create_music_table()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

def populate_music_table_safe():
    """Insert Graceland album tracks with error handling."""
    result = insert_graceland_tracks()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

def list_tables_safe():
    """List all tables with error handling."""
    result = list_all_tables()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

def get_table_data_safe(table_name: str, limit: int = 100, offset: int = 0):
    """Get table content with error handling."""
    result = get_table_content(table_name, limit, offset)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result

def delete_table_safe(table_name: str):
    """Delete a table with protection and error handling."""
    if table_name in ["users", "admin"]:
        raise HTTPException(status_code=403, detail=f"Cannot delete protected table '{table_name}'")
    
    result = drop_table(table_name)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

def get_postgres_info():
    """Get PostgreSQL service information."""
    return {
        "service": "PostgreSQL",
        "description": "Database operations for Glasgow GitOps API",
        "available_endpoints": [
            "GET /postgresql/health - Check database connection",
            "POST /postgresql/setup - Create music table and populate with Graceland tracks",
            "GET /postgresql/tables - List all tables",
            "GET /postgresql/tables/{table_name} - Get table content",
            "GET /postgresql/tables/music/tracks - Get music tracks"
        ]
    }