from fastapi import FastAPI

from app.endpoints.minio import router as minio_router
from app.endpoints.postgres import router as postgres_router
from app.endpoints.health import router as health_router
from app.endpoints.navidrome import router as navidrome_router

app = FastAPI(title="Glasgow GitOps API", version="1.0.0")

app.include_router(minio_router)
app.include_router(postgres_router)
app.include_router(health_router)
app.include_router(navidrome_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
