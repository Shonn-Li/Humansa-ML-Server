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

    async def run_embedding_job(self, job_id: str, job_type: str, note_ids: List[int] = None, conversation_ids: List[int] = None, **kwargs):
        """Run embedding job in background for notes and/or conversations"""
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            job.start()

            # Calculate total items
            total_items = 0
            if note_ids:
                total_items += len(note_ids)
            if conversation_ids:
                total_items += len(conversation_ids)

            job.total_items = total_items

            logger.info(
                f"Starting background job {job_id}: {job_type} - Notes: {len(note_ids) if note_ids else 0}, Conversations: {len(conversation_ids) if conversation_ids else 0}")

            successfully_processed = 0
            failed_items = []
            batch_size = kwargs.get('batch_size', 5)

            # Process notes if provided
            if note_ids:
                from src.utility.note_utils import create_and_save_embeddings_separate

                for i in range(0, len(note_ids), batch_size):
                    batch = note_ids[i:i + batch_size]
                    logger.info(
                        f"Job {job_id}: Processing note batch {i//batch_size + 1}: {batch}")

                    for note_id in batch:
                        try:
                            create_and_save_embeddings_separate(note_id)
                            successfully_processed += 1
                            job.update_progress(
                                successfully_processed, total_items, len(failed_items))
                            logger.info(
                                f"Job {job_id}: Processed note {note_id}")
                        except Exception as e:
                            logger.error(
                                f"Job {job_id}: Failed to process note {note_id}: {e}")
                            failed_items.append({
                                "type": "note",
                                "id": note_id,
                                "error": str(e)
                            })
                            job.update_progress(
                                successfully_processed, total_items, len(failed_items))

                    # Small delay between batches
                    await asyncio.sleep(2)

            # Process conversations if provided
            if conversation_ids:
                from src.utility.postgres import get_db_connection
                from src.utility.conversation_embeddings import create_conversation_embeddings

                for i in range(0, len(conversation_ids), batch_size):
                    batch = conversation_ids[i:i + batch_size]
                    logger.info(
                        f"Job {job_id}: Processing conversation batch {i//batch_size + 1}: {batch}")

                    for conv_id in batch:
                        try:
                            # Get messages for this conversation
                            with get_db_connection() as conn:
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        """
                                        SELECT id, role, content, "createdAt"
                                        FROM message_v1
                                        WHERE "conversationId" = %s
                                        ORDER BY "createdAt"
                                    """,
                                        (conv_id,)
                                    )
                                    messages = cursor.fetchall()

                            if not messages:
                                logger.warning(
                                    f"No messages found for conversation {conv_id}")
                                continue

                            # Convert to expected format
                            message_list = []
                            for msg_id, role, content, created_at in messages:
                                message_list.append({
                                    'id': msg_id,
                                    'role': role,
                                    'content': content,
                                    'created_at': created_at
                                })

                            # Create embeddings
                            success = await create_conversation_embeddings(conv_id, message_list)

                            if success:
                                successfully_processed += 1
                                logger.info(
                                    f"Job {job_id}: Processed conversation {conv_id}")
                            else:
                                failed_items.append({
                                    "type": "conversation",
                                    "id": conv_id,
                                    "error": "Failed to create embeddings"
                                })

                            job.update_progress(
                                successfully_processed, total_items, len(failed_items))

                        except Exception as e:
                            logger.error(
                                f"Job {job_id}: Failed to process conversation {conv_id}: {e}")
                            failed_items.append({
                                "type": "conversation",
                                "id": conv_id,
                                "error": str(e)
                            })
                            job.update_progress(
                                successfully_processed, total_items, len(failed_items))

                    # Small delay between batches
                    await asyncio.sleep(2)

            # Job completed
            result = {
                "total_items": total_items,
                "total_notes": len(note_ids) if note_ids else 0,
                "total_conversations": len(conversation_ids) if conversation_ids else 0,
                "successfully_processed": successfully_processed,
                "failed_items": failed_items,
                "job_type": job_type
            }
            job.complete(result)

            logger.info(
                f"Background job {job_id} completed: {successfully_processed}/{total_items} items processed")

        except Exception as e:
            job.fail(str(e))
            logger.error(f"Background job {job_id} failed: {e}")


# Global job service instance
job_service = JobService()
