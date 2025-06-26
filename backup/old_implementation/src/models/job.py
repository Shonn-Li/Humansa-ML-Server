from datetime import datetime, timezone
from typing import Dict, Any
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundJob:
    """Background job model for tracking long-running tasks"""

    def __init__(self, job_id: str, job_type: str, user_id: int = None):
        self.job_id = job_id
        self.job_type = job_type
        self.user_id = user_id
        self.status = JobStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.total_items = 0
        self.processed_items = 0
        self.failed_items = 0
        self.error_message = None
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "error_message": self.error_message,
            "result": self.result
        }

    def start(self):
        """Mark job as started"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, result: Dict[str, Any] = None):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result

    def fail(self, error_message: str):
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message

    def update_progress(self, processed: int, total: int, failed: int = 0):
        """Update job progress"""
        self.processed_items = processed
        self.total_items = total
        self.failed_items = failed
        self.progress = int((processed / total) * 100) if total > 0 else 0
