"""
RAG Module - Clean Retrieval-Augmented Generation

This module handles:
- ID resolution and aggregation
- Parallel query embedding and ID resolution
- Embedding checks AFTER ID resolution
- Unified embedding search across notes and conversations  
- Context assembly from multiple sources
"""

import asyncio
import logging
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Import our new independent modules
from ..postgres.db_manager import PostgresManager, ResolvedIDs, ChunkResult
from ..postgres.embedding_operations import EmbeddingDBOperations
from ..embedding.embedding_provider_selector import EmbeddingProviderSelector

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Container for RAG context results"""
    chunks: List[ChunkResult]
    used_note_ids: List[int]
    used_conversation_ids: List[int]
    total_chunks: int
    query_used: str


class IDResolver:
    """Clean ID resolution and aggregation"""

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres = postgres_manager
        logger.info("IDResolver initialized")

    def resolve_all_ids(self, user_id: int, note_ids: Optional[List[int]] = None,
                        folder_ids: Optional[List[int]] = None,
                        conversation_ids: Optional[List[int]] = None) -> ResolvedIDs:
        """
        Master ID resolution with clear priority logic:

        Notes:
        1. If note_ids provided: use them (validate ownership)
        2. If folder_ids provided: get notes from folders  
        3. If neither: get all user notes

        Conversations:
        1. If conversation_ids is None: get all user conversations with embeddings
        2. If conversation_ids provided: use them (could be empty list)
        """
        logger.info(f"=== ID RESOLUTION ===")
        logger.info(f"User: {user_id}")
        logger.info(f"Note IDs: {note_ids}")
        logger.info(f"Folder IDs: {folder_ids}")
        logger.info(f"Conversation IDs: {conversation_ids}")

        resolved_notes = self.postgres.resolve_note_ids(
            user_id, note_ids, folder_ids)
        resolved_conversations = self.postgres.resolve_conversation_ids(
            user_id, conversation_ids)

        resolved = ResolvedIDs(
            notes=resolved_notes,
            conversations=resolved_conversations
        )

        logger.info(f"=== RESOLVED ===")
        logger.info(f"Notes: {len(resolved.notes)}")
        logger.info(f"Conversations: {len(resolved.conversations)}")
        logger.info(f"==================")

        return resolved


class UnifiedRAGSearcher:
    """Unified RAG search using single mixed embedding query"""

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres = postgres_manager
        self.embedder = EmbeddingProviderSelector().get_embedding_client()
        self.embedding_ops = EmbeddingDBOperations()  # No arguments needed
        logger.info("UnifiedRAGSearcher initialized")

    def search_relevant_chunks(self, query: str, resolved_ids: ResolvedIDs,
                               top_k: int = 20) -> List[ChunkResult]:
        """
        Single mixed vector search across notes and conversations
        Uses unified embedding_v1 table query
        """
        if not query.strip():
            logger.warning("Empty query provided to RAG search")
            return []

        if not resolved_ids.notes and not resolved_ids.conversations:
            logger.warning("No IDs provided for RAG search")
            return []

        logger.info(f"=== RAG SEARCH ===")
        logger.info(f"Query: {query[:100]}...")
        logger.info(
            f"Searching {len(resolved_ids.notes)} notes, {len(resolved_ids.conversations)} conversations")

        # Generate query embedding
        try:
            query_embedding = self.embedder.get_text_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        # Perform unified vector search
        chunks = self.postgres.mixed_vector_search(
            query_embedding, resolved_ids, top_k)

        logger.info(f"Found {len(chunks)} relevant chunks")
        for i, chunk in enumerate(chunks[:5]):  # Log top 5
            logger.info(
                f"  {i+1}. {chunk.type}:{chunk.type_id} (sim: {chunk.similarity:.3f})")

        return chunks

    def extract_query_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Extract search query from chat messages"""
        if not messages:
            return ""

        # Get all user messages
        user_messages = []
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_messages.append(content)

        # Combine user messages
        if user_messages:
            query = " ".join(user_messages)
            logger.info(
                f"Extracted query from {len(user_messages)} user messages: {query[:100]}...")
            return query

        # Fallback: use last message content
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            content = last_msg.get("content", "")
            if isinstance(content, str):
                return content

        return ""


class RAGProcessor:
    """Main RAG processing orchestrator"""

    def __init__(self):
        self.postgres = PostgresManager()
        self.id_resolver = IDResolver(self.postgres)
        self.searcher = UnifiedRAGSearcher(self.postgres)
        logger.info("RAGProcessor initialized")

    async def process_rag_request(self, messages: List[Dict[str, Any]], user_id: int,
                                  note_ids: Optional[List[int]] = None,
                                  folder_ids: Optional[List[int]] = None,
                                  conversation_ids: Optional[List[int]] = None,
                                  top_k: int = 20) -> RAGContext:
        """
        Main RAG processing pipeline with optimized parallel processing:
        1. Extract query from messages
        2. PARALLEL: Generate query embedding + Resolve all IDs 
        3. Check embeddings for resolved IDs AFTER resolution
        4. Perform unified search with embedded query
        5. Return context
        """
        logger.info("=== STARTING RAG REQUEST ===")

        # Step 1: Extract query
        query = self.searcher.extract_query_from_messages(messages)
        if not query:
            logger.warning("No query extracted from messages")
            return RAGContext(
                chunks=[],
                used_note_ids=[],
                used_conversation_ids=[],
                total_chunks=0,
                query_used=""
            )

        # Step 2: PARALLEL PROCESSING - Query embedding + ID resolution
        logger.info("=== PARALLEL: QUERY EMBEDDING + ID RESOLUTION ===")

        # Run query embedding and ID resolution in parallel
        query_embedding_task = asyncio.create_task(
            self._embed_query_async(query))
        id_resolution_task = asyncio.create_task(self._resolve_ids_async(
            user_id, note_ids, folder_ids, conversation_ids
        ))

        # Wait for both to complete
        query_embedding, resolved_ids = await asyncio.gather(
            query_embedding_task,
            id_resolution_task
        )

        if query_embedding is None:
            logger.error("Failed to generate query embedding")
            return RAGContext(
                chunks=[],
                used_note_ids=[],
                used_conversation_ids=[],
                total_chunks=0,
                query_used=query
            )

        # Step 3: EMBEDDING CHECKS - Check embeddings for resolved IDs
        logger.info("=== EMBEDDING CHECKS (AFTER ID RESOLUTION) ===")
        await self._check_and_ensure_embeddings(resolved_ids)

        # Step 4: Search with embedded query
        logger.info("=== UNIFIED SEARCH ===")
        chunks = await self._search_with_embedding_async(query_embedding, resolved_ids, top_k)

        # Step 5: Extract used IDs
        used_note_ids = list(
            set(chunk.type_id for chunk in chunks if chunk.type == 'note'))
        used_conversation_ids = list(
            set(chunk.type_id for chunk in chunks if chunk.type == 'conversation'))

        context = RAGContext(
            chunks=chunks,
            used_note_ids=used_note_ids,
            used_conversation_ids=used_conversation_ids,
            total_chunks=len(chunks),
            query_used=query
        )

        logger.info(f"=== RAG CONTEXT SUMMARY ===")
        logger.info(f"Query: {query[:50]}...")
        logger.info(f"Total chunks: {len(chunks)}")
        logger.info(f"Used notes: {len(used_note_ids)}")
        logger.info(f"Used conversations: {len(used_conversation_ids)}")
        logger.info(f"===========================")

        return context

    async def _embed_query_async(self, query: str) -> Optional[List[float]]:
        """Async wrapper for query embedding"""
        try:
            logger.info(f"🔄 Embedding query: {query[:100]}...")
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self.searcher.embedder.get_text_embedding,
                query
            )
            logger.info("✅ Query embedding completed")
            return embedding
        except Exception as e:
            logger.error(f"❌ Query embedding failed: {e}")
            return None

    async def _resolve_ids_async(self, user_id: int, note_ids: Optional[List[int]],
                                 folder_ids: Optional[List[int]],
                                 conversation_ids: Optional[List[int]]) -> ResolvedIDs:
        """Async wrapper for ID resolution"""
        logger.info(f"🔄 Resolving IDs for user {user_id}...")
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        resolved_ids = await loop.run_in_executor(
            None,
            self.id_resolver.resolve_all_ids,
            user_id, note_ids, folder_ids, conversation_ids
        )
        logger.info(
            f"✅ ID resolution completed: {len(resolved_ids.notes)} notes, {len(resolved_ids.conversations)} conversations")
        return resolved_ids

    async def _check_and_ensure_embeddings(self, resolved_ids: ResolvedIDs):
        """
        🎯 KEY EMBEDDING CHECK: Check embeddings for resolved IDs and trigger background embedding
        This is where we check if the resolved notes/conversations have embeddings!
        """
        logger.info("🔍 CHECKING EMBEDDINGS FOR RESOLVED IDs...")

        # Check notes
        missing_note_ids = []
        if resolved_ids.notes:
            note_ids = resolved_ids.notes  # notes is already a List[int]
            missing_note_ids = await self._check_missing_embeddings_async('note', note_ids)

            if missing_note_ids:
                logger.warning(
                    f"⚠️  Missing embeddings for {len(missing_note_ids)} notes: {missing_note_ids}")
                # Trigger background embedding (don't wait)
                asyncio.create_task(
                    self._trigger_background_embedding_async('note', missing_note_ids))
            else:
                logger.info(f"✅ All {len(note_ids)} notes have embeddings")

        # Check conversations
        missing_conversation_ids = []
        if resolved_ids.conversations:
            # conversations is already a List[int]
            conversation_ids = resolved_ids.conversations
            missing_conversation_ids = await self._check_missing_embeddings_async('conversation', conversation_ids)

            if missing_conversation_ids:
                logger.warning(
                    f"⚠️  Missing embeddings for {len(missing_conversation_ids)} conversations: {missing_conversation_ids}")
                # Trigger background embedding (don't wait)
                asyncio.create_task(self._trigger_background_embedding_async(
                    'conversation', missing_conversation_ids))
            else:
                logger.info(
                    f"✅ All {len(conversation_ids)} conversations have embeddings")

    async def _check_missing_embeddings_async(self, type_name: str, ids: List[int]) -> List[int]:
        """Check which IDs are missing embeddings"""
        if not ids:
            return []

        loop = asyncio.get_event_loop()
        missing_ids = await loop.run_in_executor(
            None,
            self.searcher.embedding_ops.get_missing_embedding_ids,
            type_name, ids
        )
        return missing_ids

    async def _trigger_background_embedding_async(self, type_name: str, ids: List[int]):
        """Trigger background embedding for missing IDs"""
        if not ids:
            return

        logger.info(
            f"🚀 Triggering background embedding for {len(ids)} {type_name}s...")

        # Import embedding manager here to avoid circular imports
        from ..embedding.embedding_manager import embedding_manager

        # Trigger background embedding (fire and forget)
        if type_name == 'note':
            asyncio.create_task(embedding_manager.embed_notes_async(ids))
        elif type_name == 'conversation':
            asyncio.create_task(
                embedding_manager.embed_conversations_async(ids))

    async def _search_with_embedding_async(self, query_embedding: List[float],
                                           resolved_ids: ResolvedIDs,
                                           top_k: int) -> List[ChunkResult]:
        """Async wrapper for vector search"""
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None,
            self.postgres.mixed_vector_search,
            query_embedding, resolved_ids, top_k
        )
        logger.info(f"Found {len(chunks)} relevant chunks")
        return chunks

    def chunks_to_context_text(self, chunks: List[ChunkResult], max_length: int = 8000) -> str:
        """
        Convert chunks to context text for direct LLM input
        Used for non-citation mode
        """
        if not chunks:
            return ""

        context_parts = []
        total_length = 0

        for chunk in chunks:
            # Create source identifier
            source_type = "Note" if chunk.type == "note" else "Conversation"
            source_id = f"{source_type} {chunk.type_id}"

            # Format chunk with source
            chunk_text = f"[{source_id}] {chunk.chunk_text.strip()}"

            # Check length limit
            if total_length + len(chunk_text) > max_length:
                logger.info(
                    f"Context length limit reached: {total_length} chars")
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        context_text = "\n\n".join(context_parts)
        logger.info(
            f"Generated context text: {len(context_text)} chars from {len(context_parts)} chunks")
        return context_text

    def chunks_to_documents(self, chunks: List[ChunkResult]) -> List[Any]:
        """
        Convert chunks to LlamaIndex Documents for citation mode
        """
        try:
            # Try to import from existing ai_chat_bot module first
            sys.path.append(os.path.join(
                os.path.dirname(__file__), '../../..'))
            from llama_index.core import Document
        except ImportError:
            try:
                from ai_chat_bot.enhanced_chat_bot import Document
            except ImportError:
                # Fallback simple document class
                class Document:
                    def __init__(self, text, metadata=None):
                        self.text = text
                        self.metadata = metadata or {}
                logger.warning(
                    "Using fallback Document class - citation features limited")

        documents = []
        for chunk in chunks:
            doc = Document(
                text=chunk.chunk_text,
                metadata={
                    "source_type": chunk.type,
                    "source_id": chunk.type_id,
                    "section_id": chunk.section_id,
                    "similarity": chunk.similarity
                }
            )
            documents.append(doc)

        logger.info(f"Created {len(documents)} Documents")
        return documents

    def health_check(self) -> bool:
        """Health check for RAG system"""
        return self.postgres.health_check()
