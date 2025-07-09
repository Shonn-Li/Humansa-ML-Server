"""
Citation Engine - Core citation functionality using existing context chunks

This module provides citation capabilities without additional embeddings,
using the context chunks from RAG, file attachments, and web search.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CitationSource:
    """Individual citation source"""
    source_id: str
    source_type: str  # 'note', 'conversation', 'file', 'web'
    title: str
    content: str
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CitationResult:
    """Result containing response with citations"""
    response: str
    sources: List[CitationSource]
    source_mapping: Dict[str, str]  # Maps citation IDs to source IDs
    total_sources: int


class CitationEngine:
    """Core citation engine using existing context chunks"""

    def __init__(self):
        logger.info("CitationEngine initialized")

    def generate_citation_response(self,
                                   query: str,
                                   rag_context=None,
                                   attachment_context=None,
                                   websearch_context=None,
                                   llm=None) -> CitationResult:
        """
        Generate response with citations using existing context chunks

        Args:
            query: User's question
            rag_context: RAG context with chunks
            attachment_context: File attachment context
            websearch_context: Web search context  
            llm: LLM provider for generation

        Returns:
            CitationResult with response and source citations
        """
        logger.info("🔍 Generating citation response...")

        # Extract all sources from contexts
        sources = self._extract_all_sources(
            rag_context, attachment_context, websearch_context)

        if not sources:
            logger.warning("No sources available for citation")
            # Generate direct response without citations
            response = self._generate_direct_response(query, llm)
            return CitationResult(
                response=response,
                sources=[],
                source_mapping={},
                total_sources=0
            )

        # Build contextualized prompt with citation instructions
        citation_prompt = self._build_citation_prompt(query, sources)

        # Generate response with LLM
        response = llm.complete(citation_prompt).text

        # Parse and map citations
        source_mapping = self._parse_citation_mapping(response, sources)

        logger.info(
            f"✅ Citation response generated with {len(sources)} sources")

        return CitationResult(
            response=response,
            sources=sources,
            source_mapping=source_mapping,
            total_sources=len(sources)
        )

    def _extract_all_sources(self, rag_context, attachment_context, websearch_context) -> List[CitationSource]:
        """Extract all sources from different context types"""
        sources = []

        # Extract RAG sources
        if rag_context and rag_context.chunks:
            # Get note titles for all note chunks at once
            note_ids = [
                chunk.type_id for chunk in rag_context.chunks if chunk.type == "note"]
            note_titles = {}
            if note_ids:
                from ..postgres.db_manager import PostgresManager
                postgres = PostgresManager()
                note_titles = postgres.get_note_titles_batch(note_ids)

            for i, chunk in enumerate(rag_context.chunks):
                # Use note title for notes, keep conversation ID for conversations
                if chunk.type == "note":
                    title = note_titles.get(
                        chunk.type_id, f"Note {chunk.type_id}")
                else:
                    title = f"Conversation {chunk.type_id}"

                source = CitationSource(
                    source_id=f"rag_{chunk.type}_{chunk.type_id}_{i}",
                    source_type=chunk.type,
                    title=title,
                    content=chunk.chunk_text,
                    metadata={
                        'type_id': chunk.type_id,
                        'section_id': chunk.section_id,
                        'similarity': chunk.similarity
                    }
                )
                sources.append(source)

        # Extract file attachment sources
        if attachment_context and attachment_context.chunks:
            for i, chunk in enumerate(attachment_context.chunks):
                source = CitationSource(
                    source_id=f"file_{i}",
                    source_type="file",
                    title=chunk.get('filename', f"File {i+1}"),
                    content=chunk.get('content', ''),
                    url=chunk.get('url'),
                    metadata=chunk.get('metadata', {})
                )
                sources.append(source)

        # Extract web search sources
        if websearch_context and websearch_context.results:
            for i, result in enumerate(websearch_context.results):
                source = CitationSource(
                    source_id=f"web_{i}",
                    source_type="web",
                    title=result.title,
                    content=result.snippet,
                    url=result.link,
                    metadata={
                        'source': result.source,
                        'cached': result.cached
                    }
                )
                sources.append(source)

        logger.info(f"Extracted {len(sources)} total sources for citation")
        return sources

    def _build_citation_prompt(self, query: str, sources: List[CitationSource]) -> str:
        """Build prompt with sources and citation instructions"""

        # Build sources section
        sources_text = []
        for i, source in enumerate(sources, 1):
            source_text = f"[{i}] {source.title}\n"
            source_text += f"Type: {source.source_type}\n"
            if source.url:
                source_text += f"URL: {source.url}\n"
            # Limit content length
            source_text += f"Content: {source.content[:500]}..."
            sources_text.append(source_text)

        combined_sources = "\n\n".join(sources_text)

        citation_prompt = f"""You are an AI assistant that provides accurate responses with proper citations. Use the following sources to answer the user's question.

SOURCES:
{combined_sources}

QUESTION: {query}

INSTRUCTIONS:
- Answer the question using information from the provided sources
- Cite your sources using numbers in square brackets like [1], [2], etc.
- Only cite sources that you actually reference in your response
- Be specific and accurate in your citations
- If information comes from multiple sources, cite all relevant ones
- Provide a clear, well-structured response

Your response should be informative and include proper citations for all claims made."""

        return citation_prompt

    def _generate_direct_response(self, query: str, llm) -> str:
        """Generate direct response without citations"""
        try:
            response = llm.complete(query).text
            return response
        except Exception as e:
            logger.error(f"Direct response generation failed: {e}")
            return "I apologize, but I'm unable to generate a response at this time."

    def _parse_citation_mapping(self, response: str, sources: List[CitationSource]) -> Dict[str, str]:
        """Parse citation numbers from response and map to source IDs"""
        import re

        # Find all citation patterns like [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        citations_found = re.findall(citation_pattern, response)

        source_mapping = {}

        for citation in citations_found:
            citation_num = int(citation)
            if 1 <= citation_num <= len(sources):
                # Map citation number to source ID
                source_id = sources[citation_num - 1].source_id
                source_mapping[f"[{citation}]"] = source_id

        logger.info(f"Parsed {len(source_mapping)} citation mappings")
        return source_mapping
