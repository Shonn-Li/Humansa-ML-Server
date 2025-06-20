from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ApiResponse:
    """Standard API response model"""
    message: str
    data: Any = None
    error: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"message": self.message}
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class JobResponse:
    """Response model for job-related endpoints"""
    job_id: str
    message: str
    status_url: str
    total_items: int = 0
    user_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "job_id": self.job_id,
            "message": self.message,
            "status_url": self.status_url
        }
        if self.total_items > 0:
            result["total_items"] = self.total_items
        if self.user_id is not None:
            result["user_id"] = self.user_id
        return result


@dataclass
class SearchResult:
    """Search result model"""
    note_id: int
    chunk_text: str
    source: str
    relevance_score: float
    preview: str = None
    note_title: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "note_id": self.note_id,
            "chunk_text": self.chunk_text,
            "source": self.source,
            "relevance_score": self.relevance_score
        }
        if self.preview:
            result["preview"] = self.preview
        if self.note_title:
            result["note_title"] = self.note_title
        return result
