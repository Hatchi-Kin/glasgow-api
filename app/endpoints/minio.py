from fastapi import APIRouter

from app.utils.minio import minio_health_check, create_new_bucket, list_bucket_objects


router = APIRouter(prefix="/MiniO", tags=["MiniO"])


@router.get("/health")
def check_minio():
    return minio_health_check()


@router.post("/bucket/{bucket_name}")
def create_bucket(bucket_name: str):
    return create_new_bucket(bucket_name)


@router.post("/buckets/{bucket_name}/objects")
def list_objects(bucket_name):
    return list_bucket_objects(bucket_name)
