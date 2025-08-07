import os
from pathlib import Path
from typing import Optional
import aiofiles
import logging

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

# Configuration
MUSIC_FOLDER_PATH = "/music"
ALLOWED_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.aac'}

def _get_music_folder() -> Path:
    """Get and validate the music folder path"""
    music_folder = Path(MUSIC_FOLDER_PATH)
    
    try:
        music_folder.mkdir(parents=True, exist_ok=True)
        if not os.access(music_folder, os.W_OK):
            raise PermissionError(f"No write permission to {music_folder}")
        return music_folder
    except Exception as e:
        logger.error(f"Error accessing music folder: {e}")
        raise HTTPException(status_code=500, detail=f"Cannot access music folder: {e}")

async def add_music_file(file: UploadFile, subfolder: Optional[str] = None) -> dict:
    """
    Add a music file to the Navidrome music folder
    
    Args:
        file: The uploaded music file
        subfolder: Optional subfolder within music directory (e.g., "Artist/Album")
    
    Returns:
        dict: Success message with file info
    """
    try:
        music_folder = _get_music_folder()
        
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Determine target path
        if subfolder:
            target_dir = music_folder / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = music_folder
        
        target_path = target_dir / file.filename
        
        # Check if file already exists
        if target_path.exists():
            raise HTTPException(
                status_code=409, 
                detail=f"File {file.filename} already exists in {target_dir.relative_to(music_folder)}"
            )
        
        # Save the file
        async with aiofiles.open(target_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Successfully added music file: {target_path}")
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "path": str(target_path.relative_to(music_folder)),
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding music file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add music file: {e}")

async def remove_music_file(file_path: str) -> dict:
    """
    Remove a music file from the Navidrome music folder
    
    Args:
        file_path: Relative path to the file within the music folder
    
    Returns:
        dict: Success message
    """
    try:
        music_folder = _get_music_folder()
        
        # Resolve the full path
        target_path = music_folder / file_path
        
        # Security check: ensure path is within music folder
        if not str(target_path.resolve()).startswith(str(music_folder.resolve())):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file path: path traversal not allowed"
            )
        
        # Check if file exists
        if not target_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"File not found: {file_path}"
            )
        
        # Check if it's a file (not directory)
        if not target_path.is_file():
            raise HTTPException(
                status_code=400, 
                detail=f"Path is not a file: {file_path}"
            )
        
        # Remove the file
        target_path.unlink()
        
        # Remove empty parent directories if they exist within music folder
        parent = target_path.parent
        while parent != music_folder and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
        
        logger.info(f"Successfully removed music file: {target_path}")
        
        return {
            "message": "File removed successfully",
            "path": file_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing music file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove music file: {e}")

def list_music_files(subfolder: Optional[str] = None) -> dict:
    """
    List music files in the folder
    
    Args:
        subfolder: Optional subfolder to list
    
    Returns:
        dict: List of files
    """
    try:
        music_folder = _get_music_folder()
        
        if subfolder:
            search_path = music_folder / subfolder
        else:
            search_path = music_folder
        
        if not search_path.exists():
            return {"files": [], "path": str(search_path.relative_to(music_folder)) if subfolder else "", "count": 0}
        
        files = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(music_folder)),
                    "size": file_path.stat().st_size
                })
        
        return {
            "files": sorted(files, key=lambda x: x["filename"]),
            "path": str(search_path.relative_to(music_folder)) if subfolder else "",
            "count": len(files)
        }
        
    except Exception as e:
        logger.error(f"Error listing music files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list music files: {e}")