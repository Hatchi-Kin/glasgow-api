from fastapi import APIRouter, Query

from app.models.common import StatusResponse
from app.models.visualization import (
    ClusterDetail,
    SearchResponse,
    StatsResponse,
)
from app.services.visualization import (
    create_visualization_table,
    load_visualization_data_from_minio,
    get_all_visualization_points,
    get_visualization_stats,
    search_tracks,
    get_cluster_details,
    get_track_neighbors,
)

router = APIRouter(prefix="/visualization", tags=["Visualization"])


@router.post("/create_table", response_model=StatusResponse)
def create_table_endpoint():
    """Create the track_visualization table."""
    return create_visualization_table()


@router.post("/load_data", response_model=StatusResponse)
def load_data_endpoint(
    bucket_name: str = Query(default="megaset-sqlite", description="MinIO bucket name"),
    object_name: str = Query(
        default="music_visualization_data.json", description="JSON file name"
    ),
):
    """Load visualization data from MinIO JSON file into the database."""
    return load_visualization_data_from_minio(bucket_name, object_name)


@router.get("/points")
def get_points_endpoint(
    limit: int = Query(
        default=10000, ge=1, le=50000, description="Maximum number of points to return"
    ),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """Get all visualization points with track metadata."""
    return get_all_visualization_points(limit, offset)


@router.get("/stats", response_model=StatsResponse)
def get_stats_endpoint():
    """Get statistics about the visualization data."""
    return get_visualization_stats()


@router.get("/search", response_model=SearchResponse)
def search_endpoint(
    q: str = Query(..., description="Search query for title, artist, album, or genre"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum results"),
):
    """Search tracks by title, artist, album, or genre."""
    return search_tracks(q, limit)


@router.get("/cluster/{cluster_id}", response_model=ClusterDetail)
def get_cluster_endpoint(cluster_id: int):
    """Get all tracks in a specific cluster."""
    return get_cluster_details(cluster_id)


@router.get("/track/{track_id}/neighbors")
def get_neighbors_endpoint(
    track_id: int,
    limit: int = Query(default=20, ge=1, le=100, description="Number of neighbors"),
):
    """Get nearest neighbors of a track in 3D space."""
    return get_track_neighbors(track_id, limit)
