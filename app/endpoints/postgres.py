from fastapi import APIRouter, Body

from app.models.common import StatusResponse
from app.models.postgres import (
    MegasetResponse,
    MegasetTrack,
    PostgresHealthResponse,
    DatabaseListResponse,
    TableListResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)
from app.services.postgres.service import (
    create_users_table,
    migrate_music_data_from_sqlite,
    query_megaset,
    get_random_megaset_track,
    add_embedding_512_column,
    bulk_insert_512_embeddings,
    find_similar_tracks_by_512_embedding,
    health_check,
        list_all_dbs_from_postgres,
        list_tables_in_db,
        insert_admin_user,
        update_user_password,
    )
    
    
    router = APIRouter(prefix="/postgresql", tags=["PostgreSQL"])
    
    
    @router.get("/health", response_model=PostgresHealthResponse)
    def check_health():
        return health_check()
    
    
    @router.post("/migrate_music", response_model=StatusResponse)
    def migrate_music():
        return migrate_music_data_from_sqlite()
    
    
    @router.post("/megaset/add_512_embedding_column", response_model=StatusResponse)
    def add_512_embedding_column_endpoint():
        return add_embedding_512_column()
    
    
    @router.post("/megaset/bulk_insert_512_embeddings", response_model=StatusResponse)
    def bulk_insert_512_embeddings_endpoint():
        return bulk_insert_512_embeddings()
    
    
    @router.post("/megaset/search_by_512_embedding", response_model=VectorSearchResponse)
    def search_by_512_embedding_endpoint(request: VectorSearchRequest = Body(...)):
        return find_similar_tracks_by_512_embedding(request.query_embedding, request.limit)
    
    
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
    
    
    @router.post("/users/create_table", response_model=StatusResponse)
    def create_users_table_endpoint():
        return create_users_table()
    
    
    @router.post("/admin/create-initial-admin", response_model=StatusResponse)
    def create_initial_admin_endpoint(
        email: str = Body(..., embed=True),
        username: str = Body(..., embed=True),
        hashed_password: str = Body(..., embed=True),
    ):
        """Creates an initial admin user with a pre-hashed password."""
        return insert_admin_user(email, username, hashed_password)
    
    
    @router.post("/users/update-password", response_model=StatusResponse)
    def update_user_password_endpoint(
        email: str = Body(..., embed=True),
        new_hashed_password: str = Body(..., embed=True),
    ):
        """Updates a user's password with a new pre-hashed password."""
        return update_user_password(email, new_hashed_password)
    