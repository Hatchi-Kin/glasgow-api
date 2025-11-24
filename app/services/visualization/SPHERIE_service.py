import json
import tempfile
import os
from typing import List, Dict, Optional

from fastapi import HTTPException
from psycopg2.extras import execute_values

from app.core.logging import get_logger
from app.services.postgres.service import get_postgres_connection
from app.services.minio.service import download_object

logger = get_logger("visualization")


def create_visualization_table():
    """Create the track_visualization_sphere table in PostgreSQL."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS track_visualization_sphere (
                        id INTEGER PRIMARY KEY REFERENCES megaset(id) ON DELETE CASCADE,
                        x REAL NOT NULL,
                        y REAL NOT NULL,
                        z REAL NOT NULL,
                        cluster INTEGER NOT NULL,
                        cluster_color VARCHAR(7) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_track_visualization_sphere_cluster ON track_visualization_sphere(cluster);
                """)
                conn.commit()
        return {
            "status": "success",
            "message": "track_visualization_sphere table created or already exists.",
        }
    except Exception as e:
        logger.error(f"Failed to create track_visualization_sphere table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")


def load_visualization_data_from_minio(
    bucket_name: str = "megaset-sqlite",
    object_name: str = "spherical_umap_coordinates.json",
):
    """
    Load visualization data from MinIO JSON file and populate the track_visualization_sphere table.
    """
    temp_file_path = None

    try:
        # Download JSON file from MinIO
        temp_file_path = os.path.join(tempfile.gettempdir(), object_name)
        logger.info(f"Downloading {object_name} from {bucket_name}")
        download_object(bucket_name, object_name, temp_file_path)

        # Load JSON data
        with open(temp_file_path, "r") as f:
            data = json.load(f)

        points = data.get("points", [])
        if not points:
            return {"status": "warning", "message": "No points found in JSON file"}

        logger.info(f"Loaded {len(points)} points from JSON")

        # Prepare data for bulk insert
        values_to_insert = []
        for point in points:
            values_to_insert.append(
                (
                    point["id"],
                    point["x"],
                    point["y"],
                    point["z"],
                    point["cluster"],
                    point["cluster_color"],
                )
            )

        # Bulk insert into PostgreSQL
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Clear existing data
                cursor.execute("DELETE FROM track_visualization_sphere;")

                # Bulk insert
                execute_values(
                    cursor,
                    """
                    INSERT INTO track_visualization_sphere (id, x, y, z, cluster, cluster_color)
                    VALUES %s
                    ON CONFLICT (id) DO UPDATE SET
                        x = EXCLUDED.x,
                        y = EXCLUDED.y,
                        z = EXCLUDED.z,
                        cluster = EXCLUDED.cluster,
                        cluster_color = EXCLUDED.cluster_color;
                    """,
                    values_to_insert,
                )
                conn.commit()

        return {
            "status": "success",
            "message": f"Loaded {len(values_to_insert)} visualization points into database",
        }

    except Exception as e:
        logger.error(f"Failed to load visualization data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")

    finally:
        # Cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def get_all_visualization_points(limit: int = 10000, offset: int = 0):
    """Get all visualization points with track metadata."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        tv.id,
                        tv.x,
                        tv.y,
                        tv.z,
                        tv.cluster,
                        tv.cluster_color,
                        m.title,
                        m.artist,
                        m.album,
                        m.genre,
                        m.year
                    FROM track_visualization_sphere tv
                    JOIN megaset m ON tv.id = m.id
                    ORDER BY tv.id
                    LIMIT %s OFFSET %s;
                """,
                    (limit, offset),
                )

                rows = cursor.fetchall()

                # Get total count
                cursor.execute(
                    "SELECT COUNT(*) as count FROM track_visualization_sphere;"
                )
                total = cursor.fetchone()["count"]

                points = []
                for row in rows:
                    points.append(
                        {
                            "id": row["id"],
                            "x": row["x"],
                            "y": row["y"],
                            "z": row["z"],
                            "cluster": row["cluster"],
                            "cluster_color": row["cluster_color"],
                            "title": row["title"],
                            "artist": row["artist"],
                            "album": row["album"],
                            "genre": row["genre"],
                            "year": row["year"],
                        }
                    )

                return {
                    "points": points,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }

    except Exception as e:
        logger.error(f"Failed to get visualization points: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get points: {str(e)}")


def get_visualization_stats():
    """Get statistics about the visualization data."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Total tracks
                cursor.execute(
                    "SELECT COUNT(*) as count FROM track_visualization_sphere;"
                )
                total_tracks = cursor.fetchone()["count"]

                # Total clusters (excluding noise cluster -1)
                cursor.execute(
                    "SELECT COUNT(DISTINCT cluster) as count FROM track_visualization_sphere WHERE cluster >= 0;"
                )
                total_clusters = cursor.fetchone()["count"]

                # Genre distribution
                cursor.execute("""
                    SELECT m.genre, COUNT(*) as count
                    FROM track_visualization_sphere tv
                    JOIN megaset m ON tv.id = m.id
                    WHERE m.genre IS NOT NULL
                    GROUP BY m.genre
                    ORDER BY count DESC;
                """)
                genre_rows = cursor.fetchall()
                genres = {row["genre"]: row["count"] for row in genre_rows}
                top_genres = [(row["genre"], row["count"]) for row in genre_rows[:10]]

                # Largest cluster
                cursor.execute("""
                    SELECT 
                        cluster,
                        cluster_color,
                        COUNT(*) as count,
                        AVG(x) as center_x,
                        AVG(y) as center_y,
                        AVG(z) as center_z
                    FROM track_visualization_sphere
                    WHERE cluster >= 0
                    GROUP BY cluster, cluster_color
                    ORDER BY count DESC
                    LIMIT 1;
                """)
                largest = cursor.fetchone()

                largest_cluster = None
                if largest:
                    largest_cluster = {
                        "id": largest["cluster"],
                        "color": largest["cluster_color"],
                        "count": largest["count"],
                        "center": [
                            largest["center_x"],
                            largest["center_y"],
                            largest["center_z"],
                        ],
                    }

                return {
                    "total_tracks": total_tracks,
                    "total_clusters": total_clusters,
                    "genres": genres,
                    "top_genres": top_genres,
                    "largest_cluster": largest_cluster,
                }

    except Exception as e:
        logger.error(f"Failed to get visualization stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


def search_tracks(query: str, limit: int = 50):
    """Search tracks by title, artist, album, or genre."""
    try:
        search_pattern = f"%{query}%"

        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        tv.id,
                        tv.x,
                        tv.y,
                        tv.z,
                        tv.cluster,
                        tv.cluster_color,
                        m.title,
                        m.artist,
                        m.album,
                        m.genre,
                        m.year
                    FROM track_visualization_sphere tv
                    JOIN megaset m ON tv.id = m.id
                    WHERE 
                        m.title ILIKE %s OR
                        m.artist ILIKE %s OR
                        m.album ILIKE %s OR
                        m.genre ILIKE %s
                    LIMIT %s;
                """,
                    (
                        search_pattern,
                        search_pattern,
                        search_pattern,
                        search_pattern,
                        limit,
                    ),
                )

                rows = cursor.fetchall()

                # Get total count without limit
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM track_visualization_sphere tv
                    JOIN megaset m ON tv.id = m.id
                    WHERE 
                        m.title ILIKE %s OR
                        m.artist ILIKE %s OR
                        m.album ILIKE %s OR
                        m.genre ILIKE %s;
                """,
                    (search_pattern, search_pattern, search_pattern, search_pattern),
                )
                total = cursor.fetchone()["count"]

                results = []
                for row in rows:
                    results.append(
                        {
                            "id": row["id"],
                            "x": row["x"],
                            "y": row["y"],
                            "z": row["z"],
                            "cluster": row["cluster"],
                            "cluster_color": row["cluster_color"],
                            "title": row["title"],
                            "artist": row["artist"],
                            "album": row["album"],
                            "genre": row["genre"],
                            "year": row["year"],
                        }
                    )

                return {"query": query, "results": results, "total_results": total}

    except Exception as e:
        logger.error(f"Failed to search tracks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")


def get_cluster_details(cluster_id: int):
    """Get all tracks in a specific cluster."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Get cluster info
                cursor.execute(
                    """
                    SELECT 
                        cluster,
                        cluster_color,
                        COUNT(*) as count,
                        AVG(x) as center_x,
                        AVG(y) as center_y,
                        AVG(z) as center_z
                    FROM track_visualization_sphere
                    WHERE cluster = %s
                    GROUP BY cluster, cluster_color;
                """,
                    (cluster_id,),
                )

                cluster_row = cursor.fetchone()
                if not cluster_row:
                    raise HTTPException(
                        status_code=404, detail=f"Cluster {cluster_id} not found"
                    )

                cluster_info = {
                    "id": cluster_row["cluster"],
                    "color": cluster_row["cluster_color"],
                    "count": cluster_row["count"],
                    "center": [
                        cluster_row["center_x"],
                        cluster_row["center_y"],
                        cluster_row["center_z"],
                    ],
                }

                # Get all tracks in cluster
                cursor.execute(
                    """
                    SELECT 
                        tv.id,
                        tv.x,
                        tv.y,
                        tv.z,
                        tv.cluster,
                        tv.cluster_color,
                        m.title,
                        m.artist,
                        m.album,
                        m.genre,
                        m.year
                    FROM track_visualization_sphere tv
                    JOIN megaset m ON tv.id = m.id
                    WHERE tv.cluster = %s
                    ORDER BY m.artist, m.album, m.title;
                """,
                    (cluster_id,),
                )

                rows = cursor.fetchall()
                tracks = []
                for row in rows:
                    tracks.append(
                        {
                            "id": row["id"],
                            "x": row["x"],
                            "y": row["y"],
                            "z": row["z"],
                            "cluster": row["cluster"],
                            "cluster_color": row["cluster_color"],
                            "title": row["title"],
                            "artist": row["artist"],
                            "album": row["album"],
                            "genre": row["genre"],
                            "year": row["year"],
                        }
                    )

                return {
                    "cluster_id": cluster_id,
                    "count": cluster_info["count"],
                    "tracks": tracks,
                    "info": cluster_info,
                }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get cluster details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cluster: {str(e)}")


def get_track_neighbors(track_id: int, limit: int = 20):
    """Get nearest neighbors of a track in 3D space."""
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Get the track's coordinates
                cursor.execute(
                    """
                    SELECT x, y, z FROM track_visualization_sphere WHERE id = %s;
                """,
                    (track_id,),
                )

                track = cursor.fetchone()
                if not track:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Track {track_id} not found in visualization",
                    )

                tx, ty, tz = track["x"], track["y"], track["z"]

                # Find nearest neighbors using Euclidean distance
                cursor.execute(
                    """
                    SELECT 
                        tv.id,
                        tv.x,
                        tv.y,
                        tv.z,
                        tv.cluster,
                        tv.cluster_color,
                        m.title,
                        m.artist,
                        m.album,
                        m.genre,
                        m.year,
                        SQRT(POWER(tv.x - %s, 2) + POWER(tv.y - %s, 2) + POWER(tv.z - %s, 2)) as distance
                    FROM track_visualization_sphere tv
                    JOIN megaset m ON tv.id = m.id
                    WHERE tv.id != %s
                    ORDER BY distance
                    LIMIT %s;
                """,
                    (tx, ty, tz, track_id, limit),
                )

                rows = cursor.fetchall()
                neighbors = []
                for row in rows:
                    neighbors.append(
                        {
                            "id": row["id"],
                            "x": row["x"],
                            "y": row["y"],
                            "z": row["z"],
                            "cluster": row["cluster"],
                            "cluster_color": row["cluster_color"],
                            "title": row["title"],
                            "artist": row["artist"],
                            "album": row["album"],
                            "genre": row["genre"],
                            "year": row["year"],
                            "distance": float(row["distance"]),
                        }
                    )

                return {"track_id": track_id, "neighbors": neighbors}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get track neighbors: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get neighbors: {str(e)}"
        )
