import os

from minio import Minio
from minio.error import S3Error


def get_minio_client():
    """Create and return a Minio client instance."""
    try:
        client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,
        )
        return client
    except S3Error as e:
        raise RuntimeError(f"Failed to create Minio client: {str(e)}")


def check_minio_health():
    """Check the health of the Minio server."""
    try:
        client = get_minio_client()
        buckets = list(client.list_buckets())
        return {"status": "connected", "buckets": [b.name for b in buckets]}
    except S3Error as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


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
