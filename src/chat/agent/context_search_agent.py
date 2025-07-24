"""
Context Search Agent - Searches user's notes and conversations

This agent performs hybrid search (keyword + semantic) across the user's knowledge base 
(notes and conversations) and returns results with proper note IDs and conversation IDs 
for reference. This is separate from file attachments which are handled by the file search tool.
"""

from typing import Dict, Any, List, Optional
import logging

from .base import BaseAgent
from ..rag.rag_processor import RAGProcessor
from ..search.hybrid_search import HybridSearchEngine
from ..embedding.embedding_provider_selector import EmbeddingProviderSelector
from ..postgres.db_manager import PostgresManager

logger = logging.getLogger(__name__)


class ContextSearchAgent(BaseAgent):
    """Agent for searching user's notes and conversations context"""
    
    def __init__(self, rag_processor: RAGProcessor):
        super().__init__()
        self.rag_processor = rag_processor
        self.postgres = PostgresManager()
        self.hybrid_search = HybridSearchEngine(self.postgres)
        self.embedder = EmbeddingProviderSelector().get_embedding_client()
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search user's knowledge base using hybrid search for better results"""
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        search_type = router_result.get("search_type", "mixed")
        
        # Extract any specific IDs from the request if provided
        note_ids = request.get("note_ids", None)
        conversation_ids = request.get("conversation_ids", None)
        user_id = request["user_id"]
        
        # Generate query embedding for hybrid search
        try:
            query_embedding = self.embedder.get_text_embedding(condensed_query)
        except Exception as e:
            logger.error(f"Failed to generate embedding for hybrid search: {e}")
            query_embedding = None
        
        # Perform hybrid search
        hybrid_results = await self.hybrid_search.hybrid_search(
            query=condensed_query,
            user_id=user_id,
            query_embedding=query_embedding,
            search_type=search_type,
            note_ids=note_ids,
            conversation_ids=conversation_ids,
            top_k=20
        )
        
        # If hybrid search returns results, use them
        if hybrid_results:
            logger.info(f"Hybrid search returned {len(hybrid_results)} results")
            # Convert hybrid results to the expected format
            return self._format_hybrid_results(hybrid_results, condensed_query)
        
        # Fallback to pure RAG if hybrid search fails
        logger.info("Falling back to pure RAG search")
        rag_result = await self.rag_processor.process_rag_request(
            messages=request["messages"],
            user_id=user_id,
            custom_query=condensed_query,
            search_type=search_type,
            note_ids=note_ids,
            conversation_ids=conversation_ids
        )
        
        # Build structured results with proper metadata
        context_parts = []
        sources = []
        
        # Track unique note and conversation IDs
        found_note_ids = set()
        found_conversation_ids = set()
        
        for i, chunk in enumerate(rag_result.chunks[:10]):  # Limit sources for response
            context_parts.append(chunk.chunk_text)
            
            # Determine if this is a note or conversation
            is_conversation = hasattr(chunk, 'is_conversation') and chunk.is_conversation
            
            # Create properly structured source
            source = {
                "chunk_id": chunk.section_id,
                "content": chunk.chunk_text,
                "type": "conversation" if is_conversation else "note",
                "score": getattr(chunk, 'distance', 0.0) if hasattr(chunk, 'distance') else 0.0
            }
            
            # Add ID information
            if is_conversation:
                conversation_id = chunk.type_id
                source["conversation_id"] = conversation_id
                source["title"] = f"Conversation {conversation_id}"
                found_conversation_ids.add(conversation_id)
            else:
                note_id = chunk.type_id
                source["note_id"] = note_id
                source["title"] = f"Note {note_id}"
                found_note_ids.add(note_id)
                
                # Add note-specific metadata if available
                if hasattr(chunk, 'note_title') and chunk.note_title:
                    source["title"] = chunk.note_title
                if hasattr(chunk, 'folder_id'):
                    source["folder_id"] = chunk.folder_id
            
            sources.append(source)
        
        # Include remaining chunks in context without adding to sources
        for chunk in rag_result.chunks[10:]:
            context_parts.append(chunk.chunk_text)
            
            # Still track IDs even for non-source chunks
            if hasattr(chunk, 'is_conversation') and chunk.is_conversation:
                found_conversation_ids.add(chunk.type_id)
            else:
                found_note_ids.add(chunk.type_id)
        
        combined_context = "\n\n".join(context_parts)
        
        return {
            "status": "success",
            "context": combined_context,
            "sources": sources,
            "metadata": {
                "search_type": search_type,
                "context_length": len(combined_context),
                "total_chunks": rag_result.total_chunks,
                "note_ids": sorted(list(found_note_ids)),
                "conversation_ids": sorted(list(found_conversation_ids)),
                "used_note_ids": rag_result.used_note_ids,
                "used_conversation_ids": rag_result.used_conversation_ids
            }
        }
    
    def _format_hybrid_results(self, hybrid_results: List[Any], query: str) -> Dict[str, Any]:
        """Format hybrid search results into the expected response format"""
        context_parts = []
        sources = []
        found_note_ids = set()
        found_conversation_ids = set()
        
        for i, result in enumerate(hybrid_results[:10]):  # Limit sources
            context_parts.append(result.chunk_text)
            
            source = {
                "chunk_id": result.section_id,
                "content": result.chunk_text,
                "type": result.type,
                "hybrid_score": result.hybrid_score,
                "keyword_score": result.keyword_score,
                "vector_score": result.vector_score
            }
            
            if result.type == "conversation":
                source["conversation_id"] = result.type_id
                source["title"] = result.title or f"Conversation {result.type_id}"
                found_conversation_ids.add(result.type_id)
            else:
                source["note_id"] = result.type_id
                source["title"] = result.title or f"Note {result.type_id}"
                found_note_ids.add(result.type_id)
            
            # Add snippet if available
            if result.snippet:
                source["snippet"] = result.snippet
            
            sources.append(source)
        
        # Include remaining results in context without adding to sources
        for result in hybrid_results[10:]:
            context_parts.append(result.chunk_text)
            
            if result.type == "conversation":
                found_conversation_ids.add(result.type_id)
            else:
                found_note_ids.add(result.type_id)
        
        combined_context = "\n\n".join(context_parts)
        
        return {
            "status": "success",
            "context": combined_context,
            "sources": sources,
            "metadata": {
                "search_type": "hybrid",
                "search_query": query,
                "context_length": len(combined_context),
                "total_results": len(hybrid_results),
                "note_ids": sorted(list(found_note_ids)),
                "conversation_ids": sorted(list(found_conversation_ids)),
                "search_method": "keyword+vector"
            }
        }