from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import BaseTool
from llama_index.core.llms import LLM
from llama_index.core.memory import BaseMemory
from llama_index.core.callbacks import CallbackManager
import logging

logger = logging.getLogger(__name__)


class BaseHumansaAgent(ABC):
    """Abstract base class for all Humansa medical agents."""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        description: str,
        llm: LLM,
        tools: List[BaseTool],
        memory: Optional[BaseMemory] = None,
        callback_manager: Optional[CallbackManager] = None,
        verbose: bool = False
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.callback_manager = callback_manager
        self.verbose = verbose
        
        # Initialize the ReAct agent
        self.agent = self._create_agent()
        
    def _create_agent(self) -> ReActAgent:
        """Create the underlying ReAct agent using new API (llama-index 0.13.0)."""
        return ReActAgent(
            name=self.agent_name,
            description=self.description,
            tools=self.tools,
            llm=self.llm,
            memory=self.memory,
            callback_manager=self.callback_manager,
            verbose=self.verbose
        )
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt specific to this agent type."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return a list of capabilities this agent provides."""
        pass
    
    @abstractmethod
    def should_handle_query(self, query: str, context: Dict[str, Any]) -> float:
        """
        Determine if this agent should handle the query.
        Returns a confidence score between 0 and 1.
        """
        pass
    
    async def process_query(
        self,
        query: str,
        context: Dict[str, Any],
        stream: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """Process a query and yield results."""
        # TODO: update_prompts might not be available in new API - need to set system prompt differently
        # For now, incorporate system prompt in the query
        system_prompt = self.get_system_prompt()
        
        # Add context to query if provided
        enhanced_query = self._enhance_query_with_context(query, context)
        
        # Prepend system prompt to query
        enhanced_query = f"{system_prompt}\n\n{enhanced_query}"
        
        if stream:
            async for chunk in self._stream_response(enhanced_query):
                yield chunk
        else:
            # Use run method for new API
            response_handler = self.agent.run(enhanced_query)
            result = await response_handler
            
            # Extract response text
            if hasattr(result, 'response'):
                response_text = str(result.response)
            elif hasattr(result, 'output'):
                response_text = str(result.output)
            else:
                response_text = str(result)
            
            yield {
                "agent_id": self.agent_id,
                "response": response_text,
                "source_nodes": []
            }
    
    def _enhance_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance the query with relevant context."""
        enhanced = query
        
        if context.get("patient_profile"):
            enhanced = f"Patient Profile: {context['patient_profile']}\n\n{enhanced}"
            
        if context.get("conversation_history"):
            enhanced = f"Previous Context: {context['conversation_history']}\n\n{enhanced}"
            
        return enhanced
    
    async def _stream_response(self, query: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream the response from the agent."""
        # Use run method for new API
        response_handler = self.agent.run(query)
        
        # For now, just get the complete result
        # TODO: Figure out proper streaming with new API
        result = await response_handler
        
        # Extract response text
        if hasattr(result, 'response'):
            response_text = str(result.response)
        elif hasattr(result, 'output'):
            response_text = str(result.output)
        else:
            response_text = str(result)
        
        # Yield as a single chunk for now
        yield {
            "agent_id": self.agent_id,
            "chunk": response_text,
            "type": "content"
        }
    
    def add_tool(self, tool: BaseTool) -> None:
        """Add a new tool to the agent."""
        self.tools.append(tool)
        self.agent = self._create_agent()  # Recreate agent with new tools
        
    def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the agent."""
        self.tools = [t for t in self.tools if t.metadata.name != tool_name]
        self.agent = self._create_agent()  # Recreate agent with updated tools
        
    def get_tool_names(self) -> List[str]:
        """Get names of all tools available to this agent."""
        return [tool.metadata.name for tool in self.tools]