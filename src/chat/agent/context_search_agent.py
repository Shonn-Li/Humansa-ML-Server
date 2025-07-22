"""
Context Search Agent - Searches user's notes and conversations

This agent performs semantic search across the user's knowledge base (notes and conversations)
and returns results with proper note IDs and conversation IDs for reference.
This is separate from file attachments which are handled by the file search tool.
"""

from typing import Dict, Any, List, Optional
import logging

from .base import BaseAgent
from ..rag.rag_processor import RAGProcessor

logger = logging.getLogger(__name__)


class ContextSearchAgent(BaseAgent):
    """Agent for searching user's notes and conversations context"""
    
    def __init__(self, rag_processor: RAGProcessor):
        super().__init__()
        self.rag_processor = rag_processor
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search user's knowledge base and return structured results"""
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        search_type = router_result.get("search_type", "knowledge_base")
        
        # Extract any specific IDs from the request if provided
        note_ids = request.get("note_ids", None)
        conversation_ids = request.get("conversation_ids", None)
        
        # Use the RAG processor with potential ID constraints
        rag_result = await self.rag_processor.process_rag_request(
            messages=request["messages"],
            user_id=request["user_id"],
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