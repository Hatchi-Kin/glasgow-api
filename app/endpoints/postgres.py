from fastapi import APIRouter

from app.models.common import StatusResponse
from app.models.postgres import (
    MegasetResponse,
    MegasetTrack,
    PostgresHealthResponse,
    DatabaseListResponse,
    TableListResponse,
)
from app.services.postgres.service import (
    migrate_music_data_from_sqlite,
    query_megaset,
    get_random_megaset_track,
    health_check,
    list_all_dbs_from_postgres,
    list_tables_in_db,
)


router = APIRouter(prefix="/postgresql", tags=["PostgreSQL"])


@router.get("/health", response_model=PostgresHealthResponse)
def check_health():
    return health_check()


@router.post("/migrate_music", response_model=StatusResponse)
def migrate_music():
    return migrate_music_data_from_sqlite()


@router.get("/megaset", response_model=MegasetResponse)
def get_megaset(limit: int = 100, offset: int = 0):
    return query_megaset(limit=limit, offset=offset)


@router.get("/megaset/random", response_model=MegasetTrack)
def get_random_track():
    return get_random_megaset_track()


@router.get("/databases", response_model=DatabaseListResponse)
def get_databases():
    return list_all_dbs_from_postgres()


@router.get("/tables/{db_name}", response_model=TableListResponse)
def get_tables(db_name: str):
    return list_tables_in_db(db_name)
