"""
File Attachment Manager for Modular Chat System

This module handles URL-based file attachments with embedding search following
the new modular architecture. It provides:

1. URL → chunk matching and retrieval  
2. Vector similarity search within URL chunks
3. Async embedding creation for missing attachments
4. Independent operation from RAG processor

Key Design:
- URL-based chunk retrieval (not generic document processing)
- Direct embedding_v1 table queries with url field  
- Relevance search within specific URL's chunks
- Background embedding creation for missing URLs
"""

# Local imports - using internal operations only
from chat.postgres.url_embedding_operations import url_embedding_ops
from chat.embedding.embedding_manager import embedding_manager
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AttachmentChunk:
    """Represents a chunk from a file attachment"""
    chunk_text: str
    url: str
    section_id: str
    similarity: float
    metadata: Dict[str, Any]
    source: str = "file_attachment"


@dataclass
class AttachmentContext:
    """Container for all attachment-related context"""
    chunks: List[AttachmentChunk]
    total_chunks: int
    urls_processed: List[str]
    urls_missing_embeddings: List[str]
    query_used: str


class FileAttachmentManager:
    """
    Manages file attachments following new modular architecture

    Key Features:
    - URL → chunk matching and retrieval
    - Vector similarity search within URL chunks  
    - Async embedding creation for missing URLs
    - Independent from RAG processor
    """

    def __init__(self):
        self.max_chunks_per_url = 8  # Limit chunks per URL
        self.similarity_threshold = 0.7  # Minimum similarity score
        logger.info("FileAttachmentManager initialized")

    async def process_attachments(
        self,
        attachments: List[Dict[str, Any]],
        query: str,
        user_id: int,
        top_k: int = 8
    ) -> AttachmentContext:
        """
        Process file attachments following updated Phase 5 of modular architecture:

        1. Extract URLs from attachments
        2. Check/create embeddings for missing URLs SYNCHRONOUSLY (wait for completion)
        3. Retrieve chunks for each URL (including newly embedded ones)
        4. Perform relevance search within each URL's chunks
        5. Return combined context

        CRITICAL: If user provides file attachments, they expect them in the response!
        We must embed missing URLs synchronously and wait for completion.

        Args:
            attachments: List of attachment dicts with 'url' field
            query: Search query for relevance matching
            user_id: User ID for ownership tracking
            top_k: Maximum chunks to return per URL

        Returns:
            AttachmentContext with relevant chunks including newly embedded URLs
        """
        if not attachments:
            logger.info("No attachments provided")
            return AttachmentContext(
                chunks=[],
                total_chunks=0,
                urls_processed=[],
                urls_missing_embeddings=[],  # No URLs to embed
                query_used=query
            )

        logger.info(f"🔗 Processing {len(attachments)} file attachments")

        # Phase 5.1: Extract URLs
        urls = self._extract_urls_from_attachments(attachments)

        if not urls:
            logger.warning("No valid URLs found in attachments")
            return AttachmentContext(
                chunks=[],
                total_chunks=0,
                urls_processed=[],
                urls_missing_embeddings=[],  # No URLs to embed
                query_used=query
            )

        logger.info(f"📎 Found URLs: {urls}")

        # Phase 5.2: Check and ensure embeddings exist SYNCHRONOUSLY
        # CRITICAL: If user provides attachments, they expect them in the response!
        newly_embedded_urls = await self._ensure_url_embeddings_exist(urls, user_id)

        if newly_embedded_urls:
            logger.info(
                f"🎯 SYNC EMBEDDING: Successfully embedded {len(newly_embedded_urls)} URLs for current request")

        # Phase 5.3: Process each URL independently (including newly embedded ones)
        all_chunks = []
        urls_processed = []

        # Use asyncio.gather to process URLs in parallel
        url_tasks = [
            self._process_single_url(url, query, user_id, top_k)
            for url in urls
        ]

        url_results = await asyncio.gather(*url_tasks, return_exceptions=True)

        for i, result in enumerate(url_results):
            url = urls[i]

            if isinstance(result, Exception):
                logger.error(f"❌ Failed to process URL {url}: {result}")
                continue

            url_chunks = result
            if url_chunks:
                all_chunks.extend(url_chunks)
                urls_processed.append(url)
                logger.info(f"✅ URL {url}: {len(url_chunks)} relevant chunks")
            else:
                logger.info(f"⚠️ URL {url}: No relevant chunks found")

        logger.info(
            f"🎯 File attachment processing complete: {len(all_chunks)} total chunks from {len(urls_processed)} URLs")

        return AttachmentContext(
            chunks=all_chunks,
            total_chunks=len(all_chunks),
            urls_processed=urls_processed,
            # URLs that were newly embedded for this request
            urls_missing_embeddings=newly_embedded_urls,
            query_used=query
        )

    def _extract_urls_from_attachments(self, attachments: List[Dict[str, Any]]) -> List[str]:
        """Extract valid URLs from attachment objects"""
        urls = []

        for attachment in attachments:
            url = attachment.get('url')
            if url and isinstance(url, str) and url.startswith(('http://', 'https://')):
                urls.append(url)
            else:
                logger.warning(
                    f"Invalid or missing URL in attachment: {attachment}")

        # Remove duplicates while preserving order
        return list(dict.fromkeys(urls))

    async def _ensure_url_embeddings_exist(self, urls: List[str], user_id: int) -> List[str]:
        """
        Check which URLs are missing embeddings and create them SYNCHRONOUSLY

        This is critical: If user provides file attachments, they expect them in the response!
        We must embed missing URLs and wait for completion before proceeding.

        Returns:
            List of URLs that were missing embeddings (now created and available)
        """
        missing_urls = []

        # First pass: identify missing URLs
        for url in urls:
            exists = url_embedding_ops.check_user_url_embeddings_exist(
                url, user_id)
            if not exists:
                missing_urls.append(url)

        if missing_urls:
            logger.info(
                f"🔄 SYNC EMBEDDING: {len(missing_urls)} URLs missing embeddings - creating now...")

            # Create embeddings synchronously using gather for parallel processing
            embedding_tasks = [
                self._create_url_embedding_sync(url, user_id)
                for url in missing_urls
            ]

            # Wait for all embeddings to complete
            results = await asyncio.gather(*embedding_tasks, return_exceptions=True)

            # Check results
            successfully_embedded = []
            for i, result in enumerate(results):
                url = missing_urls[i]
                if isinstance(result, Exception):
                    logger.error(
                        f"❌ Failed to embed URL {url[:50]}...: {result}")
                elif result:
                    successfully_embedded.append(url)
                    logger.info(f"✅ Successfully embedded URL: {url[:50]}...")
                else:
                    logger.error(f"❌ Embedding failed for URL: {url[:50]}...")

            logger.info(
                f"🎯 SYNC EMBEDDING COMPLETE: {len(successfully_embedded)}/{len(missing_urls)} URLs embedded successfully")

            return successfully_embedded
        else:
            logger.info("✅ All attachment URLs already have embeddings")
            return []

    async def _create_url_embedding_sync(self, url: str, user_id: int) -> bool:
        """Create URL embedding synchronously and wait for completion"""
        try:
            logger.info(f"🔄 Creating embedding for URL: {url[:50]}...")
            success = await url_embedding_ops.create_user_url_embeddings(url, user_id)

            if success:
                logger.info(
                    f"✅ Successfully created embedding for URL: {url[:50]}...")
                return True
            else:
                logger.error(
                    f"❌ Failed to create embedding for URL: {url[:50]}...")
                return False

        except Exception as e:
            logger.error(
                f"❌ Sync embedding creation failed for {url[:50]}...: {e}")
            return False

    async def _process_single_url(
        self,
        url: str,
        query: str,
        user_id: int,
        top_k: int
    ) -> List[AttachmentChunk]:
        """
        Process a single URL attachment:
        1. Get all chunks for this URL
        2. Perform relevance search within URL chunks
        3. Return top-K most relevant chunks
        """
        try:
            # Get all chunks for this URL
            url_embeddings = url_embedding_ops.get_user_url_embeddings(
                url, user_id)

            if not url_embeddings:
                logger.warning(f"No embeddings found for URL: {url}")
                return []

            logger.info(
                f"🔍 Found {len(url_embeddings)} chunks for URL: {url[:50]}...")

            # Perform similarity search within this URL's chunks
            relevant_chunks = await self._search_within_url_chunks(
                query, url_embeddings, top_k
            )

            # Convert to AttachmentChunk objects
            attachment_chunks = []
            for chunk_data, similarity in relevant_chunks:
                attachment_chunk = AttachmentChunk(
                    chunk_text=chunk_data['chunk_text'],
                    url=url,
                    section_id=chunk_data.get('section_id', ''),
                    similarity=similarity,
                    metadata={
                        'url': url,
                        'source': chunk_data.get('source', 'file_attachment'),
                        'section_id': chunk_data.get('section_id'),
                        'original_metadata': chunk_data.get('metadata', {})
                    }
                )
                attachment_chunks.append(attachment_chunk)

            return attachment_chunks

        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            return []

    async def _search_within_url_chunks(
        self,
        query: str,
        url_chunks: List[Dict[str, Any]],
        top_k: int
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform similarity search within a specific URL's chunks

        Args:
            query: Search query
            url_chunks: All chunks from a specific URL
            top_k: Number of top chunks to return

        Returns:
            List of (chunk_data, similarity_score) tuples
        """
        try:
            # Get query embedding using the embedding manager
            query_embedding = await embedding_manager.get_query_embedding(query)

            if not query_embedding:
                logger.error("Failed to get query embedding")
                return []

            # Calculate similarity for each chunk
            scored_chunks = []
            for chunk in url_chunks:
                chunk_embedding = chunk.get('embedding')
                if not chunk_embedding:
                    continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(
                    query_embedding, chunk_embedding)

                # Only include chunks above similarity threshold
                if similarity >= self.similarity_threshold:
                    scored_chunks.append((chunk, similarity))

            # Sort by similarity (highest first) and return top-K
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            return scored_chunks[:top_k]

        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Calculate cosine similarity without numpy dependency
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            return dot_product / (magnitude1 * magnitude2)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def chunks_to_context_text(self, chunks: List[AttachmentChunk], max_length: int = 4000) -> str:
        """
        Convert attachment chunks to context text for LLM

        Args:
            chunks: List of attachment chunks
            max_length: Maximum character length for context

        Returns:
            Formatted context text
        """
        if not chunks:
            return ""

        context_parts = []
        current_length = 0

        for i, chunk in enumerate(chunks):
            # Format chunk with source information
            chunk_text = f"[FILE ATTACHMENT - {chunk.url}]\n{chunk.chunk_text}\n"

            if current_length + len(chunk_text) > max_length:
                logger.info(
                    f"Context truncated at {current_length} chars ({i} chunks)")
                break

            context_parts.append(chunk_text)
            current_length += len(chunk_text)

        return "\n".join(context_parts)

    def get_status(self) -> Dict[str, Any]:
        """Get file attachment manager status"""
        return {
            "max_chunks_per_url": self.max_chunks_per_url,
            "similarity_threshold": self.similarity_threshold,
            "status": "operational"
        }


# Global instance
file_attachment_manager = FileAttachmentManager()
