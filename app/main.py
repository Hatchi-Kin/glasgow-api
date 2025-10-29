from fastapi import FastAPI

from app.core.config import settings, log_config_info
from app.core.logging import setup_logging, get_logger
from app.endpoints.minio import router as minio_router
from app.endpoints.postgres import router as postgres_router
from app.endpoints.health import router as health_router
from app.endpoints.navidrome import router as navidrome_router

# Setup logging
setup_logging()
logger = get_logger("main")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)


logger.info(f"Starting {settings.app_name} v{settings.app_version}")
logger.info(log_config_info())

app.include_router(minio_router)
app.include_router(postgres_router)
app.include_router(health_router)
app.include_router(navidrome_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
