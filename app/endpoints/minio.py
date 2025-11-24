from fastapi import APIRouter

from app.models.minio import (
    MinIOHealthResponse,
    BucketCreateResponse,
    MinIOObjectListResponse,
)
from app.services.minio.service import (
    minio_health_check,
    create_new_bucket,
    list_bucket_objects,
)


router = APIRouter(prefix="/MiniO", tags=["MiniO"])


@router.get("/health", response_model=MinIOHealthResponse)
def check_minio():
    return minio_health_check()


@router.post("/bucket/{bucket_name}", response_model=BucketCreateResponse)
def create_bucket(bucket_name: str):
    return create_new_bucket(bucket_name)


@router.get("/buckets/{bucket_name}/objects", response_model=MinIOObjectListResponse)
def list_objects(bucket_name: str):
    return list_bucket_objects(bucket_name)
