from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.common import HealthResponse


class MinIOObject(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    size: int
    last_modified: Optional[str] = None
    etag: str


class MinIOObjectListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str
    bucket: str
    count: int
    objects: List[MinIOObject]


class MinIOHealthResponse(HealthResponse):
    model_config = ConfigDict(extra="ignore")
    buckets_count: Optional[int] = Field(None, description="Number of buckets")
    buckets: Optional[List[str]] = Field(None, description="List of bucket names")


class BucketCreateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: str
