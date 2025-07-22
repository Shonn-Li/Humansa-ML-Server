"""
Conversation embedding utilities for creating embeddings from chat conversations
Implements user+assistant message pairing rules as specified
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from src.utility.postgres import save_conversation_embeddings, save_url_embeddings, save_user_url_embeddings, check_url_embeddings_exist, check_user_url_embeddings_exist, get_url_embeddings, get_user_url_embeddings
import requests
import base64
from pathlib import Path
import tempfile
import os

# Try importing LlamaIndex components for image processing
try:
    from llama_index.llms.openai import OpenAI
    from llama_index.core.llms import ChatMessage, TextBlock, ImageBlock
    LLAMA_OPENAI_AVAILABLE = True
except ImportError:
    LLAMA_OPENAI_AVAILABLE = False
    logger.warning(
        "LlamaIndex OpenAI components not available for image processing.")

logger = logging.getLogger(__name__)

# Try importing file readers
try:
    from llama_index.readers.file import PDFReader, ImageReader
    FILE_READERS_AVAILABLE = True
except ImportError:
    FILE_READERS_AVAILABLE = False
    logger.warning(
        "File readers not available. Install llama-index-readers-file for URL embedding support.")

# Try importing OCR dependencies for image processing
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning(
        "OCR dependencies not available. Install pytesseract and pillow for image text extraction.")

# Try importing embedding model
try:
    from llama_index.embeddings.openai import OpenAIEmbedding
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("OpenAI embeddings not available.")


def chunk_conversation_messages(messages: List[Dict[str, Any]], max_tokens: int = 1024) -> List[Dict[str, Any]]:
    """
    Chunk conversation messages following the specified rules:
    1. Pair user + assistant together when combined tokens ≤ 1024
    2. If pair > 1024, split assistant side, keep user question whole
    3. If single user message > 1024, sentence-split at ~700 tokens each

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens per chunk (default 1024)

    Returns:
        List of chunk dicts with metadata
    """
    chunks = []
    i = 0

    while i < len(messages):
        message = messages[i]

        if message['role'] == 'user':
            user_message = message
            user_tokens = estimate_tokens(user_message['content'])

            # Look for assistant response
            assistant_message = None
            if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant':
                assistant_message = messages[i + 1]
                assistant_tokens = estimate_tokens(
                    assistant_message['content'])
            else:
                assistant_tokens = 0

            # Check if single user message is too long
            if user_tokens > max_tokens:
                # Split user message at sentence boundaries
                user_chunks = split_long_message(user_message['content'], 700)
                for idx, chunk_text in enumerate(user_chunks):
                    chunks.append({
                        'text': chunk_text,
                        'source': 'conversation',
                        'metadata': {
                            'role_pair': 'user_only',
                            'user_msg_id': user_message.get('id'),
                            'chunk_index': idx,
                            'total_chunks': len(user_chunks)
                        }
                    })
                i += 1
                continue

            # Try to pair user + assistant
            if assistant_message and (user_tokens + assistant_tokens) <= max_tokens:
                # Pair them together
                combined_text = f"User: {user_message['content']}\n\nAssistant: {assistant_message['content']}"
                chunks.append({
                    'text': combined_text,
                    'source': 'conversation',
                    'metadata': {
                        'role_pair': 'user+assistant',
                        'user_msg_id': user_message.get('id'),
                        'assistant_msg_id': assistant_message.get('id')
                    }
                })
                i += 2  # Skip both messages
            elif assistant_message:
                # Split assistant response, keep user whole
                assistant_chunks = split_long_message(
                    assistant_message['content'], max_tokens - user_tokens - 50)

                for idx, assistant_chunk in enumerate(assistant_chunks):
                    if idx == 0:
                        # First chunk includes user message
                        combined_text = f"User: {user_message['content']}\n\nAssistant: {assistant_chunk}"
                    else:
                        # Subsequent chunks are assistant only
                        combined_text = f"Assistant (continued): {assistant_chunk}"

                    chunks.append({
                        'text': combined_text,
                        'source': 'conversation',
                        'metadata': {
                            'role_pair': 'user+assistant_split' if idx == 0 else 'assistant_continuation',
                            'user_msg_id': user_message.get('id'),
                            'assistant_msg_id': assistant_message.get('id'),
                            'chunk_index': idx,
                            'total_chunks': len(assistant_chunks)
                        }
                    })
                i += 2
            else:
                # User message without assistant response
                chunks.append({
                    'text': f"User: {user_message['content']}",
                    'source': 'conversation',
                    'metadata': {
                        'role_pair': 'user_only',
                        'user_msg_id': user_message.get('id')
                    }
                })
                i += 1

        elif message['role'] == 'assistant':
            # Standalone assistant message (no preceding user message)
            assistant_tokens = estimate_tokens(message['content'])

            if assistant_tokens > max_tokens:
                assistant_chunks = split_long_message(
                    message['content'], max_tokens)
                for idx, chunk_text in enumerate(assistant_chunks):
                    chunks.append({
                        'text': f"Assistant: {chunk_text}",
                        'source': 'conversation',
                        'metadata': {
                            'role_pair': 'assistant_only',
                            'assistant_msg_id': message.get('id'),
                            'chunk_index': idx,
                            'total_chunks': len(assistant_chunks)
                        }
                    })
            else:
                chunks.append({
                    'text': f"Assistant: {message['content']}",
                    'source': 'conversation',
                    'metadata': {
                        'role_pair': 'assistant_only',
                        'assistant_msg_id': message.get('id')
                    }
                })
            i += 1
        else:
            # System or other role messages
            chunks.append({
                'text': f"{message['role'].title()}: {message['content']}",
                'source': 'conversation',
                'metadata': {
                    'role_pair': message['role'],
                    'msg_id': message.get('id')
                }
            })
            i += 1

    return chunks


def estimate_tokens(text: str) -> int:
    """Rough token estimation - approximately 1 token per 4 characters"""
    return len(text) // 4


def split_long_message(text: str, max_tokens: int) -> List[str]:
    """Split long message at sentence boundaries, targeting max_tokens per chunk"""
    max_chars = max_tokens * 4  # Rough char to token conversion

    if len(text) <= max_chars:
        return [text]

    # Try to split at sentence boundaries first
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # Add period back except for last sentence
        if not sentence.endswith('.') and sentence != sentences[-1]:
            sentence += '.'

        # Check if adding this sentence would exceed limit
        if len(current_chunk) + len(sentence) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    # If we still have chunks that are too long, split them at word boundaries
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
        else:
            # Split at word boundaries
            words = chunk.split()
            current_word_chunk = ""
            for word in words:
                if len(current_word_chunk) + len(word) + 1 > max_chars and current_word_chunk:
                    final_chunks.append(current_word_chunk.strip())
                    current_word_chunk = word
                else:
                    if current_word_chunk:
                        current_word_chunk += " " + word
                    else:
                        current_word_chunk = word
            if current_word_chunk:
                final_chunks.append(current_word_chunk.strip())

    return final_chunks


async def create_conversation_embeddings(conversation_id: int, messages: List[Dict[str, Any]]) -> bool:
    """
    Create embeddings for a conversation using the message pairing rules

    Args:
        conversation_id: ID of the conversation
        messages: List of message dicts with 'role', 'content', and optional 'id'

    Returns:
        bool: True if successful, False otherwise
    """
    if not EMBEDDINGS_AVAILABLE:
        logger.error("Embeddings not available - install required packages")
        return False

    try:
        # Chunk the conversation
        chunks = chunk_conversation_messages(messages)

        if not chunks:
            logger.warning(
                f"No chunks created for conversation {conversation_id}")
            return False

        # Create embeddings
        embedding_model = OpenAIEmbedding()
        embeddings_data = []

        for chunk in chunks:
            # Generate embedding
            embedding = embedding_model.get_text_embedding(chunk['text'])

            embeddings_data.append((
                embedding,
                chunk['text'],
                chunk['source'],
                chunk['metadata']
            ))

        # Save to database
        save_conversation_embeddings(conversation_id, embeddings_data)
        logger.info(
            f"Created {len(embeddings_data)} embeddings for conversation {conversation_id}")
        return True

    except Exception as e:
        logger.error(f"Error creating conversation embeddings: {e}")
        return False


async def create_incremental_message_embeddings(conversation_id: int, new_messages: List[Dict[str, Any]]) -> bool:
    """
    Create embeddings for new messages in an existing conversation
    This is used when users add new messages to an ongoing conversation

    Args:
        conversation_id: ID of the conversation
        new_messages: List of new message dicts to embed

    Returns:
        bool: True if successful, False otherwise
    """
    if not EMBEDDINGS_AVAILABLE:
        logger.error("Embeddings not available - install required packages")
        return False

    try:
        # Chunk just the new messages
        chunks = chunk_conversation_messages(new_messages)

        if not chunks:
            logger.warning(
                f"No chunks created for new messages in conversation {conversation_id}")
            return False

        # Create embeddings for new chunks
        embedding_model = OpenAIEmbedding()
        embeddings_data = []

        for chunk in chunks:
            embedding = embedding_model.get_text_embedding(chunk['text'])
            embeddings_data.append((
                embedding,
                chunk['text'],
                chunk['source'],
                chunk['metadata']
            ))

        # Get existing embeddings count to offset section_ids
        from src.utility.postgres import get_embeddings_v2
        existing_embeddings = get_embeddings_v2(
            conversation_id, 'conversation')
        offset = len(existing_embeddings) if existing_embeddings else 0

        # Append new embeddings (don't replace existing ones)
        save_incremental_conversation_embeddings(
            conversation_id, embeddings_data, offset)
        logger.info(
            f"Added {len(embeddings_data)} new embeddings for conversation {conversation_id}")
        return True

    except Exception as e:
        logger.error(f"Error creating incremental message embeddings: {e}")
        return False


def save_incremental_conversation_embeddings(conversation_id: int, embeddings_data: List[tuple], offset: int = 0):
    """Save new conversation embeddings without deleting existing ones"""
    import psycopg2
    from src.utility.postgres import get_db_connection
    import json

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Insert new embeddings with offset section_ids
            for section_id, (embedding, chunk_text, source, metadata) in enumerate(embeddings_data):
                # Convert to pgvector format
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"

                cursor.execute(
                    """
                    INSERT INTO embedding_v1 (type_id, type, section_id, embedding, chunk_text, source, metadata, last_updated)
                    VALUES (%s, %s, %s, %s::vector, %s, %s, %s, NOW())
                """,
                    (conversation_id, 'conversation', section_id + offset,
                     embedding_str, chunk_text, source, json.dumps(metadata)),
                )

            conn.commit()
            logger.info(
                f"Saved {len(embeddings_data)} incremental conversation embeddings")

    except Exception as e:
        logger.error(f"Error saving incremental conversation embeddings: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


async def create_user_url_embeddings(url: str, user_id: int) -> bool:
    """
    Create embeddings for a URL (document/image) with user ownership

    Args:
        url: URL to process and embed
        user_id: ID of the user who owns this attachment

    Returns:
        bool: True if successful, False otherwise
    """
    if not EMBEDDINGS_AVAILABLE or not FILE_READERS_AVAILABLE:
        logger.error("Required packages not available for URL embedding")
        return False

    try:
        # Check if embeddings already exist for this user and URL
        if check_user_url_embeddings_exist(url, user_id):
            logger.info(
                f"Embeddings already exist for user {user_id} and URL: {url}")
            return True

        # Download and process the file
        file_content = await download_and_process_url(url)

        if not file_content:
            logger.error(f"Failed to extract content from URL: {url}")
            return False

        # Create embeddings
        embedding_model = OpenAIEmbedding()
        chunks = chunk_document_content(file_content, url)

        embeddings_data = []
        for chunk in chunks:
            embedding = embedding_model.get_text_embedding(chunk['text'])
            embeddings_data.append((
                embedding,
                chunk['text'],
                chunk['source'],
                chunk['metadata']
            ))

        # Save to database with user ownership
        save_user_url_embeddings(url, user_id, embeddings_data)
        logger.info(
            f"Created {len(embeddings_data)} embeddings for user {user_id} and URL: {url}")
        return True

    except Exception as e:
        logger.error(f"Error creating user URL embeddings for {url}: {e}")
        return False


async def create_url_embeddings(url: str) -> bool:
    """
    Create embeddings for a URL (document/image)
    DEPRECATED: Use create_user_url_embeddings instead

    Args:
        url: URL to process and embed

    Returns:
        bool: True if successful, False otherwise
    """
    if not EMBEDDINGS_AVAILABLE or not FILE_READERS_AVAILABLE:
        logger.error("Required packages not available for URL embedding")
        return False

    try:
        # Check if embeddings already exist
        if check_url_embeddings_exist(url):
            logger.info(f"Embeddings already exist for URL: {url}")
            return True

        # Download and process the file
        file_content = await download_and_process_url(url)

        if not file_content:
            logger.error(f"Failed to extract content from URL: {url}")
            return False

        # Create embeddings
        embedding_model = OpenAIEmbedding()
        chunks = chunk_document_content(file_content, url)

        embeddings_data = []
        for chunk in chunks:
            embedding = embedding_model.get_text_embedding(chunk['text'])
            embeddings_data.append((
                embedding,
                chunk['text'],
                chunk['source'],
                chunk['metadata']
            ))

        # Save to database
        save_url_embeddings(url, embeddings_data)
        logger.info(
            f"Created {len(embeddings_data)} embeddings for URL: {url}")
        return True

    except Exception as e:
        logger.error(f"Error creating URL embeddings for {url}: {e}")
        return False


async def download_and_process_url(url: str) -> Optional[str]:
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
            # Extract extension from URL if content-type is unclear
            file_extension = Path(url.split('?')[0]).suffix.lower()

        # Create temporary file with correct extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        try:
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                # Process PDF
                pdf_reader = PDFReader()
                documents = pdf_reader.load_data(file=Path(temp_path))
                content = "\n\n".join([doc.text for doc in documents])

            elif any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']) or file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # Process image using GPT-4o mini for vision interpretation
                content = await process_image_with_gpt4o(temp_path, url)

                if not content:
                    logger.warning(
                        f"Failed to extract content from image using GPT-4o mini")
                    content = f"[IMAGE: Unable to extract content. URL: {url}]"

            else:
                logger.warning(
                    f"Unsupported content type for URL {url}: {content_type}")
                return None

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


def chunk_document_content(content: str, url: str, max_tokens: int = 1024) -> List[Dict[str, Any]]:
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


async def process_image_with_gpt4o(image_path: str, url: str) -> Optional[str]:
    """Process image using GPT-4o mini via LlamaIndex to extract text content"""
    if not LLAMA_OPENAI_AVAILABLE:
        logger.error(
            "LlamaIndex OpenAI components not available for image processing")
        return None

    try:
        # Log file details for debugging
        logger.info(f"Processing image: {image_path}")
        logger.info(f"File exists: {Path(image_path).exists()}")
        logger.info(
            f"File size: {Path(image_path).stat().st_size if Path(image_path).exists() else 'N/A'} bytes")

        # Initialize GPT-4o mini model via LlamaIndex
        llm = OpenAI(model="gpt-4.1-nano", temperature=0.1)

        # Create message with image and text prompt using LlamaIndex blocks
        messages = [
            ChatMessage(
                role="user",
                blocks=[
                    TextBlock(
                        text="Please extract all text content from this image. If the image contains text, transcribe it exactly as it appears. If the image is a diagram, chart, or infographic, describe the key information and data shown. If it's a screenshot of code or documentation, extract the text content. Be comprehensive and detailed in your response."
                    ),
                    ImageBlock(path=image_path),
                ],
            )
        ]

        # Get response from GPT-4o mini
        logger.info("Sending image to GPT-4o mini for processing...")
        response = llm.chat(messages)
        extracted_content = response.message.content

        if extracted_content and extracted_content.strip():
            logger.info(
                f"Successfully extracted content from image using GPT-4o mini via LlamaIndex: {len(extracted_content)} chars")
            return extracted_content.strip()
        else:
            logger.warning("GPT-4o mini returned empty content for image")
            return None

    except Exception as e:
        logger.error(
            f"Error processing image with GPT-4o mini via LlamaIndex: {e}")
        logger.error(f"Image path: {image_path}")
        logger.error(f"Original URL: {url}")
        return None
