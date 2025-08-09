from typing import List
from pydantic import BaseModel, Field


class MusicFile(BaseModel):
    filename: str
    path: str
    size: int


class MusicFileListResponse(BaseModel):
    files: List[MusicFile]
    path: str
    count: int


class FileUploadResponse(BaseModel):
    message: str
    filename: str
    path: str
    size: int


class FileRemoveResponse(BaseModel):
    message: str
    path: str


class FileRemoveRequest(BaseModel):
    file_path: str = Field(..., description="Relative path to the file within music folder")