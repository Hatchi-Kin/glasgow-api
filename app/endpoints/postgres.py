from fastapi import APIRouter

from app.models.common import StatusResponse
from app.models.postgres import (
    MusicResponse,
    PostgresHealthResponse,
    DatabaseListResponse,
    TableListResponse,
)
from app.services.postgres.service import (
    setup_music_db,
    query_music,
    health_check,
    list_all_dbs_from_postgres,
    list_tables_in_db,
)


router = APIRouter(prefix="/postgresql", tags=["PostgreSQL"])


@router.get("/health", response_model=PostgresHealthResponse)
def check_health():
    return health_check()


@router.get("/setup_music", response_model=StatusResponse)
def setup():
    return setup_music_db()


@router.get("/music", response_model=MusicResponse)
def get_music():
    return query_music()


@router.get("/databases", response_model=DatabaseListResponse)
def get_databases():
    return list_all_dbs_from_postgres()


@router.get("/tables/{db_name}", response_model=TableListResponse)
def get_tables(db_name: str):
    return list_tables_in_db(db_name)
