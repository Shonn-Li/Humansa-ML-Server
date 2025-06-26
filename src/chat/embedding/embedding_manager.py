"""
EmbeddingManager - Main coordinator for embedding operations.

Provides async embedding checks and launches embedding creation 
for notes/conversations that lack embeddings during RAG queries.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from .note_embedder import NoteEmbedder
from .conversation_embedder import ConversationEmbedder

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Main embedding manager that coordinates embedding operations
    across notes and conversations.
    """

    def __init__(self):
        self.note_embedder = NoteEmbedder()
        self.conversation_embedder = ConversationEmbedder()
        self._embedding_tasks: Dict[str, asyncio.Task] = {}

    async def check_and_ensure_embeddings(
        self,
        note_ids: List[int] = None,
        conversation_ids: List[int] = None,
        max_missing_to_embed: int = 10
    ) -> Tuple[List[int], List[int]]:
        """
        Check for missing embeddings and launch async embedding creation.

        Args:
            note_ids: List of note IDs to check
            conversation_ids: List of conversation IDs to check
            max_missing_to_embed: Max number of missing embeddings to create immediately

        Returns:
            Tuple of (notes_missing_embeddings, conversations_missing_embeddings)
        """
        notes_missing = []
        conversations_missing = []

        # Check notes for missing embeddings
        if note_ids:
            notes_missing = await self.note_embedder.get_notes_without_embeddings(note_ids)
            if notes_missing:
                logger.info(
                    f"Found {len(notes_missing)} notes without embeddings")

                # Limit mass embedding to prevent API cost explosion
                if len(notes_missing) > max_missing_to_embed:
                    logger.warning(
                        f"Too many notes missing embeddings ({len(notes_missing)}). "
                        f"Limiting to {max_missing_to_embed} to prevent cost explosion."
                    )
                    notes_to_embed = notes_missing[:max_missing_to_embed]
                else:
                    notes_to_embed = notes_missing

                # Launch async embedding creation
                if notes_to_embed:
                    task_key = f"notes_{','.join(map(str, notes_to_embed))}"
                    if task_key not in self._embedding_tasks:
                        task = asyncio.create_task(
                            self._embed_notes_async(notes_to_embed)
                        )
                        self._embedding_tasks[task_key] = task

        # Check conversations for missing embeddings
        if conversation_ids:
            conversations_missing = await self.conversation_embedder.get_conversations_without_embeddings(conversation_ids)
            if conversations_missing:
                logger.info(
                    f"Found {len(conversations_missing)} conversations without embeddings")

                # Limit mass embedding
                if len(conversations_missing) > max_missing_to_embed:
                    logger.warning(
                        f"Too many conversations missing embeddings ({len(conversations_missing)}). "
                        f"Limiting to {max_missing_to_embed} to prevent cost explosion."
                    )
                    conversations_to_embed = conversations_missing[:max_missing_to_embed]
                else:
                    conversations_to_embed = conversations_missing

                # Launch async embedding creation
                if conversations_to_embed:
                    task_key = f"conversations_{','.join(map(str, conversations_to_embed))}"
                    if task_key not in self._embedding_tasks:
                        task = asyncio.create_task(
                            self._embed_conversations_async(
                                conversations_to_embed)
                        )
                        self._embedding_tasks[task_key] = task

        return notes_missing, conversations_missing

    async def _embed_notes_async(self, note_ids: List[int]) -> None:
        """Async task to embed notes in background"""
        try:
            logger.info(f"Starting async embedding for {len(note_ids)} notes")
            for note_id in note_ids:
                try:
                    await self.note_embedder.create_note_embedding(note_id)
                    logger.info(f"Successfully embedded note {note_id}")
                except Exception as e:
                    logger.error(f"Failed to embed note {note_id}: {e}")

                # Small delay between embeddings to be API-friendly
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in async note embedding: {e}")
        finally:
            # Clean up task reference
            task_key = f"notes_{','.join(map(str, note_ids))}"
            self._embedding_tasks.pop(task_key, None)

    async def _embed_conversations_async(self, conversation_ids: List[int]) -> None:
        """Async task to embed conversations in background"""
        try:
            logger.info(
                f"Starting async embedding for {len(conversation_ids)} conversations")
            for conv_id in conversation_ids:
                try:
                    await self.conversation_embedder.create_conversation_embedding(conv_id)
                    logger.info(
                        f"Successfully embedded conversation {conv_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to embed conversation {conv_id}: {e}")

                # Small delay between embeddings
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in async conversation embedding: {e}")
        finally:
            # Clean up task reference
            task_key = f"conversations_{','.join(map(str, conversation_ids))}"
            self._embedding_tasks.pop(task_key, None)

    async def embed_all_missing_notes(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Admin function to embed all missing notes.

        Args:
            user_id: If provided, only embed notes for this user

        Returns:
            Status dict with embedding results
        """
        if user_id:
            all_notes = await self.note_embedder.get_user_notes(user_id)
        else:
            all_notes = await self.note_embedder.get_all_notes()

        missing_notes = await self.note_embedder.get_notes_without_embeddings(all_notes)

        if not missing_notes:
            return {
                "status": "success",
                "message": f"All {len(all_notes)} notes already have embeddings",
                "embedded_count": 0,
                "total_notes": len(all_notes)
            }

        # Embed all missing notes
        embedded_count = 0
        failed_notes = []

        for note_id in missing_notes:
            try:
                await self.note_embedder.create_note_embedding(note_id)
                embedded_count += 1
                logger.info(
                    f"Embedded note {note_id} ({embedded_count}/{len(missing_notes)})")

                # Small delay to be API-friendly
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to embed note {note_id}: {e}")
                failed_notes.append({"id": note_id, "error": str(e)})

        return {
            "status": "success",
            "message": f"Embedded {embedded_count} notes",
            "embedded_count": embedded_count,
            "total_notes": len(all_notes),
            "failed_notes": failed_notes,
            "total_missing": len(missing_notes)
        }

    async def embed_all_missing_conversations(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Admin function to embed all missing conversations.

        Args:
            user_id: If provided, only embed conversations for this user

        Returns:
            Status dict with embedding results
        """
        if user_id:
            all_conversations = await self.conversation_embedder.get_user_conversations(user_id)
        else:
            all_conversations = await self.conversation_embedder.get_all_conversations()

        missing_conversations = await self.conversation_embedder.get_conversations_without_embeddings(all_conversations)

        if not missing_conversations:
            return {
                "status": "success",
                "message": f"All {len(all_conversations)} conversations already have embeddings",
                "embedded_count": 0,
                "total_conversations": len(all_conversations)
            }

        # Embed all missing conversations
        embedded_count = 0
        failed_conversations = []

        for conv_id in missing_conversations:
            try:
                await self.conversation_embedder.create_conversation_embedding(conv_id)
                embedded_count += 1
                logger.info(
                    f"Embedded conversation {conv_id} ({embedded_count}/{len(missing_conversations)})")

                # Small delay to be API-friendly
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to embed conversation {conv_id}: {e}")
                failed_conversations.append({"id": conv_id, "error": str(e)})

        return {
            "status": "success",
            "message": f"Embedded {embedded_count} conversations",
            "embedded_count": embedded_count,
            "total_conversations": len(all_conversations),
            "failed_conversations": failed_conversations,
            "total_missing": len(missing_conversations)
        }

    async def embed_notes_async(self, note_ids: List[int]) -> None:
        """
        Public method to trigger background embedding for specific notes
        Used by RAG processor for background embedding
        """
        if not note_ids:
            return

        logger.info(f"Starting background embedding for {len(note_ids)} notes")
        await self._embed_notes_async(note_ids)

    async def embed_conversations_async(self, conversation_ids: List[int]) -> None:
        """
        Public method to trigger background embedding for specific conversations
        Used by RAG processor for background embedding
        """
        if not conversation_ids:
            return

        logger.info(
            f"Starting background embedding for {len(conversation_ids)} conversations")
        await self._embed_conversations_async(conversation_ids)

    async def get_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Get embedding vector for a search query.
        Used by file attachment manager for similarity search.

        Args:
            query: Text query to embed

        Returns:
            List of floats representing the embedding vector, or None if failed
        """
        try:
            # Use the note embedder's OpenAI embedding client to get query embedding
            embedding_vector = await asyncio.to_thread(
                self.note_embedder.embedder.get_text_embedding,
                query
            )
            return embedding_vector

        except Exception as e:
            logger.error(f"Failed to get query embedding: {e}")
            return None

    def get_active_embedding_tasks(self) -> List[str]:
        """Get list of currently running embedding tasks"""
        return [key for key, task in self._embedding_tasks.items() if not task.done()]

    async def wait_for_embeddings(self, timeout: float = 30.0) -> None:
        """Wait for all current embedding tasks to complete"""
        if not self._embedding_tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._embedding_tasks.values(),
                               return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Embedding tasks timed out after {timeout}s")

        # Clean up completed tasks
        self._embedding_tasks.clear()


# Global embedding manager instance
embedding_manager = EmbeddingManager()
