from fastapi import APIRouter

from app.utils.minio import check_minio_health, create_new_bucket


router = APIRouter(prefix="/MiniO", tags=["MiniO"])


@router.get("/health")
def check_minio():
    return check_minio_health()


@router.post("/bucket/{bucket_name}")
def create_bucket(bucket_name: str):
    return create_new_bucket(bucket_name)
