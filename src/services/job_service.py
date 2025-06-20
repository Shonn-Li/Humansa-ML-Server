import asyncio
import uuid
import logging
from typing import Dict, List
from src.models.job import BackgroundJob, JobStatus

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing background jobs"""
    
    def __init__(self):
        # In production, use Redis or database instead of in-memory storage
        self.jobs: Dict[str, BackgroundJob] = {}
    
    def create_job(self, job_type: str, user_id: int = None) -> str:
        """Create a new background job and return its ID"""
        job_id = str(uuid.uuid4())
        job = BackgroundJob(job_id, job_type, user_id)
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id
    
    def get_job(self, job_id: str) -> BackgroundJob:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[BackgroundJob]:
        """List all jobs"""
        return list(self.jobs.values())
    
    async def run_embedding_job(self, job_id: str, job_type: str, note_ids: List[int], **kwargs):
        """Run embedding job in background"""
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        try:
            job.start()
            job.total_items = len(note_ids)
            
            logger.info(f"Starting background job {job_id}: {job_type} for {len(note_ids)} notes")
            
            successfully_processed = 0
            failed_notes = []
            batch_size = kwargs.get('batch_size', 5)
            
            # Import the embedding function
            from src.utility.note_utils import create_and_save_embeddings_separate
            
            for i in range(0, len(note_ids), batch_size):
                batch = note_ids[i:i + batch_size]
                logger.info(f"Job {job_id}: Processing batch {i//batch_size + 1}: notes {batch}")
                
                for note_id in batch:
                    try:
                        create_and_save_embeddings_separate(note_id)
                        successfully_processed += 1
                        job.update_progress(successfully_processed, len(note_ids), len(failed_notes))
                        logger.info(f"Job {job_id}: Processed note {note_id}")
                    except Exception as e:
                        logger.error(f"Job {job_id}: Failed to process note {note_id}: {e}")
                        failed_notes.append({
                            "note_id": note_id,
                            "error": str(e)
                        })
                        job.update_progress(successfully_processed, len(note_ids), len(failed_notes))
                
                # Small delay between batches
                await asyncio.sleep(2)
            
            # Job completed
            result = {
                "total_notes": len(note_ids),
                "successfully_processed": successfully_processed,
                "failed_notes": failed_notes,
                "job_type": job_type
            }
            job.complete(result)
            
            logger.info(f"Background job {job_id} completed: {successfully_processed}/{len(note_ids)} notes processed")
            
        except Exception as e:
            job.fail(str(e))
            logger.error(f"Background job {job_id} failed: {e}")


# Global job service instance
job_service = JobService()
