"""
Response Agent - Generates the final response

This agent takes all the context from other agents and generates
the final response to the user. It supports both streaming and
non-streaming modes.
"""

from typing import Dict, Any, List, AsyncGenerator, Tuple
import logging
import re
import os
import json
from datetime import datetime
from decimal import Decimal

from .base import BaseAgent
from ..provider.llm_provider import LLMProviderSelector
from ..config.system_prompts import SystemPromptManager
from ..citation.citation_position_tracker import citation_position_tracker
from llama_index.core.llms import ChatMessage

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types and WebSearchResult objects"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        # Handle WebSearchResult objects
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super(DecimalEncoder, self).default(obj)


class ResponseAgent(BaseAgent):
    """Enhanced agent for generating responses with streaming support"""
    
    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.llm_provider_manager = llm_provider_manager
        self.system_prompt_manager = SystemPromptManager()
        self.supports_streaming = True
        self.citation_pattern = re.compile(r'\[(\d+)\]')
        
        # Create debug logs directory
        self.debug_dir = "debug_logs"
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def _save_debug_context(self, context: Dict[str, Any], combined_context: str, sources: List[Dict[str, Any]], 
                           user_id: int, conversation_id: int, request: Dict[str, Any], messages: List[ChatMessage] = None) -> str:
        """Save context to timestamped file for debugging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.debug_dir}/context_{user_id}_{conversation_id}_{timestamp}.json"
        
        debug_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "request": {
                "messages": request.get("messages", []),
                "model": request.get("model"),
                "enable_rag": request.get("enable_rag"),
                "enable_citations": request.get("enable_citations"),
                "enable_web_search": request.get("enable_web_search")
            },
            "context_agents": list(context.keys()),
            "combined_context_length": len(combined_context),
            "combined_context_preview": combined_context[:1000] + "..." if len(combined_context) > 1000 else combined_context,
            "sources": sources,
            "sources_count": len(sources),
            "context_search_found": "context_search_agent" in context,
            "web_search_found": "web_search_agent" in context,
            "attachment_found": "attachment_agent" in context,
            "full_context": {
                "context_search": context.get("context_search_agent", {}),
                "web_search": context.get("web_search_agent", {}),
                "attachment": context.get("attachment_agent", {}),
                "router": context.get("router_agent", {})
            },
            "combined_context_full": combined_context,
            "llamaindex_messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "content_length": len(msg.content)
                } for msg in (messages or [])
            ] if messages else None
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
            logger.info(f"💾 Debug context saved to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save debug context: {e}")
        
        return filename
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final response with optional citations (non-streaming)"""
        
        # Build combined context and sources
        combined_context, sources = self._build_combined_context_with_sources(context)
        
        # Get user and conversation IDs
        user_id = request.get("user_id", 0)
        conversation_id = request.get("conversation_id", 0)
        
        # Check if citations should be enabled
        enable_citations = self._should_enable_citations(request, sources)
        
        # Prepare messages
        messages = self._prepare_messages(request, combined_context, sources, enable_citations)
        
        # Save debug context with messages
        debug_file = self._save_debug_context(context, combined_context, sources, user_id, conversation_id, request, messages)
        
        # Log critical information
        logger.info(f"🎯 RESPONSE AGENT - User {user_id}, Conversation {conversation_id}")
        logger.info(f"📊 Context Summary:")
        logger.info(f"  - Combined context length: {len(combined_context)} chars")
        logger.info(f"  - Sources found: {len(sources)}")
        logger.info(f"  - Context agents: {list(context.keys())}")
        logger.info(f"  - Has RAG context: {'context_search_agent' in context}")
        logger.info(f"  - Has web search: {'web_search_agent' in context}")
        logger.info(f"  - Debug log: {debug_file}")
        
        # Validate context
        if not combined_context and request.get("enable_rag", False):
            logger.warning("⚠️ WARNING: RAG was enabled but no context found!")
            logger.warning(f"  - Context search result: {context.get('context_search_agent', {}).get('status', 'N/A')}")
            if 'context_search_agent' in context:
                search_meta = context['context_search_agent'].get('metadata', {})
                logger.warning(f"  - Total chunks searched: {search_meta.get('total_chunks', 0)}")
                logger.warning(f"  - Note IDs searched: {search_meta.get('note_ids', [])}")
        
        # Get LLM provider
        model = request.get("model", "gpt-4.1-nano")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Generate response
        response = await llm.achat(messages)
        response_text = response.message.content
        
        # Extract citation annotations if citations are enabled
        annotations = []
        if enable_citations and sources:
            _, annotations = citation_position_tracker.extract_citations_with_positions(response_text, sources)
        
        return {
            "status": "success",
            "response": response_text,
            "annotations": [ann.to_dict() for ann in annotations],
            "sources": sources if enable_citations else [],
            "metadata": {
                "model": request.get("model", "gpt-4.1-nano"),
                "context_used": bool(combined_context),
                "citations_enabled": enable_citations
            }
        }
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate the response with streaming and citations"""
        
        # Build combined context and sources
        combined_context, sources = self._build_combined_context_with_sources(context)
        
        # Get user and conversation IDs
        user_id = request.get("user_id", 0)
        conversation_id = request.get("conversation_id", 0)
        
        # Check if citations should be enabled
        enable_citations = self._should_enable_citations(request, sources)
        
        # Prepare messages
        messages = self._prepare_messages(request, combined_context, sources, enable_citations)
        
        # Save debug context with messages
        debug_file = self._save_debug_context(context, combined_context, sources, user_id, conversation_id, request, messages)
        
        # Log critical information
        logger.info(f"🎯 RESPONSE AGENT STREAM - User {user_id}, Conversation {conversation_id}")
        logger.info(f"📊 Context Summary:")
        logger.info(f"  - Combined context length: {len(combined_context)} chars")
        logger.info(f"  - Sources found: {len(sources)}")
        logger.info(f"  - Context agents: {list(context.keys())}")
        logger.info(f"  - Has RAG context: {'context_search_agent' in context}")
        logger.info(f"  - Has web search: {'web_search_agent' in context}")
        logger.info(f"  - Debug log: {debug_file}")
        
        # Validate context
        if not combined_context and request.get("enable_rag", False):
            logger.warning("⚠️ WARNING: RAG was enabled but no context found!")
            logger.warning(f"  - Context search result: {context.get('context_search_agent', {}).get('status', 'N/A')}")
            if 'context_search_agent' in context:
                search_meta = context['context_search_agent'].get('metadata', {})
                logger.warning(f"  - Total chunks searched: {search_meta.get('total_chunks', 0)}")
                logger.warning(f"  - Note IDs searched: {search_meta.get('note_ids', [])}")
        
        # Get LLM provider
        model = request.get("model", "gpt-4.1-nano")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Stream response
        try:
            stream = await llm.astream_chat(messages)
            
            # Accumulate response for citation tracking
            accumulated_response = ""
            
            # Stream the response chunks
            async for chunk in stream:
                # Handle regular content delta
                if chunk.delta:
                    accumulated_response += chunk.delta
                    yield {
                        "type": "response_chunk",
                        "content": chunk.delta,
                        "metadata": {"agent": "response"}
                    }
                
                # Handle DeepSeek reasoning content
                # Check if chunk has raw attribute (for llama-index chunks)
                if hasattr(chunk, 'raw') and chunk.raw:
                    raw_chunk = chunk.raw
                    # Check for DeepSeek reasoning in choices[0].delta
                    if hasattr(raw_chunk, 'choices') and raw_chunk.choices:
                        choice = raw_chunk.choices[0]
                        if hasattr(choice, 'delta') and choice.delta:
                            delta = choice.delta
                            # Check for reasoning_content field (DeepSeek R1 specific)
                            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                                logger.info(f"🧠 DeepSeek reasoning chunk detected: {delta.reasoning_content[:50]}...")
                                yield {
                                    "type": "reasoning_chunk", 
                                    "content": delta.reasoning_content,
                                    "metadata": {"agent": "response", "model": model}
                                }
            
            # Extract citation annotations if enabled
            if enable_citations and sources:
                _, annotations = citation_position_tracker.extract_citations_with_positions(accumulated_response, sources)
                
                logger.info(f"📚 Extracted {len(annotations)} annotations from response")
                
                # Yield annotation data
                yield {
                    "type": "annotations",
                    "annotations": [ann.to_dict() for ann in annotations],
                    "sources": sources
                }
            
            # Final result
            yield {
                "type": "success",
                "status": "success",
                "response": accumulated_response,
                "metadata": {
                    "model": request.get("model", "gpt-4.1-nano"),
                    "context_used": bool(combined_context),
                    "citations_enabled": enable_citations,
                    "source_count": len(sources)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in response streaming: {e}")
            yield {"type": "error", "error": str(e)}
    
    def _build_combined_context_with_sources(self, context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """Build combined context and extract sources from all agents"""
        context_parts = []
        all_sources = []
        source_counter = 1
        
        # Attachment context and sources
        if "attachment_agent" in context:
            attachment_data = context["attachment_agent"]
            attachment_context = attachment_data.get("context", "")
            
            # Add attachment context
            if attachment_context:
                context_parts.append(f"[{source_counter}] Attachment Content:\n{attachment_context}")
                source_counter += 1
            
            # Add attachment sources
            attachment_sources = attachment_data.get("sources", [])
            for source in attachment_sources:
                all_sources.append({
                    "source_id": f"attachment_{source_counter}",
                    "type": "attachment",
                    "title": source.get("title", "User Attachment"),
                    "content": attachment_context[:500] if attachment_context else "Attachment content",
                    "url": source.get("url", ""),
                    "metadata": {
                        "filename": source.get("filename", "attachment"),
                        "file_type": source.get("file_type", "unknown"),
                        "file_id": source.get("file_id")
                    }
                })
        
        # Context search sources (notes and conversations)
        if "context_search_agent" in context:
            context_sources = context["context_search_agent"].get("sources", [])
            for source in context_sources:
                # Handle both direct content and nested chunks structure
                source_content = ""
                
                # Check if source has direct content field (old format)
                if "content" in source and source["content"]:
                    source_content = source["content"][:500]
                # Check if source has chunks field (agentic processor format)
                elif "chunks" in source and isinstance(source["chunks"], list) and source["chunks"]:
                    # Combine content from all chunks
                    chunk_texts = []
                    for chunk in source["chunks"][:3]:  # Limit to first 3 chunks per source
                        if isinstance(chunk, dict) and "content" in chunk:
                            chunk_texts.append(chunk["content"])
                    source_content = "\n".join(chunk_texts)[:500]
                
                # Only add non-empty content
                if source_content:
                    # Format based on source type
                    source_type = source.get("type", "note")
                    source_title = source.get("title", "")
                    
                    if source_type == "note":
                        context_header = f"[{source_counter}] Note: {source_title}"
                    elif source_type == "conversation":
                        context_header = f"[{source_counter}] Conversation: {source_title}"
                    else:
                        context_header = f"[{source_counter}] {source_type.capitalize()}: {source_title}"
                    
                    context_parts.append(f"{context_header}\n{source_content}")
                
                # Add context search source with proper metadata
                source_type = source.get("type", "note")
                source_id = source.get("type_id") or source.get("note_id") or source.get("conversation_id")
                
                all_sources.append({
                    "source_id": f"context_{source_counter}",
                    "type": "context_search",
                    "title": source.get("title", f"{source_type.capitalize()} {source_counter}"),
                    "content": source_content,
                    "url": f"youwo://{source_type}/{source_id}" if source_id else "",
                    "metadata": {
                        "note_id": source.get("note_id") or (source.get("type_id") if source_type == "note" else None),
                        "conversation_id": source.get("conversation_id") or (source.get("type_id") if source_type == "conversation" else None),
                        "node_id": source.get("node_id"),
                        "chunk_id": source.get("chunk_id") or (source["chunks"][0].get("section_id") if "chunks" in source and source["chunks"] else None),
                        "score": source.get("score", source["chunks"][0].get("score", 0.0) if "chunks" in source and source["chunks"] else 0.0),
                        "type": source_type
                    }
                })
                source_counter += 1
        
        # Web search context and sources
        if "web_search_agent" in context:
            web_results = context["web_search_agent"].get("results", [])
            for result in web_results:
                # Format web result
                snippet = result.get("snippet", "") if isinstance(result, dict) else getattr(result, "snippet", "")
                title = result.get("title", "") if isinstance(result, dict) else getattr(result, "title", "")
                url = result.get("link", result.get("url", "")) if isinstance(result, dict) else getattr(result, "link", "")
                
                context_parts.append(f"[{source_counter}] {title}:\n{snippet}")
                
                # Add web source
                all_sources.append({
                    "source_id": f"web_{source_counter}",
                    "type": "web_search",
                    "title": title,
                    "content": snippet,
                    "url": url,
                    "metadata": {
                        "search_engine": "google"
                    }
                })
                source_counter += 1
        
        combined_context = "\n\n".join(context_parts)
        return combined_context, all_sources
    
    def _prepare_messages(self, request: Dict[str, Any], combined_context: str, sources: List[Dict[str, Any]], enable_citations: bool) -> List[ChatMessage]:
        """Prepare messages for LLM with citation instructions"""
        messages = []
        
        # System message
        system_prompt = self.system_prompt_manager.get_system_prompt(
            request.get("model", "gpt-4.1-nano")
        )
        messages.append(ChatMessage(role="system", content=system_prompt))
        
        # Add conversation history EXCEPT the last user message
        for msg in request["messages"][:-1]:
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
        
        # Get the last user message
        last_user_message = request["messages"][-1]["content"] if request["messages"] else ""
        
        # Construct enhanced user message with context
        if combined_context:
            # Build the user message with context
            enhanced_user_message = f"Context from your notes and documents:\n\n{combined_context}"
            
            # Add citation instructions if enabled and we have sources
            if enable_citations and sources:
                enhanced_user_message += """\n\nCITATION INSTRUCTIONS:
- Cite sources using numbered brackets like [1], [2], etc.
- Place citations immediately after relevant statements
- You can cite multiple sources like [1, 3]
- Only cite sources that directly support your statement
- Every factual claim from the provided sources must have a citation

"""
            
            # Add the actual user question
            enhanced_user_message += f"\nUser Question: {last_user_message}"
            
            # Add as single user message
            messages.append(ChatMessage(role="user", content=enhanced_user_message))
        else:
            # No context, just add the user message as-is
            messages.append(ChatMessage(role="user", content=last_user_message))
        
        # Log the exact messages being sent to LlamaIndex
        logger.info("📝 MESSAGES SENT TO LLAMAINDEX:")
        for i, msg in enumerate(messages):
            logger.info(f"  Message {i+1} ({msg.role}):")
            # Log first 200 chars of each message
            content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            logger.info(f"    {content_preview}")
        logger.info(f"  Total messages: {len(messages)}")
        logger.info(f"  Total chars: {sum(len(m.content) for m in messages)}")
        
        return messages
    
    def _should_enable_citations(self, request: Dict[str, Any], sources: List[Dict[str, Any]]) -> bool:
        """Determine if citations should be enabled"""
        # Check explicit setting first
        if "enable_citations" in request:
            return request["enable_citations"]
        
        # Enable by default if we have any sources
        return len(sources) > 0