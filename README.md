# Glasgow FastAPI

A simple FastAPI application for the Glasgow GitOps learning project.

## Features

- Health checks for database and MinIO connections
- Bucket creation in MinIO
- PostgreSQL connectivity testing

## Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t glasgow-fastapi .
docker run -p 8000:8000 glasgow-fastapi
```