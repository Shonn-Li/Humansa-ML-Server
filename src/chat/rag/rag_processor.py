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
        Master ID resolution with corrected scoped search logic:

        CORRECTED LOGIC:
        1. If ONLY user_id provided (no other IDs) → Full context search (all notes + all conversations)
        2. If ANY specific IDs provided → ONLY search within those specific IDs, ignore others
        3. No cross-contamination → Don't auto-include conversations when note_ids specified

        Examples:
        - user_id=3 only → All user's notes + all user's conversations
        - note_ids=[1,2] → Only notes 1,2 + NO conversations (unless conversation_ids explicitly provided)
        - folder_ids=[5] → Only notes from folder 5 + NO conversations (unless conversation_ids explicitly provided)
        - conversation_ids=[10,11] → NO notes + only conversations 10,11
        - note_ids=[1] + conversation_ids=[10] → Only note 1 + only conversation 10
        """
        logger.info(f"=== ID RESOLUTION WITH CORRECTED SCOPED SEARCH ===")
        logger.info(f"User: {user_id}")
        logger.info(f"Note IDs: {note_ids}")
        logger.info(f"Folder IDs: {folder_ids}")
        logger.info(f"Conversation IDs: {conversation_ids}")

        # Check if any specific IDs are provided
        has_specific_ids = note_ids is not None or folder_ids is not None or conversation_ids is not None

        if has_specific_ids:
            # SCOPED SEARCH: Only search within specified IDs
            logger.info("🎯 SCOPED SEARCH: Using only specified IDs")

            # Resolve notes only if note_ids or folder_ids provided
            if note_ids is not None or folder_ids is not None:
                resolved_notes = self.postgres.resolve_note_ids(
                    user_id, note_ids, folder_ids)
            else:
                resolved_notes = []  # No notes if not specified

            # Resolve conversations only if conversation_ids explicitly provided
            if conversation_ids is not None:
                resolved_conversations = self.postgres.resolve_conversation_ids(
                    user_id, conversation_ids)
            else:
                resolved_conversations = []  # No conversations if not specified
        else:
            # FULL CONTEXT SEARCH: Get all user content
            logger.info("🌐 FULL CONTEXT SEARCH: Getting all user content")
            resolved_notes = self.postgres.resolve_note_ids(
                user_id, None, None)  # All notes
            resolved_conversations = self.postgres.resolve_conversation_ids(
                user_id, None)  # All conversations

        resolved = ResolvedIDs(
            notes=resolved_notes,
            conversations=resolved_conversations
        )

        logger.info(f"=== RESOLVED WITH CORRECTED LOGIC ===")
        logger.info(f"Notes: {len(resolved.notes)}")
        logger.info(f"Conversations: {len(resolved.conversations)}")
        logger.info(
            f"Search type: {'SCOPED' if has_specific_ids else 'FULL CONTEXT'}")
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
                               top_k: int = 20, search_type: str = "mixed") -> List[ChunkResult]:
        """
        Vector search across notes and conversations with type-specific routing
        Supports "notes", "conversations", or "mixed" search types
        """
        if not query.strip():
            logger.warning("Empty query provided to RAG search")
            return []

        if not resolved_ids.notes and not resolved_ids.conversations:
            logger.warning("No IDs provided for RAG search")
            return []

        logger.info(f"=== RAG SEARCH ({search_type.upper()}) ===")
        logger.info(f"Query: {query[:100]}...")
        logger.info(
            f"Searching {len(resolved_ids.notes)} notes, {len(resolved_ids.conversations)} conversations")

        # Generate query embedding
        try:
            query_embedding = self.embedder.get_text_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        # Perform search based on search_type
        if search_type == "notes":
            chunks = self.postgres.notes_only_vector_search(
                query_embedding, resolved_ids, top_k)
        elif search_type == "conversations":
            chunks = self.postgres.conversations_only_vector_search(
                query_embedding, resolved_ids, top_k)
        else:  # search_type == "mixed" (default)
            chunks = self.postgres.mixed_vector_search(
                query_embedding, resolved_ids, top_k)

        logger.info(
            f"Found {len(chunks)} relevant chunks using {search_type} search")
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
                                  top_k: int = 20,
                                  custom_query: Optional[str] = None,
                                  search_type: str = "mixed") -> RAGContext:
        """
        Main RAG processing pipeline with optimized parallel processing:
        1. Extract query from messages (or use custom_query if provided)
        2. PARALLEL: Generate query embedding + Resolve all IDs 
        3. Check embeddings for resolved IDs AFTER resolution
        4. Perform unified search with embedded query
        5. Return context

        Args:
            custom_query: If provided, use this query instead of extracting from messages.
                         This enables using condensed/transformed queries for better RAG results.
        """
        logger.info("=== STARTING RAG REQUEST ===")

        # Step 1: Extract query (or use custom query)
        if custom_query:
            query = custom_query
            logger.info(f"Using custom query for RAG: {query[:100]}...")
        else:
            query = self.searcher.extract_query_from_messages(messages)
            logger.info(f"Extracted query from messages: {query[:100]}...")

        if not query:
            logger.warning("No query available for RAG processing")
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

        # Determine if this is a targeted search based on original parameters
        is_targeted_search = (note_ids is not None or
                              folder_ids is not None or
                              conversation_ids is not None)

        await self._check_and_ensure_embeddings(resolved_ids, is_targeted_search)

        # Step 4: Search with embedded query using router-determined search type
        logger.info(f"=== {search_type.upper()} SEARCH ===")
        chunks = await self._search_with_embedding_async(query_embedding, resolved_ids, top_k, search_type)

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

    async def _check_and_ensure_embeddings(self, resolved_ids: ResolvedIDs, is_targeted_search: bool):
        """
        🎯 KEY EMBEDDING CHECK: Check embeddings for resolved IDs and ensure they exist

        UPDATED LOGIC:
        - If specific IDs were requested (targeted search), WAIT for embeddings to be created
        - If full context search (no specific IDs), use background embedding (don't wait)
        - This ensures specifically requested content is always searchable

        Args:
            resolved_ids: The resolved note and conversation IDs
            is_targeted_search: True if specific IDs were provided, False for full context search
        """
        logger.info("🔍 CHECKING EMBEDDINGS FOR RESOLVED IDs...")

        if is_targeted_search:
            logger.info(
                "🎯 TARGETED SEARCH: Ensuring embeddings exist for specific IDs (will wait if needed)")
        else:
            logger.info(
                "🌐 FULL CONTEXT SEARCH: Using background embedding for missing embeddings")

        # Check notes
        missing_note_ids = []
        if resolved_ids.notes:
            note_ids = resolved_ids.notes  # notes is already a List[int]
            missing_note_ids = await self._check_missing_embeddings_async('note', note_ids)

            if missing_note_ids:
                if is_targeted_search:
                    logger.warning(
                        f"⚠️  Missing embeddings for {len(missing_note_ids)} specifically requested notes: {missing_note_ids}")
                    logger.info(
                        "⏳ WAITING for embeddings to be created (targeted search)...")
                    # WAIT for embeddings to be created for targeted search
                    await self._create_embeddings_sync_async('note', missing_note_ids)
                    logger.info("✅ Embeddings created for targeted notes")
                else:
                    logger.warning(
                        f"⚠️  Missing embeddings for {len(missing_note_ids)} notes: {missing_note_ids}")
                    # Trigger background embedding (don't wait) for full context search
                    asyncio.create_task(
                        self._trigger_background_embedding_async('note', missing_note_ids))
                    logger.info("🚀 Background embedding triggered for notes")
            else:
                logger.info(f"✅ All {len(note_ids)} notes have embeddings")

        # Check conversations
        missing_conversation_ids = []
        if resolved_ids.conversations:
            # conversations is already a List[int]
            conversation_ids = resolved_ids.conversations
            missing_conversation_ids = await self._check_missing_embeddings_async('conversation', conversation_ids)

            if missing_conversation_ids:
                if is_targeted_search:
                    logger.warning(
                        f"⚠️  Missing embeddings for {len(missing_conversation_ids)} specifically requested conversations: {missing_conversation_ids}")
                    logger.info(
                        "⏳ WAITING for embeddings to be created (targeted search)...")
                    # WAIT for embeddings to be created for targeted search
                    await self._create_embeddings_sync_async('conversation', missing_conversation_ids)
                    logger.info(
                        "✅ Embeddings created for targeted conversations")
                else:
                    logger.warning(
                        f"⚠️  Missing embeddings for {len(missing_conversation_ids)} conversations: {missing_conversation_ids}")
                    # Trigger background embedding (don't wait) for full context search
                    asyncio.create_task(self._trigger_background_embedding_async(
                        'conversation', missing_conversation_ids))
                    logger.info(
                        "🚀 Background embedding triggered for conversations")
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
                                           top_k: int, search_type: str = "mixed") -> List[ChunkResult]:
        """Async wrapper for vector search with search type support"""
        loop = asyncio.get_event_loop()

        # Choose the right search method based on search_type
        if search_type == "notes":
            search_func = self.postgres.notes_only_vector_search
        elif search_type == "conversations":
            search_func = self.postgres.conversations_only_vector_search
        else:  # search_type == "mixed" (default)
            search_func = self.postgres.mixed_vector_search

        chunks = await loop.run_in_executor(
            None,
            search_func,
            query_embedding, resolved_ids, top_k
        )
        logger.info(
            f"Found {len(chunks)} relevant chunks using {search_type} search")
        return chunks

    async def _create_embeddings_sync_async(self, type_name: str, ids: List[int]):
        """
        Create embeddings synchronously and WAIT for completion
        Used for targeted searches where we need embeddings before searching
        """
        if not ids:
            return

        logger.info(
            f"⏳ Creating embeddings SYNCHRONOUSLY for {len(ids)} {type_name}s (targeted search)...")

        # Import embedding manager here to avoid circular imports
        from ..embedding.embedding_manager import embedding_manager

        # Create embeddings and WAIT for completion
        if type_name == 'note':
            await embedding_manager.embed_notes_async(ids)
            logger.info(f"✅ Note embeddings created for IDs: {ids}")
        elif type_name == 'conversation':
            await embedding_manager.embed_conversations_async(ids)
            logger.info(f"✅ Conversation embeddings created for IDs: {ids}")

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
            # Extract title from metadata
            title = chunk.metadata.get("title") if chunk.metadata else None

            # Create source identifier with title if available
            if chunk.type == "note":
                if title:
                    source_id = f"Note '{title}'"
                else:
                    source_id = f"Note {chunk.type_id}"
            else:  # conversation
                if title:
                    source_id = f"Conversation '{title}'"
                else:
                    source_id = f"Conversation {chunk.type_id}"

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

        # Log the actual context content for debugging
        logger.info("🔍 === RAG CONTEXT CONTENT ===")
        logger.info(
            f"Context preview (first 500 chars):\n{context_text[:500]}{'...' if len(context_text) > 500 else ''}")
        if len(context_parts) > 0:
            logger.info(f"📄 Individual chunks summary:")
            for i, part in enumerate(context_parts[:3]):  # Show first 3 chunks
                logger.info(
                    f"  Chunk {i+1}: {part[:100]}{'...' if len(part) > 100 else ''}")
            if len(context_parts) > 3:
                logger.info(f"  ... and {len(context_parts) - 3} more chunks")
        logger.info("=== END RAG CONTEXT CONTENT ===")

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
