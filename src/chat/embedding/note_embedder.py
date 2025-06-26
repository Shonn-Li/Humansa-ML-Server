"""
NoteEmbedder - Independent note embedding functionality.

COMPLETELY INDEPENDENT MODULE - No external dependencies.
All database operations, text processing, and OpenAI client are self-contained.
"""

import logging
import asyncio
from typing import List, Tuple, Optional, Dict, Any

from ..postgres.embedding_operations import EmbeddingDBOperations
from .embedding_provider_selector import EmbeddingProviderSelector
from .text_processing import TextProcessor

logger = logging.getLogger(__name__)


class NoteEmbedder:
    """Handles embedding creation and management for notes"""

    def __init__(self):
        self.embedder = EmbeddingProviderSelector().get_embedding_client()
        self.text_processor = TextProcessor()
        self.db = EmbeddingDBOperations()
        logger.info("NoteEmbedder initialized with independent modules")

    async def get_all_notes(self) -> List[int]:
        """Get all note IDs in the system"""
        return await asyncio.to_thread(self.db.get_all_notes)

    async def get_user_notes(self, user_id: int) -> List[int]:
        """Get all note IDs for a specific user"""
        return await asyncio.to_thread(self.db.get_user_notes, user_id)

    async def get_notes_without_embeddings(self, note_ids: List[int]) -> List[int]:
        """Get notes that don't have embeddings yet"""
        if not note_ids:
            return []
        return await asyncio.to_thread(self.db.get_notes_without_embeddings, note_ids)

    async def create_note_embedding(self, note_id: int) -> bool:
        """
        Create and save embeddings for a note with separate AI and user content.

        Args:
            note_id: ID of the note to embed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get separated content
            ai_content, user_content, note_type = await asyncio.to_thread(
                self.db.get_note_content_separate, note_id
            )

            if not ai_content and not user_content:
                logger.warning(
                    f"No content found for note {note_id}, marking to skip embedding")
                await asyncio.to_thread(self.db.mark_note_skip_embedding, note_id)
                return False

            logger.info(
                f"Note {note_id}: Processing AI content ({len(ai_content)} chars) "
                f"and user content ({len(user_content)} chars) separately"
            )

            # Prepare chunks and embeddings
            all_chunks_for_embedding = []
            chunk_metadata = []

            # Process AI content (summaries) separately
            if ai_content.strip():
                ai_chunks = self.text_processor.split_text(ai_content)
                logger.info(
                    f"Note {note_id}: Generated {len(ai_chunks)} AI content chunks")

                for chunk in ai_chunks:
                    all_chunks_for_embedding.append(chunk)
                    chunk_metadata.append((chunk, "summary"))

            # Process user content separately
            if user_content.strip():
                user_chunks = self.text_processor.split_text(user_content)
                logger.info(
                    f"Note {note_id}: Generated {len(user_chunks)} user content chunks ({note_type})")

                for chunk in user_chunks:
                    all_chunks_for_embedding.append(chunk)
                    chunk_metadata.append((chunk, note_type))

            if not all_chunks_for_embedding:
                logger.warning(f"No valid chunks generated for note {note_id}")
                return False

            # Create embeddings in batches
            logger.info(
                f"Creating embeddings for {len(all_chunks_for_embedding)} chunks")
            all_embeddings = await asyncio.to_thread(
                self.embedder.get_embeddings_with_retry,
                all_chunks_for_embedding,
                max_retries=3,
                batch_size=50
            )

            # Combine embeddings with metadata
            embeddings_data = []
            for embedding, (chunk_text, source) in zip(all_embeddings, chunk_metadata):
                embeddings_data.append((embedding, chunk_text, source))

            # Save embeddings
            await asyncio.to_thread(self.db.save_note_embeddings, note_id, embeddings_data)

            logger.info(
                f"Note {note_id}: Saved {len(embeddings_data)} embeddings with separate content")
            return True

        except Exception as e:
            logger.error(f"Failed to create embedding for note {note_id}: {e}")
            return False

    async def bulk_embed_notes(
        self,
        note_ids: List[int],
        batch_size: int = 10,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Bulk embed multiple notes with progress tracking.

        Args:
            note_ids: List of note IDs to embed
            batch_size: Number of notes to process in parallel
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with embedding results
        """
        if not note_ids:
            return {"embedded_count": 0, "failed_notes": [], "total_notes": 0}

        embedded_count = 0
        failed_notes = []

        # Process in batches to limit concurrent API calls
        for i in range(0, len(note_ids), batch_size):
            batch = note_ids[i:i + batch_size]

            # Create tasks for this batch
            tasks = [self.create_note_embedding(note_id) for note_id in batch]

            # Wait for batch completion
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for note_id, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Exception embedding note {note_id}: {result}")
                    failed_notes.append({"id": note_id, "error": str(result)})
                elif result:
                    embedded_count += 1
                else:
                    failed_notes.append(
                        {"id": note_id, "error": "Unknown embedding failure"})

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(
                        embedded_count + len(failed_notes), len(note_ids))

            # Small delay between batches
            if i + batch_size < len(note_ids):
                await asyncio.sleep(2)

        return {
            "embedded_count": embedded_count,
            "failed_notes": failed_notes,
            "total_notes": len(note_ids)
        }

    def has_embedding(self, note_id: int) -> bool:
        """Check if a note has embeddings (synchronous version)"""
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) FROM embedding_v1 WHERE type_id = %s AND type = 'note'",
                (note_id,),
                fetch_type='scalar'
            )
            return result > 0
        except Exception as e:
            logger.error(f"Error checking embeddings for note {note_id}: {e}")
            return False

    async def has_embedding_async(self, note_id: int) -> bool:
        """Check if a note has embeddings (async version)"""
        return await asyncio.to_thread(self.has_embedding, note_id)
