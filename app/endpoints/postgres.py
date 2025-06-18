from fastapi import APIRouter, Query
from app.utils.postgres import (
    get_postgres_version,
    setup_database,
    create_music_table_safe,
    populate_music_table_safe,
    list_tables_safe,
    get_table_data_safe,
    delete_table_safe,
    get_postgres_info,
)

router = APIRouter(prefix="/postgresql", tags=["PostgreSQL"])


@router.get("/health")
def check_database():
    return get_postgres_version()


@router.post("/setup")
def setup_db():
    return setup_database()


@router.post("/tables/music/create")
def create_music_table():
    return create_music_table_safe()


@router.post("/tables/music/populate")
def populate_music_table():
    return populate_music_table_safe()


@router.get("/tables")
def list_tables():
    return list_tables_safe()


@router.get("/tables/{table_name}")
def get_table_data(table_name: str, limit: int = Query(100), offset: int = Query(0)):
    return get_table_data_safe(table_name, limit, offset)


@router.get("/tables/music/tracks")
def get_music_tracks(limit: int = Query(20), offset: int = Query(0)):
    return get_table_data_safe("music", limit, offset)


@router.delete("/tables/{table_name}")
def delete_table(table_name: str):
    return delete_table_safe(table_name)


@router.get("/")
def postgres_info():
    return get_postgres_info()
