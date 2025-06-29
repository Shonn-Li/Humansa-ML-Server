"""
URL Embedding Operations for Modular Chat System

This module handles all URL-related embedding database operations
within the chat module structure - no external dependencies.
"""

import os
import json
import logging
import requests
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector

# Use the new provider-based embedding approach
from ..embedding.embedding_provider_selector import EmbeddingProviderSelector

# Import Azure Inference for GPT-4o mini image processing
try:
    from llama_index.llms.azure_inference import AzureAICompletionsModel
    AZURE_INFERENCE_AVAILABLE = True
except ImportError:
    AZURE_INFERENCE_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "Azure Inference not available - image processing will be limited")

# Import LlamaIndex core schema for image processing (separate from file readers)
try:
    from llama_index.core.base.llms.types import ChatMessage, ImageBlock, TextBlock
    LLAMAINDEX_SCHEMA_AVAILABLE = True
except ImportError:
    LLAMAINDEX_SCHEMA_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "LlamaIndex core schema not available - image processing will be limited")

# Import LlamaIndex file readers for PDF processing (separate from core schema)
try:
    from llama_index.readers.file import PDFReader
    LLAMAINDEX_PDF_READER_AVAILABLE = True
except ImportError:
    LLAMAINDEX_PDF_READER_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "LlamaIndex PDFReader not available - PDF processing will use PyPDF2 fallback")

logger = logging.getLogger(__name__)

# Fallback: Import PyPDF2 if LlamaIndex PDFReader not available
if not LLAMAINDEX_PDF_READER_AVAILABLE:
    try:
        import PyPDF2
        PDF_PROCESSING_AVAILABLE = True
        logger.info("✅ PyPDF2 fallback available")
    except ImportError:
        PDF_PROCESSING_AVAILABLE = False
        logger.warning("No PDF processing libraries available")
else:
    PDF_PROCESSING_AVAILABLE = True  # LlamaIndex PDFReader is available

# Import PIL for basic image processing if available
try:
    from PIL import Image
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logger.warning("PIL not available - basic image processing disabled")


class URLEmbeddingOperations:
    """Database operations specifically for URL embeddings"""

    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT")),
            "user": os.getenv("DB_USERNAME"),
            "password": os.getenv("DB_PASSWORD"),
            "dbname": os.getenv("DB_ACTIVE_DATABASE"),
        }
        self.embedder = EmbeddingProviderSelector().get_embedding_client()
        logger.info("URLEmbeddingOperations initialized")

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing query parameters and fragments for consistent storage/matching.

        This fixes the issue where S3 presigned URLs with different query parameters
        don't match the clean URLs used in attachments.

        Example:
        Input:  https://example.com/file.jpg?X-Amz-Algorithm=...&X-Amz-Signature=...
        Output: https://example.com/file.jpg
        """
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            # Keep scheme, netloc, path - remove params, query, fragment
            normalized = urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

            if normalized != url:
                logger.debug(
                    f"🔧 URL normalized: {url[:50]}... -> {normalized}")

            return normalized
        except Exception as e:
            logger.warning(
                f"Failed to normalize URL {url}: {e}, using original")
            return url

    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            register_vector(conn)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def check_user_url_embeddings_exist(self, url: str, user_id: int) -> bool:
        """
        Check if embeddings exist for a URL owned by a specific user

        Args:
            url: The URL to check (will be normalized to remove query parameters)
            user_id: The user ID who should own the embeddings

        Returns:
            bool: True if embeddings exist for this user and URL
        """
        try:
            # Normalize URL to remove query parameters for consistent matching
            normalized_url = self._normalize_url(url)

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM embedding_v1 WHERE type = 'user' AND type_id = %s AND url = %s",
                        (user_id, normalized_url),
                    )
                    count = cursor.fetchone()[0]
                    logger.debug(
                        f"🔍 URL embedding check: {normalized_url} -> {count > 0}")
                    return count > 0
        except Exception as e:
            logger.error(f"Error checking user URL embeddings: {e}")
            return False

    def get_user_url_embeddings(self, url: str, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get embeddings for a URL owned by a specific user

        Args:
            url: The URL to get embeddings for (will be normalized to remove query parameters)
            user_id: The user ID who owns the embeddings

        Returns:
            List of embedding data or None if not found
        """
        try:
            # Normalize URL to remove query parameters for consistent matching
            normalized_url = self._normalize_url(url)

            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT embedding::text, chunk_text, source, section_id, url, metadata
                        FROM embedding_v1 
                        WHERE type = 'user' AND type_id = %s AND url = %s
                        ORDER BY section_id
                    """,
                        (user_id, normalized_url),
                    )

                    results = cursor.fetchall()
                    if results:
                        parsed_results = []
                        for row in results:
                            row_dict = dict(row)

                            # Parse the embedding vector string back to list
                            embedding_str = row_dict['embedding']
                            if embedding_str:
                                # Remove brackets and split by comma
                                embedding_str = embedding_str.strip('[]')
                                row_dict['embedding'] = [
                                    float(x.strip()) for x in embedding_str.split(',')]

                            parsed_results.append(row_dict)

                        logger.debug(
                            f"📄 Found {len(parsed_results)} embeddings for normalized URL: {normalized_url}")
                        return parsed_results
                    return None
        except Exception as e:
            logger.error(f"Error getting user URL embeddings: {e}")
            return None

    def save_user_url_embeddings(self, url: str, user_id: int, embeddings_data: List[Tuple]) -> bool:
        """
        Save URL embeddings for file attachments with user ownership

        Args:
            url: The URL of the file/attachment (will be normalized to remove query parameters)
            user_id: The ID of the user who owns the attachment
            embeddings_data: List of (embedding_vector, chunk_text, source, metadata) tuples

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Normalize URL to remove query parameters for consistent storage
            normalized_url = self._normalize_url(url)

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Delete existing embeddings for this user and normalized URL
                    cursor.execute(
                        "DELETE FROM embedding_v1 WHERE type = 'user' AND type_id = %s AND url = %s",
                        (user_id, normalized_url)
                    )

                    # Insert new embeddings with normalized URL
                    for section_id, (embedding, chunk_text, source, *metadata) in enumerate(embeddings_data):
                        # Convert to pgvector format
                        embedding_str = "[" + \
                            ",".join(map(str, embedding)) + "]"

                        # Extract additional metadata if provided
                        extra_metadata = metadata[0] if metadata else {}

                        cursor.execute(
                            """
                            INSERT INTO embedding_v1 (type_id, type, section_id, embedding, chunk_text, source, url, metadata, last_updated)
                            VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, NOW())
                        """,
                            (user_id, 'user', section_id, embedding_str, chunk_text,
                             source, normalized_url, json.dumps(extra_metadata) if extra_metadata else None),
                        )

                    conn.commit()
                    logger.info(
                        f"Saved {len(embeddings_data)} URL embeddings for user {user_id}, URL: {normalized_url}")
                    return True

        except Exception as e:
            logger.error(f"Error saving user URL embeddings: {e}")
            return False

    def delete_user_url_embeddings(self, url: str, user_id: int) -> bool:
        """
        Delete all embeddings for a specific URL and user

        Args:
            url: The URL to delete embeddings for (will be normalized to remove query parameters)
            user_id: The user ID who owns the embeddings

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Normalize URL to remove query parameters for consistent matching
            normalized_url = self._normalize_url(url)

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM embedding_v1 WHERE type = 'user' AND type_id = %s AND url = %s",
                        (user_id, normalized_url)
                    )
                    deleted_count = cursor.rowcount
                    conn.commit()

                    logger.info(
                        f"Deleted {deleted_count} URL embeddings for user {user_id}, URL: {normalized_url}")
                    return True

        except Exception as e:
            logger.error(f"Error deleting user URL embeddings: {e}")
            return False

    def get_user_url_count(self, user_id: int) -> int:
        """
        Get the count of URLs with embeddings for a specific user

        Args:
            user_id: The user ID

        Returns:
            int: Number of unique URLs with embeddings for this user
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(DISTINCT url) FROM embedding_v1 WHERE type = 'user' AND type_id = %s AND url IS NOT NULL",
                        (user_id,)
                    )
                    count = cursor.fetchone()[0]
                    return count
        except Exception as e:
            logger.error(f"Error getting user URL count: {e}")
            return 0

    def get_user_urls(self, user_id: int) -> List[str]:
        """
        Get all URLs with embeddings for a specific user

        Args:
            user_id: The user ID

        Returns:
            List[str]: List of URLs with embeddings for this user
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT DISTINCT url FROM embedding_v1 WHERE type = 'user' AND type_id = %s AND url IS NOT NULL ORDER BY url",
                        (user_id,)
                    )
                    results = cursor.fetchall()
                    return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting user URLs: {e}")
            return []

    def update_embeddings_to_conversation(self, user_id: int, conversation_type: str,
                                          conversation_type_id: int, attachment_urls: List[str]) -> int:
        """
        Update embeddings from user ownership to conversation ownership

        Args:
            user_id: The current user owner
            conversation_type: The type of conversation (user, note, folder)
            conversation_type_id: The ID of the conversation target
            attachment_urls: List of URLs to update (will be normalized to remove query parameters)

        Returns:
            int: Number of updated embeddings
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    updated_count = 0

                    for url in attachment_urls:
                        # Normalize URL to remove query parameters for consistent matching
                        normalized_url = self._normalize_url(url)

                        cursor.execute(
                            """
                            UPDATE embedding_v1 
                            SET type = %s, type_id = %s 
                            WHERE type = 'user' AND type_id = %s AND url = %s
                            """,
                            (conversation_type, conversation_type_id,
                             user_id, normalized_url),
                        )
                        updated_count += cursor.rowcount

                    conn.commit()

                    logger.info(
                        f"Updated {updated_count} embeddings from user {user_id} to {conversation_type}:{conversation_type_id} for {len(attachment_urls)} URLs")
                    return updated_count

        except Exception as e:
            logger.error(f"Error updating embeddings to conversation: {e}")
            return 0

    def get_url_embedding_stats(self, url: str, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about embeddings for a specific URL

        Args:
            url: The URL to get stats for (will be normalized to remove query parameters)
            user_id: The user ID who owns the embeddings

        Returns:
            Dict with statistics
        """
        try:
            # Normalize URL to remove query parameters for consistent matching
            normalized_url = self._normalize_url(url)

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            COUNT(*) as chunk_count,
                            AVG(LENGTH(chunk_text)) as avg_chunk_length,
                            MAX(last_updated) as last_updated,
                            MIN(section_id) as min_section,
                            MAX(section_id) as max_section
                        FROM embedding_v1 
                        WHERE type = 'user' AND type_id = %s AND url = %s
                        """,
                        (user_id, normalized_url)
                    )
                    result = cursor.fetchone()

                    if result and result[0] > 0:
                        return {
                            "url": normalized_url,
                            "user_id": user_id,
                            "chunk_count": result[0],
                            "avg_chunk_length": round(result[1], 2) if result[1] else 0,
                            "last_updated": result[2].isoformat() if result[2] else None,
                            "section_range": f"{result[3]}-{result[4]}" if result[3] is not None else "0-0"
                        }
                    else:
                        return {
                            "url": normalized_url,
                            "user_id": user_id,
                            "chunk_count": 0,
                            "exists": False
                        }

        except Exception as e:
            logger.error(f"Error getting URL embedding stats: {e}")
            return {
                "url": url,
                "user_id": user_id,
                "error": str(e)
            }

    def search_similar_chunks(self, query_embedding: List[float], user_id: int,
                              urls: List[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity

        Args:
            query_embedding: The query embedding vector
            user_id: The user ID who owns the embeddings
            urls: Optional list of URLs to restrict search to (will be normalized to remove query parameters)
            top_k: Number of top results to return

        Returns:
            List of similar chunks with similarity scores
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Convert query embedding to pgvector format
                    query_vector = "[" + \
                        ",".join(map(str, query_embedding)) + "]"

                    if urls:
                        # Normalize URLs to remove query parameters for consistent matching
                        normalized_urls = [
                            self._normalize_url(url) for url in urls]

                        # Search within specific URLs
                        url_placeholders = ",".join(
                            ["%s"] * len(normalized_urls))
                        query = f"""
                            SELECT 
                                url, chunk_text, source, section_id, metadata,
                                1 - (embedding <=> %s::vector) as similarity
                            FROM embedding_v1 
                            WHERE type = 'user' AND type_id = %s AND url IN ({url_placeholders})
                            ORDER BY embedding <=> %s::vector 
                            LIMIT %s
                        """
                        params = [query_vector, user_id] + \
                            normalized_urls + [query_vector, top_k]
                    else:
                        # Search all user URLs
                        query = """
                            SELECT 
                                url, chunk_text, source, section_id, metadata,
                                1 - (embedding <=> %s::vector) as similarity
                            FROM embedding_v1 
                            WHERE type = 'user' AND type_id = %s AND url IS NOT NULL
                            ORDER BY embedding <=> %s::vector 
                            LIMIT %s
                        """
                        params = [query_vector, user_id, query_vector, top_k]

                    cursor.execute(query, params)
                    results = cursor.fetchall()

                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []

    async def create_user_url_embeddings(self, url: str, user_id: int) -> bool:
        """
        Create embeddings for a URL (document/image) with user ownership

        Args:
            url: URL to process and embed (will be normalized to remove query parameters)
            user_id: ID of the user who owns this attachment

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if embeddings already exist for this user and URL (normalized)
            if self.check_user_url_embeddings_exist(url, user_id):
                normalized_url = self._normalize_url(url)
                logger.info(
                    f"Embeddings already exist for user {user_id} and URL: {normalized_url}")
                return True

            # Download and process the file
            file_content = await self._download_and_process_url(url)

            if not file_content:
                logger.error(f"Failed to extract content from URL: {url}")
                return False

            # Create embeddings using our OpenAI client
            chunks = self._chunk_document_content(file_content, url)
            logger.info(f"📝 Created {len(chunks)} chunks from content (length: {len(file_content)} chars)")
            
            # Log first chunk for debugging
            if chunks:
                logger.info(f"🔍 First chunk preview: {chunks[0]['text'][:100]}...")
            else:
                logger.warning("⚠️ No chunks were created from content!")
                logger.info(f"Content preview: {file_content[:200]}...")

            embeddings_data = []
            for chunk in chunks:
                try:
                    embedding = self.embedder.get_text_embedding(chunk['text'])
                    embeddings_data.append((
                        embedding,
                        chunk['text'],
                        chunk['source'],
                        chunk['metadata']
                    ))
                except Exception as e:
                    logger.error(f"Failed to create embedding for chunk: {e}")
                    continue

            if not embeddings_data:
                logger.error("No embeddings were created")
                return False

            # Save to database with user ownership (URL will be normalized in save function)
            success = self.save_user_url_embeddings(
                url, user_id, embeddings_data)
            if success:
                normalized_url = self._normalize_url(url)
                logger.info(
                    f"Created {len(embeddings_data)} embeddings for user {user_id} and URL: {normalized_url}")
            return success

        except Exception as e:
            logger.error(f"Error creating user URL embeddings for {url}: {e}")
            return False

    async def _download_and_process_url(self, url: str) -> Optional[str]:
        """Download and extract text content from a URL"""
        try:
            # Download the file
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Determine file type and extension
            content_type = response.headers.get('content-type', '').lower()

            # Determine appropriate file extension
            file_extension = ""
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                file_extension = ".pdf"
            elif any(img_type in content_type for img_type in ['image/jpeg', 'image/jpg']):
                file_extension = ".jpg"
            elif 'image/png' in content_type:
                file_extension = ".png"
            elif 'image/gif' in content_type:
                file_extension = ".gif"
            elif 'image/webp' in content_type:
                file_extension = ".webp"
            elif url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                file_extension = Path(url.split('?')[0]).suffix.lower()

            # Create temporary file with correct extension
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name

            try:
                if 'pdf' in content_type or url.lower().endswith('.pdf'):
                    # Process PDF with PyPDF2 if available
                    content = self._process_pdf_file(temp_path)
                    if not content:
                        # Fallback: treat as generic document
                        content = f"[PDF Document from {url}] - Content extraction not available"

                elif any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']) or file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    # For images, use Azure GPT-4o mini for content extraction
                    content = await self._process_image_with_gpt4o_azure(temp_path, url)

                else:
                    # Try to read as text
                    try:
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        # If not text, create a basic description
                        content = f"[DOCUMENT from {url}] - Binary content (embedding will be based on filename and context)"

                return content

            finally:
                # Clean up temp file
                try:
                    Path(temp_path).unlink()
                except:
                    pass

        except Exception as e:
            logger.error(f"Error downloading/processing URL {url}: {e}")
            return None

    def _process_pdf_file(self, file_path: str) -> Optional[str]:
        """Extract text from PDF file using LlamaIndex PDFReader or PyPDF2 fallback"""
        # Try LlamaIndex PDFReader first (preferred method)
        if LLAMAINDEX_PDF_READER_AVAILABLE:
            try:
                logger.info(f"Using LlamaIndex PDFReader for: {file_path}")
                pdf_reader = PDFReader()
                documents = pdf_reader.load_data(file=Path(file_path))

                # Combine all document texts
                text = "\n\n".join([doc.text for doc in documents])
                logger.info(
                    f"✅ LlamaIndex PDF extraction successful: {text} chars")
                return text.strip()
            except Exception as e:
                logger.error(f"❌ LlamaIndex PDFReader failed: {e}")
                logger.info("🔄 Falling back to PyPDF2...")

        # Fallback to PyPDF2 if LlamaIndex fails or not available
        if PDF_PROCESSING_AVAILABLE:
            try:
                logger.info(f"Using PyPDF2 fallback for: {file_path}")
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    logger.info(
                        f"✅ PyPDF2 extraction successful: {len(text)} chars")
                    return text.strip()
            except Exception as e:
                logger.error(f"❌ PyPDF2 extraction failed: {e}")

        logger.warning("No PDF processing libraries available")
        return None

    def _chunk_document_content(self, content: str, url: str, max_tokens: int = 1024) -> List[Dict[str, Any]]:
        """Chunk document content for embedding"""
        chunks = []
        max_chars = max_tokens * 4  # Rough estimation

        # Split content into manageable chunks
        paragraphs = content.split('\n\n')
        current_chunk = ""

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 > max_chars and current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'source': 'url_document',
                    'metadata': {
                        'url': url,
                        'chunk_type': 'document_chunk'
                    }
                })
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # Add remaining chunk
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'source': 'url_document',
                'metadata': {
                    'url': url,
                    'chunk_type': 'document_chunk'
                }
            })

        return chunks

    async def _process_image_with_gpt4o_azure(self, image_path: str, url: str) -> str:
        """
        Process image using Azure OpenAI GPT-4o mini via LlamaIndex blocks (proper vision support)

        NOTE: This function bypasses the cost-saving override that would normally redirect
        azure_openai requests to azure_inference, because Azure AI Inference does not
        support vision capabilities. Only Azure OpenAI has proper image processing support.
        """
        if not LLAMAINDEX_SCHEMA_AVAILABLE:
            logger.warning(
                "LlamaIndex ChatMessage/ImageBlock not available - falling back to simple description")
            return self._process_image_with_simple_description(image_path, url)

        # Use Azure OpenAI (has proper vision support) instead of Azure AI Inference
        # Import the LLM provider to get Azure OpenAI instance
        try:
            from ..provider.llm_provider import LLMProviderSelector
            provider_selector = LLMProviderSelector()

            # Check if Azure OpenAI is available and get the LLM instance
            available_providers = provider_selector.get_available_providers()
            if "azure_openai" not in available_providers:
                logger.warning(
                    "Azure OpenAI not available - falling back to simple description")
                return self._process_image_with_simple_description(image_path, url)

            # FORCE Azure OpenAI for vision - bypass cost-saving override
            # Use the dedicated vision method to avoid azure_inference override
            try:
                provider_enum, llm = provider_selector.force_provider_for_vision(
                    "azure_openai", "gpt-4o-mini")
                logger.info(
                    "Using Azure OpenAI for image processing (proper vision support) - bypassing cost override")
            except ValueError as e:
                logger.warning(f"Failed to force Azure OpenAI for vision: {e}")
                return self._process_image_with_simple_description(image_path, url)

        except Exception as e:
            logger.error(f"Failed to get Azure OpenAI LLM: {e}")
            return self._process_image_with_simple_description(image_path, url)

        try:
            # Log file details for debugging
            logger.info(f"Processing image: {image_path}")
            logger.info(f"File exists: {Path(image_path).exists()}")
            logger.info(
                f"File size: {Path(image_path).stat().st_size if Path(image_path).exists() else 'N/A'} bytes")

            # Create message with image and text prompt using LlamaIndex blocks
            messages = [
                ChatMessage(
                    role="user",
                    blocks=[
                        ImageBlock(path=image_path),
                        TextBlock(
                            text="Please extract all text content from this image. If the image contains text, transcribe it exactly as it appears. If the image is a diagram, chart, or infographic, describe the key information and data shown. If it's a screenshot of code or documentation, extract the text content. Be comprehensive and detailed in your response."
                        ),
                    ],
                )
            ]

            # Get response from Azure OpenAI GPT-4o mini (proper vision support)
            logger.info(
                "Sending image to Azure OpenAI GPT-4o mini for processing...")
            response = await llm.achat(messages)
            extracted_content = response.message.content
            logger.info(
                f"Received response from Azure OpenAI GPT-4o mini: {extracted_content[:100]}...")
            
            # Check if this is actually image content or an error message
            is_vision_error = any(phrase in extracted_content.lower() for phrase in [
                "can't view", "cannot view", "can't see", "cannot see", 
                "can't process images", "cannot process images", "i'm sorry"
            ]) if extracted_content else False
            
            if is_vision_error:
                logger.error("🚫 Azure AI is returning vision error - image processing failed!")
                logger.error(f"Error response: {extracted_content}")
                return self._process_image_with_simple_description(image_path, url)
                
            if extracted_content and extracted_content.strip():
                logger.info(
                    f"✅ Successfully extracted content from image using Azure OpenAI GPT-4o mini: {len(extracted_content)} chars")
                logger.info(f"🖼️ Image content preview: {extracted_content[:200]}...")
                return extracted_content.strip()
            else:
                logger.warning(
                    "Azure OpenAI GPT-4o mini returned empty content for image")
                return self._process_image_with_simple_description(image_path, url)

        except Exception as e:
            logger.error(
                f"Error processing image with Azure OpenAI GPT-4o mini: {e}")
            logger.error(f"Image path: {image_path}")
            logger.error(f"Original URL: {url}")
            logger.info("🔄 Falling back to simple image description")
            return self._process_image_with_simple_description(image_path, url)

    def _process_image_with_simple_description(self, image_path: str, url: str) -> str:
        """Create a simple description for image files"""
        try:
            file_size = Path(image_path).stat().st_size if Path(
                image_path).exists() else 0
            file_extension = Path(image_path).suffix.lower()

            # Create a basic description that can be embedded
            description = f"Image file from {url}. File type: {file_extension}, Size: {file_size} bytes. "
            description += "This is an image attachment that may contain visual content, diagrams, screenshots, or text that would require image processing to extract."

            return description
        except Exception as e:
            logger.error(f"Error creating image description: {e}")
            return f"Image file from {url}"


# Global instance for easy access
url_embedding_ops = URLEmbeddingOperations()
