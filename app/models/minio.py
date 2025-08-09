from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.common import HealthResponse


class MinIOObject(BaseModel):
    name: str
    size: int
    last_modified: Optional[str] = None
    etag: str


class MinIOObjectListResponse(BaseModel):
    status: str
    bucket: str
    count: int
    objects: List[MinIOObject]


class MinIOHealthResponse(HealthResponse):
    buckets_count: Optional[int] = Field(None, description="Number of buckets")
    buckets: Optional[List[str]] = Field(None, description="List of bucket names")


class BucketCreateResponse(BaseModel):
    message: str