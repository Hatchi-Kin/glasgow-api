import os

from fastapi import FastAPI, HTTPException
from minio import Minio
import psycopg2

app = FastAPI(title="Glasgow GitOps API", version="1.0.0")


@app.get("/")
def read_root():
    return {"message": "Hello from Glasgow GitOps!", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
def check_database():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        conn.close()
        return {"status": "connected", "db_version": version[0]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/health/minio")
def check_minio():
    try:
        client = Minio(
            os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,
        )
        buckets = list(client.list_buckets())
        return {"status": "connected", "buckets": [b.name for b in buckets]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/bucket/{bucket_name}")
def create_bucket(bucket_name: str):
    try:
        client = Minio(
            os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,
        )
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            return {"message": f"Bucket {bucket_name} created successfully"}
        else:
            return {"message": f"Bucket {bucket_name} already exists"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
