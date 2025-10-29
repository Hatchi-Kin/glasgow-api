from fastapi import APIRouter
from typing import Dict, Any

from app.models.common import StatusResponse
from app.services.health.service import comprehensive_health_check


router = APIRouter(tags=["Health"])


@router.get("/", response_model=StatusResponse)
def read_root():
    return {"message": "Hello from Glasgow GitOps!", "status": "running"}


@router.get("/health")
def simple_health_check():
    """Simple health check for basic liveness probe."""
    return {"status": "very healthy"}


@router.get("/health/comprehensive", response_model=StatusResponse)
def health_check() -> Dict[str, Any]:
    """Comprehensive health check of all services."""
    return comprehensive_health_check()
