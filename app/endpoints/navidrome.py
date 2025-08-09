from typing import Optional

from fastapi import APIRouter, UploadFile, File, Query

from app.models.navidrome import FileUploadResponse, FileRemoveResponse, MusicFileListResponse
from app.services.navidrome.service import add_music_file, remove_music_file, list_music_files


router = APIRouter(prefix="/navidrome", tags=["navidrome"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_music_file(
    file: UploadFile = File(...),
    subfolder: Optional[str] = Query(
        None, description="Optional subfolder path (e.g., 'Artist/Album')"
    ),
):
    """Upload a music file to Navidrome music folder"""
    return await add_music_file(file, subfolder)


@router.delete("/remove", response_model=FileRemoveResponse)
async def remove_music_file_endpoint(
    file_path: str = Query(
        ..., description="Relative path to the file within music folder"
    )
):
    """Remove a music file from Navidrome music folder"""
    return await remove_music_file(file_path)


@router.get("/list", response_model=MusicFileListResponse)
async def list_music_files_endpoint(
    subfolder: Optional[str] = Query(None, description="Optional subfolder to list")
):
    """List music files in the folder"""
    return list_music_files(subfolder)
