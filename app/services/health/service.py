from typing import Dict, Any
from app.core.logging import get_logger
from app.services.postgres.service import health_check as postgres_health
from app.services.minio.service import minio_health_check

logger = get_logger("health")


def comprehensive_health_check() -> Dict[str, Any]:
    """
    Perform comprehensive health check of all services.

    Returns:
        Dict containing overall status and individual service statuses
    """
    logger.info("Starting comprehensive health check")

    services = {}
    overall_healthy = True

    # Check PostgreSQL
    try:
        postgres_status = postgres_health()
        services["postgres"] = postgres_status
        if postgres_status.get("status") != "healthy":
            overall_healthy = False
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        services["postgres"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check MinIO
    try:
        minio_status = minio_health_check()
        services["minio"] = minio_status
        if minio_status.get("status") != "healthy":
            overall_healthy = False
    except Exception as e:
        logger.error(f"MinIO health check failed: {e}")
        services["minio"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    result = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "services": services,
        "timestamp": logger.handlers[0].formatter.formatTime(
            logger.makeRecord("health", 20, "", 0, "", (), None)
        )
        if logger.handlers
        else None,
    }

    logger.info(
        f"Health check completed: {'healthy' if overall_healthy else 'unhealthy'}"
    )
    return result
