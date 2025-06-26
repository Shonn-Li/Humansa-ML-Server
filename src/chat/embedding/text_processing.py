"""
Independent Text Processing for Modular Embedding System

This module provides text chunking and processing functionality without external dependencies.
All logic copied from existing implementations - NO PLACEHOLDERS.
"""

import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TextProcessor:
    """Independent text processing for embedding system"""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(
            f"Initialized TextProcessor with chunk_size={chunk_size}, overlap={chunk_overlap}")

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap, prioritizing sentence boundaries

        Args:
            text: Text to split

        Returns:
            List[str]: List of text chunks
        """
        if not text or not text.strip():
            return []

        # Convert chunk sizes to approximate character counts (1 token ≈ 4 chars)
        max_chars = self.chunk_size * 4
        overlap_chars = self.chunk_overlap * 4

        # If text is shorter than max chunk size, return as single chunk
        if len(text) <= max_chars:
            return [text.strip()]

        chunks = []

        # First, try to split by paragraphs
        paragraphs = text.split('\n\n')
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) + 2 > max_chars and current_chunk:
                # Finalize current chunk
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(
                    current_chunk, overlap_chars)
                current_chunk = overlap_text + "\n\n" + paragraph if overlap_text else paragraph
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        # If we still have chunks that are too long, split by sentences
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chars:
                final_chunks.append(chunk)
            else:
                sentence_chunks = self._split_by_sentences(
                    chunk, max_chars, overlap_chars)
                final_chunks.extend(sentence_chunks)

        logger.info(f"Split text into {len(final_chunks)} chunks")
        return final_chunks

    def _get_overlap_text(self, text: str, overlap_chars: int) -> str:
        """Get overlap text from the end of a chunk"""
        if len(text) <= overlap_chars:
            return text

        # Try to find a good break point (sentence or word boundary)
        end_portion = text[-overlap_chars:]

        # Look for sentence boundary
        sentences = end_portion.split('. ')
        if len(sentences) > 1:
            return '. '.join(sentences[1:])

        # Look for word boundary
        words = end_portion.split()
        if len(words) > 3:
            return ' '.join(words[1:])

        return end_portion

    def _split_by_sentences(self, text: str, max_chars: int, overlap_chars: int) -> List[str]:
        """Split text by sentences when paragraph-level splitting isn't enough"""
        # Split by sentences using multiple delimiters
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If single sentence is too long, split by words
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                word_chunks = self._split_by_words(
                    sentence, max_chars, overlap_chars)
                chunks.extend(word_chunks)
                continue

            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 2 > max_chars and current_chunk:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(
                    current_chunk, overlap_chars)
                current_chunk = overlap_text + " " + sentence if overlap_text else sentence
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_words(self, text: str, max_chars: int, overlap_chars: int) -> List[str]:
        """Split text by words as a last resort"""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            # If adding this word would exceed chunk size
            if len(current_chunk) + len(word) + 1 > max_chars and current_chunk:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_words = self._get_overlap_words(
                    current_chunk, overlap_chars)
                current_chunk = overlap_words + " " + word if overlap_words else word
            else:
                # Add word to current chunk
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap_words(self, text: str, overlap_chars: int) -> str:
        """Get overlap words from the end of a chunk"""
        if len(text) <= overlap_chars:
            return text

        words = text.split()
        overlap_text = ""

        # Add words from the end until we reach overlap_chars
        for word in reversed(words):
            if len(overlap_text) + len(word) + 1 <= overlap_chars:
                if overlap_text:
                    overlap_text = word + " " + overlap_text
                else:
                    overlap_text = word
            else:
                break

        return overlap_text

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (1 token ≈ 4 characters)"""
        return len(text) // 4

    def clean_text(self, text: str) -> str:
        """Clean text by removing excessive whitespace and normalizing"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def validate_chunk_sizes(self, chunks: List[str]) -> Dict[str, Any]:
        """Validate that chunks are within expected size limits"""
        if not chunks:
            return {"valid": True, "issues": []}

        issues = []
        max_chars = self.chunk_size * 4

        for i, chunk in enumerate(chunks):
            chunk_tokens = self.estimate_tokens(chunk)

            if chunk_tokens > self.chunk_size * 1.2:  # Allow 20% tolerance
                issues.append({
                    "chunk_index": i,
                    "estimated_tokens": chunk_tokens,
                    "max_tokens": self.chunk_size,
                    "text_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
                })

        return {
            "valid": len(issues) == 0,
            "total_chunks": len(chunks),
            "oversized_chunks": len(issues),
            "issues": issues,
            "avg_tokens": sum(self.estimate_tokens(chunk) for chunk in chunks) / len(chunks)
        }


class ConversationProcessor:
    """Process conversation messages into chunks following specific rules"""

    def __init__(self, max_tokens: int = 1024):
        self.max_tokens = max_tokens
        self.text_processor = TextProcessor(chunk_size=max_tokens)
        logger.info(
            f"Initialized ConversationProcessor with max_tokens={max_tokens}")

    def chunk_conversation_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk conversation messages following the specified rules:
        1. Pair user + assistant together when combined tokens ≤ 1024
        2. If pair > 1024, split assistant side, keep user question whole
        3. If single user message > 1024, sentence-split at ~700 tokens each
        """
        chunks = []
        i = 0

        while i < len(messages):
            message = messages[i]

            if message['role'] == 'user':
                user_message = message
                user_tokens = self._estimate_tokens(user_message['content'])

                # Look for assistant response
                assistant_message = None
                if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant':
                    assistant_message = messages[i + 1]
                    assistant_tokens = self._estimate_tokens(
                        assistant_message['content'])
                else:
                    assistant_tokens = 0

                # Check if single user message is too long
                if user_tokens > self.max_tokens:
                    # Split user message at sentence boundaries
                    user_chunks = self._split_long_message(
                        user_message['content'], 700)
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
                if assistant_message and (user_tokens + assistant_tokens) <= self.max_tokens:
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
                    assistant_chunks = self._split_long_message(
                        assistant_message['content'], self.max_tokens - user_tokens - 50)

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
                # Standalone assistant message
                assistant_tokens = self._estimate_tokens(message['content'])

                if assistant_tokens > self.max_tokens:
                    assistant_chunks = self._split_long_message(
                        message['content'], self.max_tokens)
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

        logger.info(f"Chunked conversation into {len(chunks)} chunks")
        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation - approximately 1 token per 4 characters"""
        return len(text) // 4

    def _split_long_message(self, text: str, max_tokens: int) -> List[str]:
        """Split long message at sentence boundaries, targeting max_tokens per chunk"""
        max_chars = max_tokens * 4  # Rough char to token conversion

        if len(text) <= max_chars:
            return [text]

        # Use the text processor for consistent splitting
        temp_processor = TextProcessor(chunk_size=max_tokens, chunk_overlap=50)
        return temp_processor.split_text(text)


# Global instances
text_processor = TextProcessor()
conversation_processor = ConversationProcessor()
