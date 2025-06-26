"""
ConversationEmbedder - Independent conversation embedding functionality.

COMPLETELY INDEPENDENT MODULE - No external dependencies.
All database operations, text processing, and OpenAI client are self-contained.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from ..postgres.embedding_operations import EmbeddingDBOperations
from .embedding_provider_selector import EmbeddingProviderSelector
from .text_processing import ConversationProcessor

logger = logging.getLogger(__name__)


class ConversationEmbedder:
    """Handles embedding creation and management for conversations"""

    def __init__(self):
        self.embedder = EmbeddingProviderSelector().get_embedding_client()
        self.conversation_processor = ConversationProcessor()
        self.db = EmbeddingDBOperations()
        logger.info("ConversationEmbedder initialized with independent modules")

    async def get_all_conversations(self) -> List[int]:
        """Get all conversation IDs in the system"""
        return await asyncio.to_thread(self.db.get_all_conversations)

    async def get_user_conversations(self, user_id: int) -> List[int]:
        """Get all conversation IDs for a specific user"""
        return await asyncio.to_thread(self.db.get_user_conversations, user_id)

    async def get_conversations_without_embeddings(self, conversation_ids: List[int]) -> List[int]:
        """Get conversations that don't have embeddings yet"""
        if not conversation_ids:
            return []
        return await asyncio.to_thread(self.db.get_conversations_without_embeddings, conversation_ids)

    async def create_conversation_embedding(self, conversation_id: int) -> bool:
        """
        Create embeddings for a conversation using message pairing rules.

        Args:
            conversation_id: ID of the conversation to embed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get messages for this conversation
            messages = await asyncio.to_thread(
                self.db.get_conversation_messages, conversation_id
            )

            if not messages:
                logger.warning(
                    f"No messages found for conversation {conversation_id}")
                # Mark conversation to skip embedding since it has no messages
                await asyncio.to_thread(
                    self.db.mark_conversation_skip_embedding, conversation_id
                )
                return True  # Return True since we handled the case appropriately

            # Convert to expected format
            message_list = []
            for msg_id, role, content, created_at in messages:
                message_list.append({
                    'id': msg_id,
                    'role': role,
                    'content': content,
                    'created_at': created_at
                })

            # Chunk the conversation using our independent processor
            chunks = self.conversation_processor.chunk_conversation_messages(
                message_list)

            if not chunks:
                logger.warning(
                    f"No chunks created for conversation {conversation_id}")
                return False

            # Create embeddings for all chunks
            chunk_texts = [chunk['text'] for chunk in chunks]
            embeddings = await asyncio.to_thread(
                self.embedder.get_embeddings_with_retry,
                chunk_texts,
                max_retries=3,
                batch_size=50
            )

            # Prepare embeddings data
            embeddings_data = []
            for embedding, chunk in zip(embeddings, chunks):
                embeddings_data.append((
                    embedding,
                    chunk['text'],
                    chunk['source'],
                    chunk['metadata']
                ))

            # Save to database
            await asyncio.to_thread(
                self.db.save_conversation_embeddings, conversation_id, embeddings_data
            )

            logger.info(
                f"Successfully embedded conversation {conversation_id} with {len(embeddings_data)} chunks")
            return True

        except Exception as e:
            logger.error(
                f"Failed to create embedding for conversation {conversation_id}: {e}")
            return False

    async def bulk_embed_conversations(
        self,
        conversation_ids: List[int],
        batch_size: int = 10,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Bulk embed multiple conversations with progress tracking.

        Args:
            conversation_ids: List of conversation IDs to embed
            batch_size: Number of conversations to process in parallel
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with embedding results
        """
        if not conversation_ids:
            return {"embedded_count": 0, "failed_conversations": [], "total_conversations": 0}

        embedded_count = 0
        failed_conversations = []

        # Process in batches to limit concurrent API calls
        for i in range(0, len(conversation_ids), batch_size):
            batch = conversation_ids[i:i + batch_size]

            # Create tasks for this batch
            tasks = [self.create_conversation_embedding(
                conv_id) for conv_id in batch]

            # Wait for batch completion
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for conv_id, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Exception embedding conversation {conv_id}: {result}")
                    failed_conversations.append(
                        {"id": conv_id, "error": str(result)})
                elif result:
                    embedded_count += 1
                else:
                    failed_conversations.append(
                        {"id": conv_id, "error": "Unknown embedding failure"})

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(
                        embedded_count + len(failed_conversations), len(conversation_ids))

            # Small delay between batches
            if i + batch_size < len(conversation_ids):
                await asyncio.sleep(2)

        return {
            "embedded_count": embedded_count,
            "failed_conversations": failed_conversations,
            "total_conversations": len(conversation_ids)
        }

    def has_embedding(self, conversation_id: int) -> bool:
        """Check if a conversation has embeddings (synchronous version)"""
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) FROM embedding_v1 WHERE type_id = %s AND type = 'conversation'",
                (conversation_id,),
                fetch_type='scalar'
            )
            return result > 0
        except Exception as e:
            logger.error(
                f"Error checking embeddings for conversation {conversation_id}: {e}")
            return False

    async def has_embedding_async(self, conversation_id: int) -> bool:
        """Check if a conversation has embeddings (async version)"""
        return await asyncio.to_thread(self.has_embedding, conversation_id)
