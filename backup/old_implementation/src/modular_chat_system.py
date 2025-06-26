"""
New Modular Chat System Integration Example

This demonstrates how the new modular system works:
1. Provider selection
2. RAG processing with ID resolution
3. Clean separation of concerns
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

# Import our new modules
from .chat import LLMProviderSelector, RAGProcessor

logger = logging.getLogger(__name__)


class ModularChatSystem:
    """
    New modular chat system that replaces the monolithic enhanced_chat_bot
    Clean separation of concerns and better performance
    """

    def __init__(self):
        # Initialize modules
        self.provider_selector = LLMProviderSelector()
        self.rag_processor = RAGProcessor()
        logger.info("ModularChatSystem initialized")

    async def process_chat_request(self,
                                   messages: List[Dict[str, Any]],
                                   user_id: int,
                                   enable_rag: bool = True,
                                   enable_citations: bool = False,
                                   note_ids: Optional[List[int]] = None,
                                   folder_ids: Optional[List[int]] = None,
                                   conversation_ids: Optional[List[int]] = None,
                                   provider: Optional[str] = None,
                                   model: Optional[str] = None,
                                   temperature: Optional[float] = None,
                                   max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Main chat processing pipeline using new modular architecture

        Flow:
        1. Provider Selection
        2. RAG Processing (if enabled)
        3. Response Generation
        """

        logger.info(f"=== MODULAR CHAT REQUEST ===")
        logger.info(f"User: {user_id}")
        logger.info(f"Enable RAG: {enable_rag}")
        logger.info(f"Enable Citations: {enable_citations}")
        logger.info(f"Provider: {provider}, Model: {model}")

        # Phase 1: Provider Selection
        try:
            provider_enum, llm = self.provider_selector.select_provider_and_model(
                provider, model
            )

            # Configure LLM
            if temperature is not None or max_tokens is not None:
                llm = self.provider_selector.configure_llm(
                    llm, temperature, max_tokens)

            logger.info(f"✅ Selected provider: {provider_enum.value}")

        except Exception as e:
            logger.error(f"❌ Provider selection failed: {e}")
            return {
                "error": f"Provider selection failed: {str(e)}",
                "status": "error"
            }

        # Phase 2: RAG Processing (if enabled)
        rag_context = None
        if enable_rag and user_id:
            try:
                rag_context = self.rag_processor.process_rag_request(
                    messages=messages,
                    user_id=user_id,
                    note_ids=note_ids,
                    folder_ids=folder_ids,
                    conversation_ids=conversation_ids,
                    top_k=20
                )
                logger.info(
                    f"✅ RAG processing completed: {rag_context.total_chunks} chunks")

            except Exception as e:
                logger.error(f"❌ RAG processing failed: {e}")
                # Continue without RAG
                rag_context = None

        # Phase 3: Response Generation
        try:
            if enable_citations and rag_context and rag_context.chunks:
                # Citation mode - use LlamaIndex
                response = await self._generate_with_citations(rag_context, llm)
            else:
                # Direct mode - inject context into prompt
                response = await self._generate_direct_response(rag_context, messages, llm)

            # Add metadata
            response.update({
                "provider": provider_enum.value,
                "model": llm.model if hasattr(llm, 'model') else "unknown",
                "rag_enabled": enable_rag,
                "citations_enabled": enable_citations,
                "context_stats": {
                    "total_chunks": rag_context.total_chunks if rag_context else 0,
                    "used_notes": len(rag_context.used_note_ids) if rag_context else 0,
                    "used_conversations": len(rag_context.used_conversation_ids) if rag_context else 0
                }
            })

            return response

        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            return {
                "error": f"Response generation failed: {str(e)}",
                "status": "error"
            }

    async def _generate_with_citations(self, rag_context, llm) -> Dict[str, Any]:
        """Generate response with citations using LlamaIndex"""
        logger.info("Generating response with citations")

        # Convert chunks to documents
        documents = self.rag_processor.chunks_to_documents(rag_context.chunks)

        if not documents:
            logger.warning(
                "No documents for citation mode, falling back to direct")
            return await self._generate_direct_response(rag_context, [], llm)

        try:
            from llama_index.core import VectorStoreIndex
            from llama_index.core.query_engine import CitationQueryEngine

            # Create vector store index
            index = VectorStoreIndex.from_documents(documents)

            # Create citation query engine
            citation_engine = CitationQueryEngine.from_args(
                index=index,
                similarity_top_k=10
            )

            # Query
            response = citation_engine.query(rag_context.query_used)

            # Extract citations
            citations = []
            if hasattr(response, 'source_nodes'):
                for i, node in enumerate(response.source_nodes):
                    citation = {
                        "id": i + 1,
                        "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "metadata": node.metadata,
                        "score": getattr(node, 'score', 0.0)
                    }
                    citations.append(citation)

            return {
                "content": str(response),
                "citations": citations,
                "status": "success"
            }

        except ImportError:
            logger.error("LlamaIndex not available for citations")
            return await self._generate_direct_response(rag_context, [], llm)

    async def _generate_direct_response(self, rag_context, messages, llm) -> Dict[str, Any]:
        """Generate response with direct context injection"""
        logger.info("Generating direct response")

        # Build prompt
        if rag_context and rag_context.chunks:
            # With context
            context_text = self.rag_processor.chunks_to_context_text(
                rag_context.chunks)

            # Extract user query
            query = rag_context.query_used if rag_context.query_used else "Please help me."

            prompt = f"""You are an AI assistant. Use the following context to answer the user's question.

CONTEXT:
{context_text}

QUESTION: {query}

INSTRUCTIONS:
- Answer based primarily on the provided context
- Be specific and reference relevant information naturally  
- If the context doesn't fully answer the question, say so honestly
- Keep your response helpful and concise

ANSWER:"""
        else:
            # Without context - extract query from messages
            if messages:
                last_message = messages[-1]
                query = last_message.get("content", "") if isinstance(
                    last_message, dict) else str(last_message)
            else:
                query = "Hello! How can I help you?"

            prompt = f"User: {query}\nAssistant:"

        # Generate response
        try:
            response = await llm.acomplete(prompt)
            content = str(response)

            return {
                "content": content,
                "context_used": bool(rag_context and rag_context.chunks),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            return {
                "error": f"LLM completion failed: {str(e)}",
                "status": "error"
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all modules"""
        return {
            "providers": self.provider_selector.get_available_providers(),
            "database": self.rag_processor.health_check(),
            "status": "operational"
        }


# Example usage function
async def example_usage():
    """Example of how to use the new modular system"""

    # Initialize system
    chat_system = ModularChatSystem()

    # Example 1: Simple chat without RAG
    response1 = await chat_system.process_chat_request(
        messages=[{"role": "user", "content": "Hello! What is Python?"}],
        user_id=123,
        enable_rag=False
    )
    print("Simple response:", response1.get("content", "")[:100])

    # Example 2: RAG-enabled chat with specific notes
    response2 = await chat_system.process_chat_request(
        messages=[
            {"role": "user", "content": "What are my notes about machine learning?"}],
        user_id=123,
        enable_rag=True,
        note_ids=[1001, 1002, 1003]  # Specific notes
    )
    print("RAG response:", response2.get("content", "")[:100])

    # Example 3: RAG with citations
    response3 = await chat_system.process_chat_request(
        messages=[
            {"role": "user", "content": "Summarize my research on AI trends"}],
        user_id=123,
        enable_rag=True,
        enable_citations=True,
        folder_ids=[10, 11]  # Specific folders
    )
    print("Citation response:", len(response3.get("citations", [])), "citations")

    # System status
    status = chat_system.get_system_status()
    print("System status:", status["status"])


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
