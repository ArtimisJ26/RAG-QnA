from fastapi import APIRouter, HTTPException
import asyncio
from typing import Dict, Optional
from pydantic import BaseModel
import time

router = APIRouter()

# In-memory storage for embedding status
# Structure: {filename: {status, progress, start_time}}
embedding_status: Dict[str, Dict] = {}

class EmbeddingProgress(BaseModel):
    status: str  # 'pending' | 'processing' | 'complete' | 'error'
    progress: int
    error_message: Optional[str] = None

def init_embedding_status(filename: str):
    """Initialize embedding status for a file"""
    embedding_status[filename] = {
        'status': 'pending',
        'progress': 0,
        'start_time': time.time(),
        'error_message': None
    }

def update_embedding_status(filename: str, status: str, progress: int, error_message: Optional[str] = None):
    """Update embedding status for a file"""
    if filename in embedding_status:
        embedding_status[filename].update({
            'status': status,
            'progress': progress,
            'error_message': error_message
        })

def cleanup_old_status():
    """Remove status entries older than 1 hour"""
    current_time = time.time()
    to_remove = []
    for filename, status in embedding_status.items():
        if current_time - status['start_time'] > 3600:  # 1 hour
            to_remove.append(filename)
    
    for filename in to_remove:
        del embedding_status[filename]

@router.get("/{filename}")
async def get_embedding_status(filename: str):
    cleanup_old_status()
    
    if filename not in embedding_status:
        raise HTTPException(
            status_code=404,
            detail=f"No embedding status found for file: {filename}"
        )
    
    status = embedding_status[filename]
    return {
        "status": status['status'],
        "progress": status['progress'],
        "error_message": status['error_message']
    }

# Export functions to be used by other modules
__all__ = ['router', 'init_embedding_status', 'update_embedding_status'] 