from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.common import HealthResponse


class MegasetTrack(BaseModel):
    id: int
    filename: str
    filepath: str
    relative_path: str
    album_folder: Optional[str] = None
    artist_folder: Optional[str] = None
    filesize: Optional[float] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[int] = None
    tracknumber: Optional[int] = None
    genre: Optional[str] = None
    top_5_genres: Optional[str] = None
    created_at: datetime


class MegasetResponse(BaseModel):
    status: str
    count: int
    tracks: List[MegasetTrack]


class DatabaseListResponse(BaseModel):
    status: str
    databases: List[str]


class TableListResponse(BaseModel):
    status: str
    database: str
    tables: List[str]


class PostgresHealthResponse(HealthResponse):
    database: Optional[str] = Field(None, description="Database connection status")