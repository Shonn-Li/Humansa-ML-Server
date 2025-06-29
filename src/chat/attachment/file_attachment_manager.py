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
    chunk_header: str  # "[ATTACHMENT] filename - description" per consultation
    url: str
    section_id: str
    similarity: float
    is_image: bool = False  # NEW: Whether this chunk is from an image file
    metadata: Dict[str, Any] = None
    source: str = "file_attachment"

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AttachmentContext:
    """Container for all attachment-related context"""
    chunks: List[AttachmentChunk]
    # NEW: Separate list for independent image chunks
    image_chunks: List[AttachmentChunk]
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
        self.similarity_threshold = 0.7  # Minimum similarity score for additional chunks
        # Lower threshold for explicit attachments
        self.explicit_attachment_threshold = 0.5
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
                image_chunks=[],  # NEW: Empty image chunks list
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
                image_chunks=[],  # NEW: Empty image chunks list
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

        # NEW: Separate image chunks from text chunks
        image_chunks = [chunk for chunk in all_chunks if chunk.is_image]
        text_chunks = [chunk for chunk in all_chunks if not chunk.is_image]

        logger.info(
            f"📊 Chunk breakdown: {len(image_chunks)} image chunks, {len(text_chunks)} text chunks")

        return AttachmentContext(
            chunks=text_chunks,  # Only text chunks go through similarity search
            image_chunks=image_chunks,  # Image chunks are always included
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
        Process a single URL attachment with special handling for images:
        1. Get all chunks for this URL
        2. Separate image chunks from text chunks
        3. For text chunks: perform relevance search within URL chunks
        4. For image chunks: always include (independent from similarity search)
        5. Return combined chunks with proper priority
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

            # NEW: Separate image chunks from text chunks
            image_chunks_data = []
            text_chunks_data = []

            for chunk_data in url_embeddings:
                if self._is_image_chunk(url, chunk_data):
                    image_chunks_data.append(chunk_data)
                else:
                    text_chunks_data.append(chunk_data)

            logger.info(
                f"📊 URL {url[:50]}... has {len(image_chunks_data)} image chunks, {len(text_chunks_data)} text chunks")

            attachment_chunks = []

            # NEW: Process image chunks - ALWAYS include (no similarity search)
            if image_chunks_data:
                logger.info(
                    f"📸 Processing {len(image_chunks_data)} image chunks - all will be included")

            for chunk_data in image_chunks_data:
                chunk_header = self._create_chunk_header(url, chunk_data)

                attachment_chunk = AttachmentChunk(
                    chunk_text=chunk_data['chunk_text'],
                    chunk_header=chunk_header,
                    url=url,
                    section_id=chunk_data.get('section_id', ''),
                    # Max similarity for images (always relevant)
                    similarity=1.0,
                    is_image=True,  # NEW: Mark as image chunk
                    metadata={
                        'url': url,
                        'source': chunk_data.get('source', 'file_attachment'),
                        'section_id': chunk_data.get('section_id'),
                        'original_metadata': chunk_data.get('metadata', {}),
                        'chunk_type': 'image'
                    }
                )
                attachment_chunks.append(attachment_chunk)
                logger.info(
                    f"✅ Added image chunk: {len(chunk_data['chunk_text'])} chars")

            # Process text chunks - use similarity search with explicit attachment flag
            if text_chunks_data:
                logger.info(
                    f"📄 Processing {len(text_chunks_data)} text chunks with explicit attachment logic")
                relevant_text_chunks = await self._search_within_url_chunks(
                    query, text_chunks_data, top_k, is_explicit_attachment=True
                )

                for chunk_data, similarity in relevant_text_chunks:
                    chunk_header = self._create_chunk_header(url, chunk_data)

                    attachment_chunk = AttachmentChunk(
                        chunk_text=chunk_data['chunk_text'],
                        chunk_header=chunk_header,
                        url=url,
                        section_id=chunk_data.get('section_id', ''),
                        similarity=similarity,
                        is_image=False,  # Mark as text chunk
                        metadata={
                            'url': url,
                            'source': chunk_data.get('source', 'file_attachment'),
                            'section_id': chunk_data.get('section_id'),
                            'original_metadata': chunk_data.get('metadata', {}),
                            'chunk_type': 'text'
                        }
                    )
                    attachment_chunks.append(attachment_chunk)
                    logger.info(
                        f"✅ Added text chunk: {len(chunk_data['chunk_text'])} chars, similarity: {similarity:.3f}")

            return attachment_chunks

        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            return []

    async def _search_within_url_chunks(
        self,
        query: str,
        url_chunks: List[Dict[str, Any]],
        top_k: int,
        is_explicit_attachment: bool = True
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform similarity search within a specific URL's chunks

        Args:
            query: Search query
            url_chunks: All chunks from a specific URL
            top_k: Number of top chunks to return
            is_explicit_attachment: True if user explicitly attached this file

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
            all_scored_chunks = []
            for chunk in url_chunks:
                chunk_embedding = chunk.get('embedding')
                if not chunk_embedding:
                    continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(
                    query_embedding, chunk_embedding)
                all_scored_chunks.append((chunk, similarity))

            # Sort by similarity (highest first)
            all_scored_chunks.sort(key=lambda x: x[1], reverse=True)

            # Apply filtering logic
            scored_chunks = []

            # For explicit attachments, always include at least the top chunk
            if is_explicit_attachment and all_scored_chunks:
                # Always include the highest scoring chunk
                scored_chunks.append(all_scored_chunks[0])
                logger.info(
                    f"📎 Including top chunk for explicit attachment (similarity: {all_scored_chunks[0][1]:.3f})")

                # Add additional chunks that meet the lower threshold for explicit attachments
                threshold = self.explicit_attachment_threshold
                for chunk, similarity in all_scored_chunks[1:]:
                    if similarity >= threshold:
                        scored_chunks.append((chunk, similarity))
                        logger.info(
                            f"📎 Including additional chunk (similarity: {similarity:.3f} >= {threshold})")
                    if len(scored_chunks) >= top_k:
                        break
            else:
                # Standard filtering: only chunks above regular threshold
                threshold = self.similarity_threshold
                for chunk, similarity in all_scored_chunks:
                    if similarity >= threshold:
                        scored_chunks.append((chunk, similarity))
                    if len(scored_chunks) >= top_k:
                        break

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

    def chunks_to_context_text(self, chunks: List[AttachmentChunk], image_chunks: List[AttachmentChunk] = None, max_length: int = 4000) -> str:
        """
        Convert attachment chunks to context text for LLM with PRIORITY ORDERING

        CRITICAL: File attachments have priority and images are independent from similarity search

        Per consultation guidance:
        [ATTACHMENT] filename - description (IMAGE - always included)
        <image content extracted via OCR/Vision>

        [ATTACHMENT] filename - description (TEXT - similarity filtered)  
        <first 300-500 tokens of chunk_text>

        Args:
            chunks: List of text attachment chunks (similarity filtered)
            image_chunks: List of image attachment chunks (always included)
            max_length: Maximum character length for context

        Returns:
            Formatted context text with headers and chunk content, images first (NO PREFIX)
        """
        if not chunks and not image_chunks:
            return ""

        context_parts = []  # NO "FILE ATTACHMENTS:" prefix - handled by caller
        current_length = 0

        # PRIORITY 1: Image chunks ALWAYS come first (independent from similarity)
        if image_chunks:
            logger.info(
                f"📸 Adding {len(image_chunks)} image chunks (always included)")
            for chunk in image_chunks:
                chunk_text = f"{chunk.chunk_header}\n{chunk.chunk_text[:500]}{'...' if len(chunk.chunk_text) > 500 else ''}\n"

                if current_length + len(chunk_text) > max_length:
                    logger.info(
                        f"📎 Context truncated at {current_length} chars (image chunks)")
                    break

                context_parts.append(chunk_text)
                current_length += len(chunk_text)

        # PRIORITY 2: Text chunks (similarity filtered)
        if chunks:
            logger.info(
                f"📄 Adding {len(chunks)} text chunks (similarity filtered)")
            for i, chunk in enumerate(chunks):
                chunk_text = f"{chunk.chunk_header}\n{chunk.chunk_text[:500]}{'...' if len(chunk.chunk_text) > 500 else ''}\n"

                if current_length + len(chunk_text) > max_length:
                    logger.info(
                        f"📎 Context truncated at {current_length} chars ({i} text chunks)")
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

    def _create_chunk_header(self, url: str, chunk_data: Dict[str, Any]) -> str:
        """
        Create a lightweight chunk header for attachment chunks

        Per consultation guidance:
        "[ATTACHMENT] filename - description (≤ 120 chars)"

        Args:
            url: The file URL
            chunk_data: Chunk metadata

        Returns:
            Formatted chunk header string
        """
        import os
        from urllib.parse import urlparse, unquote

        try:
            # Extract filename from URL
            parsed_url = urlparse(url)
            filename = unquote(os.path.basename(parsed_url.path))

            # If no filename in path, use the last part of URL
            if not filename or filename == '/':
                filename = url.split('/')[-1] if '/' in url else url

            # Get file type/description
            file_extension = os.path.splitext(
                filename)[1].lower() if '.' in filename else ''

            if file_extension in ['.pdf']:
                description = "PDF document"
            elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                description = "image (extracted via OCR)" if chunk_data.get(
                    'source') == 'ocr' else "image"
            elif file_extension in ['.doc', '.docx']:
                description = "Word document"
            elif file_extension in ['.txt']:
                description = "text file"
            elif file_extension in ['.md']:
                description = "markdown file"
            else:
                description = "document"

            # Add section info if available
            section_id = chunk_data.get('section_id', '')
            if section_id and section_id != '':
                description = f"{description} - {section_id}"

            # Format header with length limit (≤ 120 chars as per consultation)
            header = f"[ATTACHMENT] {filename} - {description}"
            if len(header) > 120:
                # Truncate filename if too long
                max_filename_length = 120 - \
                    len(f"[ATTACHMENT]  - {description}")
                if max_filename_length > 10:
                    filename = filename[:max_filename_length-3] + "..."
                    header = f"[ATTACHMENT] {filename} - {description}"
                else:
                    header = header[:117] + "..."

            return header

        except Exception as e:
            logger.warning(f"Failed to create chunk header for {url}: {e}")
            return f"[ATTACHMENT] {url[:50]}..." if len(url) > 50 else f"[ATTACHMENT] {url}"

    def _is_image_chunk(self, url: str, chunk_data: Dict[str, Any]) -> bool:
        """
        Determine if a chunk is from an image file

        Args:
            url: The source URL
            chunk_data: The chunk metadata

        Returns:
            True if this chunk is from an image file
        """
        try:
            from urllib.parse import urlparse
            import os

            # Check URL extension
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            file_extension = os.path.splitext(filename)[1].lower()

            # Check if URL indicates image file
            if file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                return True

            # Check chunk metadata for image indicators
            source = chunk_data.get('source', '')
            if source == 'ocr' or 'image' in source.lower():
                return True

            # Check chunk content for image processing indicators
            chunk_text = chunk_data.get('chunk_text', '')
            if any(indicator in chunk_text.lower() for indicator in [
                'image file from', 'extracted content from image',
                'azure openai gpt-4o mini', 'image processing'
            ]):
                return True

            return False

        except Exception as e:
            logger.warning(f"Error detecting image chunk for {url}: {e}")
            return False


# Global instance
file_attachment_manager = FileAttachmentManager()
