from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.common import HealthResponse


class MusicTrack(BaseModel):
    id: int
    title: str
    artist: str
    album: str = "Graceland"
    track_number: Optional[int] = None
    created_at: datetime


class MusicResponse(BaseModel):
    status: str
    count: int
    tracks: List[MusicTrack]


class DatabaseListResponse(BaseModel):
    status: str
    databases: List[str]


class TableListResponse(BaseModel):
    status: str
    database: str
    tables: List[str]


class PostgresHealthResponse(HealthResponse):
    database: Optional[str] = Field(None, description="Database connection status")