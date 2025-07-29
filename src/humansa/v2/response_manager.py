"""
Response Manager for HUMANSA V2
Implements OpenAI Responses API-style response tracking with forking support
"""

import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class Response:
    """Represents a single response in a conversation"""
    id: str
    conversation_id: str
    user_id: str
    model: str
    created: int
    input: str
    output: List[Dict[str, Any]]
    previous_response_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "object": "response",
            "created": self.created,
            "model": self.model,
            "conversation_id": self.conversation_id,
            "previous_response_id": self.previous_response_id,
            "input": self.input,
            "output": self.output,
            "metadata": self.metadata,
            "tools_used": self.tools_used,
            "usage": self.token_usage
        }


class ResponseManager:
    """
    Manages responses with OpenAI-style response IDs and conversation forking
    """
    
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.responses: Dict[str, Response] = {}
        self.response_chains: Dict[str, List[str]] = {}  # conversation_id -> [response_ids]
        self.response_tree: Dict[str, List[str]] = {}  # response_id -> [child_response_ids]
        
    def create_response(
        self,
        user_id: str,
        model: str,
        input_text: str,
        output: List[Dict[str, Any]],
        previous_response_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tools_used: Optional[List[str]] = None,
        token_usage: Optional[Dict[str, int]] = None
    ) -> Response:
        """Create a new response, optionally continuing from a previous response"""
        
        # Generate response ID
        response_id = f"resp_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        
        # Handle conversation creation or continuation
        if previous_response_id:
            # Continue or fork from previous response
            if previous_response_id not in self.responses:
                raise ValueError(f"Previous response {previous_response_id} not found")
            
            previous_response = self.responses[previous_response_id]
            conversation_id = previous_response.conversation_id
            user_id = previous_response.user_id
            
            # Check if this is a fork (branching conversation)
            is_fork = self._is_fork(previous_response_id, conversation_id)
            if is_fork:
                logger.info(f"Forking conversation from response {previous_response_id}")
                # Track fork in metadata
                if metadata is None:
                    metadata = {}
                metadata["forked_from"] = previous_response_id
        else:
            # New conversation
            if not conversation_id:
                conversation_id = self.conversation_manager.create_conversation(user_id)
            elif conversation_id not in self.conversation_manager.conversations:
                # Create conversation with specific ID
                self.conversation_manager.create_conversation(user_id, conversation_id)
        
        # Create response object
        response = Response(
            id=response_id,
            conversation_id=conversation_id,
            user_id=user_id,
            model=model,
            created=int(datetime.now().timestamp()),
            input=input_text,
            output=output,
            previous_response_id=previous_response_id,
            metadata=metadata or {},
            tools_used=tools_used or [],
            token_usage=token_usage or {}
        )
        
        # Store response
        self.responses[response_id] = response
        
        # Update response chains
        if conversation_id not in self.response_chains:
            self.response_chains[conversation_id] = []
        self.response_chains[conversation_id].append(response_id)
        
        # Update response tree
        if previous_response_id:
            if previous_response_id not in self.response_tree:
                self.response_tree[previous_response_id] = []
            self.response_tree[previous_response_id].append(response_id)
        
        # Add messages to conversation manager
        self.conversation_manager.add_message(conversation_id, "user", input_text)
        output_text = self._extract_text_from_output(output)
        self.conversation_manager.add_message(conversation_id, "assistant", output_text)
        
        logger.info(f"Created response {response_id} for conversation {conversation_id}")
        return response
    
    def get_response(self, response_id: str) -> Optional[Response]:
        """Retrieve a response by ID"""
        return self.responses.get(response_id)
    
    def get_response_chain(self, response_id: str) -> List[Response]:
        """Get the full chain of responses leading to this response"""
        chain = []
        current_id = response_id
        
        while current_id:
            if current_id not in self.responses:
                break
            response = self.responses[current_id]
            chain.insert(0, response)  # Insert at beginning to maintain order
            current_id = response.previous_response_id
            
        return chain
    
    def get_conversation_tree(self, conversation_id: str) -> Dict[str, Any]:
        """Get the full conversation tree showing all branches"""
        if conversation_id not in self.response_chains:
            return {}
            
        # Find root responses (no previous_response_id)
        roots = [
            resp_id for resp_id in self.response_chains[conversation_id]
            if not self.responses[resp_id].previous_response_id
        ]
        
        def build_tree_node(response_id: str) -> Dict[str, Any]:
            response = self.responses[response_id]
            children = self.response_tree.get(response_id, [])
            
            node = {
                "id": response_id,
                "input": response.input,
                "output": self._extract_text_from_output(response.output),
                "created": response.created,
                "children": [build_tree_node(child_id) for child_id in children]
            }
            
            return node
        
        tree = {
            "conversation_id": conversation_id,
            "roots": [build_tree_node(root_id) for root_id in roots]
        }
        
        return tree
    
    def get_context_for_response(
        self,
        previous_response_id: Optional[str],
        include_summary: bool = True
    ) -> Tuple[List[Dict[str, str]], int]:
        """Get optimized context for creating a new response"""
        
        if not previous_response_id:
            return [], 0
            
        # Get the response chain
        chain = self.get_response_chain(previous_response_id)
        if not chain:
            return [], 0
            
        # Extract conversation ID
        conversation_id = chain[0].conversation_id
        
        # Build messages from response chain
        messages = []
        for response in chain:
            messages.append({
                "role": "user",
                "content": response.input
            })
            messages.append({
                "role": "assistant",
                "content": self._extract_text_from_output(response.output)
            })
        
        # Use conversation manager's context window optimization
        return self.conversation_manager.get_context_window(
            conversation_id,
            include_summary=include_summary
        )
    
    def _is_fork(self, previous_response_id: str, conversation_id: str) -> bool:
        """Check if this creates a fork in the conversation"""
        # Check if previous response already has children
        return previous_response_id in self.response_tree and \
               len(self.response_tree[previous_response_id]) > 0
    
    def _extract_text_from_output(self, output: List[Dict[str, Any]]) -> str:
        """Extract text content from output array"""
        text_parts = []
        for item in output:
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts)
    
    def cleanup_old_responses(self, max_age_hours: int = 24):
        """Remove old responses to prevent memory bloat"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_remove = []
        
        for resp_id, response in self.responses.items():
            if response.created < cutoff:
                to_remove.append(resp_id)
        
        for resp_id in to_remove:
            # Remove from responses
            response = self.responses[resp_id]
            del self.responses[resp_id]
            
            # Remove from chains
            if response.conversation_id in self.response_chains:
                self.response_chains[response.conversation_id].remove(resp_id)
            
            # Remove from tree
            if response.previous_response_id in self.response_tree:
                self.response_tree[response.previous_response_id].remove(resp_id)
            
            # Remove as parent if it has children
            if resp_id in self.response_tree:
                del self.response_tree[resp_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old responses")
    
    def get_response_statistics(self, conversation_id: str) -> Dict[str, Any]:
        """Get statistics about responses in a conversation"""
        if conversation_id not in self.response_chains:
            return {}
        
        response_ids = self.response_chains[conversation_id]
        total_responses = len(response_ids)
        
        # Count forks
        fork_count = 0
        for resp_id in response_ids:
            if resp_id in self.response_tree and len(self.response_tree[resp_id]) > 1:
                fork_count += 1
        
        # Calculate token usage
        total_tokens = 0
        for resp_id in response_ids:
            response = self.responses[resp_id]
            if response.token_usage:
                total_tokens += response.token_usage.get("total_tokens", 0)
        
        # Find most used tools
        tool_usage = {}
        for resp_id in response_ids:
            response = self.responses[resp_id]
            for tool in response.tools_used:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        return {
            "total_responses": total_responses,
            "fork_count": fork_count,
            "total_tokens": total_tokens,
            "average_tokens_per_response": total_tokens / total_responses if total_responses > 0 else 0,
            "tool_usage": tool_usage,
            "conversation_tree": self.get_conversation_tree(conversation_id)
        }