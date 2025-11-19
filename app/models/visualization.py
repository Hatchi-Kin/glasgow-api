from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class TrackPoint(BaseModel):
    """Single track point in 3D space."""
    id: int = Field(..., description="Track ID")
    x: float = Field(..., description="X coordinate in 3D space")
    y: float = Field(..., description="Y coordinate in 3D space")
    z: float = Field(..., description="Z coordinate in 3D space")
    cluster: int = Field(..., description="Cluster ID (-1 for noise)")
    cluster_color: str = Field(..., description="Hex color for cluster")
    title: Optional[str] = Field(None, description="Track title")
    artist: Optional[str] = Field(None, description="Artist name")
    album: Optional[str] = Field(None, description="Album name")
    genre: Optional[str] = Field(None, description="Genre")
    year: Optional[int] = Field(None, description="Release year")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 725,
                "x": 1.234,
                "y": -0.567,
                "z": 0.890,
                "cluster": 5,
                "cluster_color": "#FF6B6B",
                "title": "No Biggie",
                "artist": "Logic",
                "album": "Young Sinatra: Undeniable",
                "genre": "Hip-Hop",
                "year": 2010
            }
        }


class ClusterInfo(BaseModel):
    """Information about a cluster."""
    id: int = Field(..., description="Cluster ID")
    color: str = Field(..., description="Hex color")
    count: int = Field(..., description="Number of tracks in cluster")
    center: List[float] = Field(..., description="[x, y, z] center coordinates")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 5,
                "color": "#FF6B6B",
                "count": 342,
                "center": [0.5, -0.2, 0.8]
            }
        }


class VisualizationData(BaseModel):
    """Complete visualization dataset."""
    points: List[TrackPoint] = Field(..., description="All track points")
    clusters: Dict[str, ClusterInfo] = Field(..., description="Cluster metadata")


class SearchResponse(BaseModel):
    """Search results."""
    query: str = Field(..., description="Search query")
    results: List[TrackPoint] = Field(..., description="Matching tracks")
    total_results: int = Field(..., description="Total matches (before limit)")


class StatsResponse(BaseModel):
    """Visualization statistics."""
    total_tracks: int = Field(..., description="Total number of tracks")
    total_clusters: int = Field(..., description="Number of clusters")
    genres: Dict[str, int] = Field(..., description="Track count by genre")
    top_genres: List[tuple] = Field(..., description="Top 10 genres")
    largest_cluster: Optional[ClusterInfo] = Field(None, description="Largest cluster info")


class ClusterDetail(BaseModel):
    """Detailed cluster information."""
    cluster_id: int = Field(..., description="Cluster ID")
    count: int = Field(..., description="Number of tracks")
    tracks: List[TrackPoint] = Field(..., description="All tracks in cluster")
    info: Optional[ClusterInfo] = Field(None, description="Cluster metadata")
