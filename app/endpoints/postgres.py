from fastapi import APIRouter

from app.utils.postgres import setup_music_db, query_music, health_check


router = APIRouter(prefix="/postgresql", tags=["PostgreSQL"])


@router.get("/health")
def check_health():
    return health_check()


@router.get("/setup")
def setup():
    return setup_music_db()


@router.get("/music")
def get_music():
    return query_music()
