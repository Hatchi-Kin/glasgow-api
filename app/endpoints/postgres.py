from fastapi import APIRouter

from app.utils.postgres import get_postgres_version


router = APIRouter(prefix="/PostgreSQL", tags=["PostgreSQL"])


@router.get("/health")
def check_database():
    return get_postgres_version()
