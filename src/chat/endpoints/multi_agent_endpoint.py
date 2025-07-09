"""
Multi-Agent Response Endpoint v1

This endpoint implements a multi-agent workflow where different specialized agents
handle different aspects of the response generation process:

1. RouterAgent - Routes queries to appropriate agents based on intent
2. RAGAgent - Retrieves relevant context from notes and conversations
3. WebSearchAgent - Performs web searches when needed
4. AttachmentAgent - Processes file attachments (images, PDFs, etc.)
5. ResponseAgent - Generates the final response using gathered context
6. CitationAgent - Adds citations and references to responses

Each agent is autonomous and can be invoked independently or as part of a workflow.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Import existing infrastructure
from ..router.intelligent_router import IntelligentRouter, RouterDecision
from ..rag.rag_processor import RAGProcessor, RAGContext
from ..websearch.web_search_processor import web_search_processor
from ..attachment.file_attachment_manager import file_attachment_manager
from ..provider.llm_provider import LLMProviderSelector
from ..citation.citation_engine import CitationEngine
from ..query.query_transformer import QueryTransformer
from ..config.system_prompts import SystemPromptManager

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Available agent types"""
    ROUTER = "router"
    RAG = "rag"
    WEB_SEARCH = "web_search"
    ATTACHMENT = "attachment"
    RESPONSE = "response"
    CITATION = "citation"


@dataclass
class AgentResult:
    """Result from an agent execution"""
    agent_type: AgentType
    success: bool
    data: Dict[str, Any]
    execution_time: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MultiAgentRequest:
    """Request structure for multi-agent endpoint"""
    messages: List[Dict[str, Any]]
    user_id: int
    model: str = "gpt-4o-mini"
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 4000
    
    # Agent control
    enabled_agents: List[AgentType] = None
    agent_config: Dict[str, Any] = None
    
    # Context parameters
    note_ids: Optional[List[int]] = None
    folder_ids: Optional[List[int]] = None
    conversation_ids: Optional[List[int]] = None
    attachments: Optional[List[str]] = None
    
    # System prompt configuration
    completion_type: str = "system"
    system_prompt: Optional[str] = None
    
    # Response configuration
    enable_citations: bool = True
    generate_title: bool = False


class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.name = f"{agent_type.value}_agent"
        logger.info(f"🤖 {self.name} initialized")
    
    async def execute(self, request: MultiAgentRequest, context: Dict[str, Any]) -> AgentResult:
        """Execute the agent's main function"""
        start_time = time.time()
        
        try:
            logger.info(f"🚀 {self.name} starting execution")
            result_data = await self._execute_impl(request, context)
            execution_time = time.time() - start_time
            
            result = AgentResult(
                agent_type=self.agent_type,
                success=True,
                data=result_data,
                execution_time=execution_time
            )
            
            logger.info(f"✅ {self.name} completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ {self.name} failed: {str(e)}")
            
            return AgentResult(
                agent_type=self.agent_type,
                success=False,
                data={},
                execution_time=execution_time,
                error=str(e)
            )
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implement this method in subclasses"""
        raise NotImplementedError


class RouterAgent(BaseAgent):
    """Agent responsible for routing queries to appropriate tools"""
    
    def __init__(self):
        super().__init__(AgentType.ROUTER)
        self.router = IntelligentRouter()
        self.query_transformer = QueryTransformer()
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route the query and determine which agents should be activated"""
        
        # Get the latest user message
        user_messages = [msg for msg in request.messages if msg["role"] == "user"]
        if not user_messages:
            raise ValueError("No user messages found in request")
        
        query = user_messages[-1]["content"]
        
        # Transform query with conversation context
        condensed_query = await self.query_transformer.transform_query(
            query, request.messages[-3:]  # Use last 3 messages for context
        )
        
        # Route the query
        router_decision = await self.router.route_query(
            condensed_query, str(request.user_id), request.messages[-3:]
        )
        
        # Determine which agents should be enabled based on router decision
        enabled_agents = []
        
        # Always enable response agent
        enabled_agents.append(AgentType.RESPONSE)
        
        # Enable agents based on router decision
        if router_decision.selected_tool in ["knowledge_base_notes", "knowledge_base_conversations", "knowledge_base_full"]:
            enabled_agents.append(AgentType.RAG)
        
        if router_decision.selected_tool == "web_search":
            enabled_agents.append(AgentType.WEB_SEARCH)
        
        if router_decision.selected_tool == "attachments" or request.attachments:
            enabled_agents.append(AgentType.ATTACHMENT)
        
        if request.enable_citations:
            enabled_agents.append(AgentType.CITATION)
        
        return {
            "router_decision": asdict(router_decision),
            "original_query": query,
            "condensed_query": condensed_query,
            "enabled_agents": [agent.value for agent in enabled_agents],
            "search_type": router_decision.search_type if hasattr(router_decision, 'search_type') else "knowledge_base"
        }


class RAGAgent(BaseAgent):
    """Agent responsible for retrieving context from notes and conversations"""
    
    def __init__(self):
        super().__init__(AgentType.RAG)
        self.rag_processor = RAGProcessor()
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context from user's knowledge base"""
        
        # Get search parameters from router context
        router_data = context.get("router_agent", {})
        condensed_query = router_data.get("condensed_query", "")
        search_type = router_data.get("search_type", "knowledge_base")
        
        if not condensed_query:
            # Fallback to original query
            user_messages = [msg for msg in request.messages if msg["role"] == "user"]
            condensed_query = user_messages[-1]["content"] if user_messages else ""
        
        # Process RAG request
        rag_context = await self.rag_processor.process_rag_request(
            user_id=request.user_id,
            query=condensed_query,
            note_ids=request.note_ids,
            folder_ids=request.folder_ids,
            conversation_ids=request.conversation_ids,
            search_type=search_type
        )
        
        return {
            "rag_context": asdict(rag_context),
            "total_chunks": rag_context.total_chunks,
            "used_note_ids": rag_context.used_note_ids,
            "used_conversation_ids": rag_context.used_conversation_ids,
            "query_used": rag_context.query_used
        }


class WebSearchAgent(BaseAgent):
    """Agent responsible for performing web searches"""
    
    def __init__(self):
        super().__init__(AgentType.WEB_SEARCH)
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search for current information"""
        
        # Get search query from router context
        router_data = context.get("router_agent", {})
        search_query = router_data.get("condensed_query", "")
        
        if not search_query:
            # Fallback to original query
            user_messages = [msg for msg in request.messages if msg["role"] == "user"]
            search_query = user_messages[-1]["content"] if user_messages else ""
        
        # Perform web search
        web_context = await web_search_processor.process_web_search(
            query=search_query,
            user_id=request.user_id,
            num_results=5
        )
        
        return {
            "web_context": asdict(web_context) if web_context else None,
            "query_used": search_query,
            "total_results": len(web_context.results) if web_context else 0
        }


class AttachmentAgent(BaseAgent):
    """Agent responsible for processing file attachments"""
    
    def __init__(self):
        super().__init__(AgentType.ATTACHMENT)
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process file attachments and extract content"""
        
        if not request.attachments:
            return {"attachment_context": None, "urls_processed": []}
        
        # Get search query from router context
        router_data = context.get("router_agent", {})
        search_query = router_data.get("condensed_query", "")
        
        if not search_query:
            # Fallback to original query
            user_messages = [msg for msg in request.messages if msg["role"] == "user"]
            search_query = user_messages[-1]["content"] if user_messages else ""
        
        # Process attachments
        attachment_context = await file_attachment_manager.process_attachments(
            attachments=request.attachments,
            user_id=request.user_id,
            query=search_query
        )
        
        return {
            "attachment_context": asdict(attachment_context) if attachment_context else None,
            "urls_processed": request.attachments,
            "query_used": search_query
        }


class ResponseAgent(BaseAgent):
    """Agent responsible for generating the final response"""
    
    def __init__(self):
        super().__init__(AgentType.RESPONSE)
        self.llm_provider = LLMProviderSelector()
        self.system_prompt_manager = SystemPromptManager()
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final response using gathered context"""
        
        # Get LLM instance
        llm = self.llm_provider.get_llm(request.model, request.temperature)
        
        # Build context from all agents
        context_parts = []
        
        # Add RAG context
        if "rag_agent" in context:
            rag_data = context["rag_agent"]
            rag_context = rag_data.get("rag_context")
            if rag_context and rag_context.get("chunks"):
                context_parts.append("## Knowledge Base Context:")
                for chunk in rag_context["chunks"]:
                    context_parts.append(f"- {chunk['content']}")
        
        # Add web search context
        if "web_search_agent" in context:
            web_data = context["web_search_agent"]
            web_context = web_data.get("web_context")
            if web_context and web_context.get("results"):
                context_parts.append("## Web Search Results:")
                for result in web_context["results"]:
                    context_parts.append(f"- {result['title']}: {result['snippet']}")
        
        # Add attachment context
        if "attachment_agent" in context:
            attachment_data = context["attachment_agent"]
            attachment_context = attachment_data.get("attachment_context")
            if attachment_context:
                context_parts.append("## File Attachments:")
                if attachment_context.get("image_chunks"):
                    for chunk in attachment_context["image_chunks"]:
                        context_parts.append(f"- Image: {chunk['content']}")
                if attachment_context.get("chunks"):
                    for chunk in attachment_context["chunks"]:
                        context_parts.append(f"- File: {chunk['content']}")
        
        # Build messages for LLM
        messages = request.messages.copy()
        
        # Add system prompt if needed
        has_system_message = any(msg["role"] == "system" for msg in messages)
        if not has_system_message:
            system_prompt = self.system_prompt_manager.get_system_prompt(
                completion_type=request.completion_type,
                custom_prompt=request.system_prompt
            )
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Add context before the last user message if we have context
        if context_parts:
            context_message = "\n".join(context_parts)
            
            # Find the last user message and add context before it
            last_user_idx = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    last_user_idx = i
                    break
            
            if last_user_idx is not None:
                # Insert context before the last user message
                messages.insert(last_user_idx, {
                    "role": "system",
                    "content": f"Here is relevant context for the user's query:\n\n{context_message}"
                })
        
        # Generate response
        if request.stream:
            # For streaming, we would need to implement streaming logic here
            # For now, let's do a simple non-streaming response
            pass
        
        # Convert messages to LlamaIndex format
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles to MessageRole enum
            if role == "system":
                llamaindex_role = MessageRole.SYSTEM
            elif role == "assistant":
                llamaindex_role = MessageRole.ASSISTANT
            else:  # user or any other role
                llamaindex_role = MessageRole.USER

            chat_messages.append(ChatMessage(
                role=llamaindex_role,
                content=content
            ))
        
        # Generate response
        response = await llm.achat(chat_messages)
        
        return {
            "response": response.message.content,
            "model_used": request.model,
            "context_used": len(context_parts) > 0,
            "total_messages": len(messages),
            "context_summary": {
                "rag_chunks": context.get("rag_agent", {}).get("total_chunks", 0),
                "web_results": context.get("web_search_agent", {}).get("total_results", 0),
                "attachments": len(request.attachments) if request.attachments else 0
            }
        }


class CitationAgent(BaseAgent):
    """Agent responsible for adding citations to responses"""
    
    def __init__(self):
        super().__init__(AgentType.CITATION)
        self.citation_engine = CitationEngine()
    
    async def _execute_impl(self, request: MultiAgentRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add citations to the response"""
        
        # Get response from ResponseAgent
        response_data = context.get("response_agent", {})
        response_text = response_data.get("response", "")
        
        if not response_text:
            return {"cited_response": "", "citations": []}
        
        # Build source data from other agents
        sources = []
        
        # Add RAG sources
        if "rag_agent" in context:
            rag_data = context["rag_agent"]
            rag_context = rag_data.get("rag_context")
            if rag_context and rag_context.get("chunks"):
                for chunk in rag_context["chunks"]:
                    sources.append({
                        "id": chunk.get("id", ""),
                        "content": chunk.get("content", ""),
                        "type": chunk.get("type", "note"),
                        "metadata": chunk.get("metadata", {})
                    })
        
        # Add web search sources
        if "web_search_agent" in context:
            web_data = context["web_search_agent"]
            web_context = web_data.get("web_context")
            if web_context and web_context.get("results"):
                for result in web_context["results"]:
                    sources.append({
                        "id": result.get("url", ""),
                        "content": result.get("snippet", ""),
                        "type": "web",
                        "metadata": {
                            "title": result.get("title", ""),
                            "url": result.get("url", "")
                        }
                    })
        
        # Process citations
        cited_response, citations = await self.citation_engine.process_citations(
            response_text, sources
        )
        
        return {
            "cited_response": cited_response,
            "citations": citations,
            "total_citations": len(citations)
        }


class MultiAgentOrchestrator:
    """Orchestrates the execution of multiple agents"""
    
    def __init__(self):
        self.agents = {
            AgentType.ROUTER: RouterAgent(),
            AgentType.RAG: RAGAgent(),
            AgentType.WEB_SEARCH: WebSearchAgent(),
            AgentType.ATTACHMENT: AttachmentAgent(),
            AgentType.RESPONSE: ResponseAgent(),
            AgentType.CITATION: CitationAgent()
        }
        logger.info("🎼 MultiAgentOrchestrator initialized")
    
    async def execute_workflow(self, request: MultiAgentRequest) -> Dict[str, Any]:
        """Execute the multi-agent workflow"""
        
        workflow_start = time.time()
        results = {}
        context = {}
        
        logger.info(f"🚀 Starting multi-agent workflow for user {request.user_id}")
        
        # Phase 1: Router Agent (always first)
        router_result = await self.agents[AgentType.ROUTER].execute(request, context)
        results["router_agent"] = asdict(router_result)
        
        if router_result.success:
            context["router_agent"] = router_result.data
            enabled_agents = [AgentType(agent) for agent in router_result.data.get("enabled_agents", [])]
        else:
            # Fallback to all agents if router fails
            enabled_agents = [AgentType.RAG, AgentType.WEB_SEARCH, AgentType.ATTACHMENT, AgentType.RESPONSE]
            if request.enable_citations:
                enabled_agents.append(AgentType.CITATION)
        
        logger.info(f"🎯 Enabled agents: {[agent.value for agent in enabled_agents]}")
        
        # Phase 2: Parallel execution of context agents
        context_agents = []
        for agent_type in enabled_agents:
            if agent_type in [AgentType.RAG, AgentType.WEB_SEARCH, AgentType.ATTACHMENT]:
                context_agents.append(agent_type)
        
        if context_agents:
            logger.info(f"⚡ Executing context agents in parallel: {[agent.value for agent in context_agents]}")
            
            # Execute context agents in parallel
            context_tasks = []
            for agent_type in context_agents:
                task = self.agents[agent_type].execute(request, context)
                context_tasks.append((agent_type, task))
            
            # Wait for all context agents to complete
            for agent_type, task in context_tasks:
                result = await task
                results[f"{agent_type.value}_agent"] = asdict(result)
                if result.success:
                    context[f"{agent_type.value}_agent"] = result.data
        
        # Phase 3: Response Agent (always required)
        if AgentType.RESPONSE in enabled_agents:
            response_result = await self.agents[AgentType.RESPONSE].execute(request, context)
            results["response_agent"] = asdict(response_result)
            
            if response_result.success:
                context["response_agent"] = response_result.data
        
        # Phase 4: Citation Agent (if enabled)
        if AgentType.CITATION in enabled_agents:
            citation_result = await self.agents[AgentType.CITATION].execute(request, context)
            results["citation_agent"] = asdict(citation_result)
        
        # Calculate total workflow time
        workflow_time = time.time() - workflow_start
        
        # Build final response
        response_data = context.get("response_agent", {})
        citation_data = context.get("citation_agent", {})
        
        final_response = {
            "response": citation_data.get("cited_response") or response_data.get("response", ""),
            "model": request.model,
            "usage": {
                "workflow_time": workflow_time,
                "enabled_agents": [agent.value for agent in enabled_agents],
                "total_agents": len(enabled_agents)
            },
            "metadata": {
                "agent_results": results,
                "context_summary": response_data.get("context_summary", {}),
                "citations": citation_data.get("citations", [])
            }
        }
        
        logger.info(f"✅ Multi-agent workflow completed in {workflow_time:.2f}s")
        return final_response


# Global orchestrator instance
orchestrator = MultiAgentOrchestrator()


async def handle_multi_agent_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main handler for multi-agent requests"""
    
    try:
        # Parse request
        request = MultiAgentRequest(
            messages=request_data.get("messages", []),
            user_id=request_data.get("user_id", 0),
            model=request_data.get("model", "gpt-4o-mini"),
            stream=request_data.get("stream", False),
            temperature=request_data.get("temperature", 0.7),
            max_tokens=request_data.get("max_tokens", 4000),
            enabled_agents=request_data.get("enabled_agents"),
            agent_config=request_data.get("agent_config", {}),
            note_ids=request_data.get("note_ids"),
            folder_ids=request_data.get("folder_ids"),
            conversation_ids=request_data.get("conversation_ids"),
            attachments=request_data.get("attachments"),
            completion_type=request_data.get("completion_type", "system"),
            system_prompt=request_data.get("system_prompt"),
            enable_citations=request_data.get("enable_citations", True),
            generate_title=request_data.get("generate_title", False)
        )
        
        # Execute workflow
        result = await orchestrator.execute_workflow(request)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Multi-agent request failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "type": "multi_agent_error"
        }
