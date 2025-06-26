"""
Citation Engine Module - Advanced citation system with streaming support

This module provides citation capabilities using existing context chunks
without additional embeddings. Features:
- Streaming progress updates for context gathering phases
- Priority-based progress streaming (RAG → Attachments → Web Search)
- Direct citation from existing chunks
- Modular and independent design
"""

from .citation_engine import CitationEngine, CitationResult
from .streaming_citation_engine import StreamingCitationEngine

__all__ = [
    'CitationEngine',
    'CitationResult',
    'StreamingCitationEngine'
]
