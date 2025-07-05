"""
OpenAI v1 Streaming Handler for Humansa Agentic Agent

This module provides OpenAI v1-compatible streaming for agent reasoning and tool calls.
Converts ReAct agent output to proper delta.reasoning_content and delta.tool_calls format.
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenAIV1StreamingHandler:
    """
    Converts Humansa agent output to OpenAI v1 streaming format.
    
    Uses:
    - delta.reasoning_content for thoughts, observations, answers
    - delta.tool_calls for tool calls/actions  
    - delta.content for progress and errors
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.stream_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        self.chunk_index = 0
        
    def create_chunk(self, delta: Dict[str, Any], reasoning: Optional[str] = None, 
                    finish_reason: Optional[str] = None) -> Dict[str, Any]:
        """Create an OpenAI v1-compatible streaming chunk."""
        chunk = {
            "id": self.stream_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": self.model,
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason
            }]
        }
        
        # Add reasoning field for frontend processing
        if reasoning:
            chunk["reasoning"] = reasoning
            
        self.chunk_index += 1
        return chunk
    
    async def stream_agent_reasoning(self, agent_response: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Convert agent response to OpenAI v1 streaming format.
        
        Args:
            agent_response: Response from HumansaAgenticAgent.execute_with_tools()
            
        Yields:
            OpenAI v1-compatible streaming chunks
        """
        try:
            # Extract agent data
            agent_trace = agent_response.get('agent_trace', '')
            tool_calls_observed = agent_response.get('tool_calls_observed', [])
            reasoning_text = agent_response.get('reasoning', '')
            final_response = agent_response.get('agent_response', '')
            
            logger.info(f"🔄 Starting OpenAI v1 streaming conversion")
            logger.info(f"📝 Agent trace: {len(agent_trace)} chars")
            logger.info(f"🛠️ Tool calls: {len(tool_calls_observed)}")
            
            # Parse agent trace into reasoning steps
            reasoning_steps = self._parse_agent_trace(agent_trace)
            logger.info(f"🧠 Parsed {len(reasoning_steps)} reasoning steps")
            
            # Stream progress
            yield self.create_chunk(
                delta={"content": "🤖 Agent is processing your request..."},
                reasoning="progress"
            )
            
            # Stream reasoning steps
            for i, step in enumerate(reasoning_steps):
                step_type = step.get('type', 'thought')
                content = step.get('content', '')
                
                if step_type in ['thought', 'observation', 'answer'] and content:
                    # Use reasoning_content for thoughts, observations, answers
                    yield self.create_chunk(
                        delta={"reasoning_content": content},
                        reasoning=step_type
                    )
                    logger.debug(f"💭 Streamed {step_type}: {content[:50]}...")
                    
                elif step_type == 'action' and content:
                    # Parse tool call from action
                    tool_call = self._parse_tool_call_from_action(content, i)
                    if tool_call:
                        yield self.create_chunk(
                            delta={"tool_calls": [tool_call]},
                            reasoning="action"
                        )
                        logger.debug(f"⚡ Streamed tool call: {tool_call['function']['name']}")
            
            # Stream tool call results if available
            for tool_call in tool_calls_observed:
                if tool_call.get('result'):
                    yield self.create_chunk(
                        delta={"reasoning_content": f"Tool result: {tool_call['result'][:200]}..."},
                        reasoning="observation"
                    )
            
            # Stream final answer if available
            if final_response and final_response != agent_trace:
                yield self.create_chunk(
                    delta={"reasoning_content": final_response},
                    reasoning="answer"
                )
            
            # Stream completion
            yield self.create_chunk(
                delta={},
                finish_reason="stop"
            )
            
            logger.info(f"✅ OpenAI v1 streaming completed - {self.chunk_index} chunks")
            
        except Exception as e:
            logger.error(f"❌ OpenAI v1 streaming failed: {e}")
            # Stream error
            yield self.create_chunk(
                delta={"content": f"Error in agent processing: {str(e)}"},
                reasoning="error"
            )
            yield self.create_chunk(
                delta={},
                finish_reason="stop"
            )
    
    def _parse_agent_trace(self, agent_trace: str) -> List[Dict[str, Any]]:
        """Parse agent trace into structured reasoning steps."""
        if not agent_trace:
            return []
        
        steps = []
        lines = agent_trace.split('\n')
        current_step = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect step types
            if line.startswith('Thought:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'thought',
                    'content': line.replace('Thought:', '').strip()
                }
            elif line.startswith('Action:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'action', 
                    'content': line.replace('Action:', '').strip()
                }
            elif line.startswith('Observation:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'observation',
                    'content': line.replace('Observation:', '').strip()
                }
            elif line.startswith('Answer:') or line.startswith('Final Answer:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'answer',
                    'content': line.replace('Answer:', '').replace('Final Answer:', '').strip()
                }
            elif current_step:
                # Continue current step content
                current_step['content'] += ' ' + line
        
        # Add final step
        if current_step:
            steps.append(current_step)
            
        return steps
    
    def _parse_tool_call_from_action(self, action_content: str, call_index: int) -> Optional[Dict[str, Any]]:
        """Parse tool call from action content."""
        try:
            # Try to parse JSON if it looks like a tool call
            if '{' in action_content and '}' in action_content:
                # Extract JSON part
                start_idx = action_content.find('{')
                end_idx = action_content.rfind('}') + 1
                json_part = action_content[start_idx:end_idx]
                
                try:
                    parsed = json.loads(json_part)
                    if 'tool' in parsed or 'function' in parsed:
                        tool_name = parsed.get('tool', parsed.get('function', 'unknown'))
                        arguments = parsed.get('arguments', parsed.get('args', {}))
                        
                        return {
                            "index": call_index,
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
                            }
                        }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: create tool call from text
            tool_name = "agent_action"
            if "search" in action_content.lower():
                tool_name = "search_tool"
            elif "database" in action_content.lower():
                tool_name = "database_tool"
            elif "web" in action_content.lower():
                tool_name = "web_tool"
                
            return {
                "index": call_index,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function", 
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps({"action": action_content})
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse tool call from action: {e}")
            return None


async def convert_agent_response_to_v1_stream(agent_response: Dict[str, Any], 
                                             model: str = "gpt-4o-mini") -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to convert agent response to OpenAI v1 streaming format.
    
    Args:
        agent_response: Response from HumansaAgenticAgent.execute_with_tools()
        model: Model name for the response
        
    Yields:
        OpenAI v1-compatible streaming chunks
    """
    handler = OpenAIV1StreamingHandler(model)
    async for chunk in handler.stream_agent_reasoning(agent_response):
        yield chunk
