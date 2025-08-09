from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("minio")


def get_minio_client():
    """Get MinIO client instance."""
    logger.debug(f"Creating MinIO client for endpoint: {settings.minio_endpoint}")
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def create_new_bucket(bucket_name: str):
    """Create a new bucket in Minio."""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            return {"message": f"Bucket {bucket_name} created successfully"}
        else:
            return {"message": f"Bucket {bucket_name} already exists"}
    except S3Error as e:
        raise RuntimeError(f"Failed to create bucket: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


def list_bucket_objects(bucket_name: str):
    """List all objects in a given bucket."""
    try:
        client = get_minio_client()

        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            raise HTTPException(
                status_code=404, detail=f"Bucket '{bucket_name}' not found"
            )

        # List objects
        objects = client.list_objects(bucket_name, recursive=True)
        object_list = []

        for obj in objects:
            object_list.append(
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": (
                        obj.last_modified.isoformat() if obj.last_modified else None
                    ),
                    "etag": obj.etag,
                }
            )

        return {
            "status": "success",
            "bucket": bucket_name,
            "count": len(object_list),
            "objects": object_list,
        }

    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def minio_health_check():
    """Simple health check for MinIO connection."""
    try:
        client = get_minio_client()
        # Try to list buckets as a simple health check
        buckets = list(client.list_buckets())
        return {
            "status": "healthy",
            "buckets_count": len(buckets),
            "buckets": [bucket.name for bucket in buckets],
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}