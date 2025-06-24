from fastapi import APIRouter

from app.utils.postgres import (
    setup_music_db,
    query_music,
    health_check,
    list_all_dbs_from_postgres,
)


router = APIRouter(prefix="/postgresql", tags=["PostgreSQL"])


@router.get("/health")
def check_health():
    return health_check()


@router.get("/setup_music")
def setup():
    return setup_music_db()


@router.get("/music")
def get_music():
    return query_music()


@router.get("/databases")
def get_databases():
    return list_all_dbs_from_postgres()
