"""
RAG Agent - Retrieval-Augmented Generation Agent

This agent retrieves relevant context from the knowledge base (notes and conversations)
to augment the response generation with user-specific information.
"""

from typing import Dict, Any
import logging

from .base import BaseAgent
from ..rag.rag_processor import RAGProcessor

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """Agent for retrieving context from knowledge base"""
    
    def __init__(self, rag_processor: RAGProcessor):
        super().__init__()
        self.rag_processor = rag_processor
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context from notes and conversations"""
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        search_type = router_result.get("search_type", "knowledge_base")
        
        # Use the RAG processor
        rag_result = await self.rag_processor.process_rag_request(
            messages=request["messages"],
            user_id=request["user_id"],
            custom_query=condensed_query,
            search_type=search_type
        )
        
        # Build context from chunks
        context_parts = []
        for chunk in rag_result.chunks:
            context_parts.append(chunk.chunk_text)
        
        combined_context = "\n\n".join(context_parts)
        
        return {
            "status": "success",
            "context": combined_context,
            "sources": [{"chunk_id": chunk.section_id, "content": chunk.chunk_text[:100] + "..."} for chunk in rag_result.chunks[:5]],
            "metadata": {
                "search_type": search_type,
                "context_length": len(combined_context),
                "total_chunks": rag_result.total_chunks,
                "used_note_ids": rag_result.used_note_ids,
                "used_conversation_ids": rag_result.used_conversation_ids
            }
        }