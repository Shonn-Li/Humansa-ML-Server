"""
Modular embedding system for notes and conversations.

This module provides:
- Async embedding checks and creation for missing embeddings
- Admin endpoints for bulk embedding operations
- Modular, clean separation from legacy embedding code
"""

from .embedding_manager import EmbeddingManager
from .note_embedder import NoteEmbedder
from .conversation_embedder import ConversationEmbedder
from .admin_embedding_endpoint import admin_embedding_bp

__all__ = [
    'EmbeddingManager',
    'NoteEmbedder',
    'ConversationEmbedder',
    'admin_embedding_bp'
]
