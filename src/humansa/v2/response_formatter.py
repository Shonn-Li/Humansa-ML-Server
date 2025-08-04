"""
Response Formatter for OpenAI Responses API Format
Converts LlamaIndex agent outputs to proper OpenAI Responses API format
with full reasoning chain, tool calls, and streaming events
"""

import json
import time
import uuid
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


# Output item types
@dataclass
class TextOutput:
    """Text output item"""
    type: str = "text"
    text: str = ""


@dataclass
class ToolUse:
    """Tool invocation details"""
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class ToolUseOutput:
    """Tool use output item"""
    tool_use: ToolUse
    type: str = "tool_use"


@dataclass
class ToolResult:
    """Tool execution result"""
    tool_use_id: str
    output: Union[str, Dict[str, Any]]
    is_error: bool = False


@dataclass
class ToolResultOutput:
    """Tool result output item"""
    tool_result: ToolResult
    type: str = "tool_result"


# Union type for all output items
OutputItem = Union[TextOutput, ToolUseOutput, ToolResultOutput]


class ResponseFormatter:
    """
    Formats LlamaIndex agent responses to OpenAI Responses API format
    """
    
    def __init__(self):
        self.current_tool_id = 0
        
    def format_agent_response(
        self,
        agent_response: Any,
        model: str = "gpt-4.1",
        response_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert LlamaIndex agent response to OpenAI Responses format
        
        Returns complete response object with output array
        """
        if not response_id:
            response_id = f"resp_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        # Extract output items from agent response
        output_items = self._extract_output_items(agent_response)
        
        # Calculate token usage
        usage = self._calculate_usage(output_items)
        
        # Build response object
        response = {
            "id": response_id,
            "object": "response",
            "created": int(time.time()),
            "model": model,
            "output": [self._serialize_output_item(item) for item in output_items],
            "usage": usage,
            "metadata": {
                "reasoning_tokens": usage.get("reasoning_tokens", 0),
                "tool_tokens": usage.get("tool_tokens", 0)
            }
        }
        
        return response
    
    def _extract_output_items(self, agent_response: Any) -> List[OutputItem]:
        """
        Extract all output items from LlamaIndex agent response
        
        This includes:
        1. Initial reasoning text
        2. Tool calls and their results
        3. Final response text
        """
        output_items = []
        
        # Check if agent has step-by-step reasoning (ReAct pattern)
        if hasattr(agent_response, 'sources') and agent_response.sources:
            # Process each reasoning step
            for source in agent_response.sources:
                if hasattr(source, 'raw_output'):
                    # Parse ReAct format: Thought, Action, Observation
                    react_steps = self._parse_react_output(source.raw_output)
                    
                    for step in react_steps:
                        if step['type'] == 'thought':
                            output_items.append(TextOutput(text=step['content']))
                        
                        elif step['type'] == 'action':
                            # Tool invocation
                            tool_id = f"tool_{self.current_tool_id}"
                            self.current_tool_id += 1
                            
                            tool_use = ToolUse(
                                id=tool_id,
                                name=step['tool_name'],
                                input=step['tool_input']
                            )
                            output_items.append(ToolUseOutput(tool_use=tool_use))
                            
                            # Tool result (observation)
                            if 'observation' in step:
                                tool_result = ToolResult(
                                    tool_use_id=tool_id,
                                    output=step['observation']
                                )
                                output_items.append(ToolResultOutput(tool_result=tool_result))
        
        # Add final response
        final_text = str(agent_response)
        if final_text and not any(isinstance(item, TextOutput) and item.text == final_text for item in output_items):
            output_items.append(TextOutput(text=final_text))
        
        # If no reasoning steps found, at least include the response
        if not output_items:
            output_items.append(TextOutput(text=str(agent_response)))
        
        return output_items
    
    def _parse_react_output(self, raw_output: str) -> List[Dict[str, Any]]:
        """
        Parse ReAct format output into structured steps
        
        Expected format:
        Thought: [reasoning]
        Action: [tool_name]
        Action Input: [tool_input]
        Observation: [tool_result]
        """
        steps = []
        lines = raw_output.strip().split('\n')
        
        current_step = {}
        for line in lines:
            line = line.strip()
            
            if line.startswith('Thought:') or line.startswith('思考:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'thought',
                    'content': line.split(':', 1)[1].strip() if ':' in line else line
                }
            
            elif line.startswith('Action:') or line.startswith('行动:'):
                tool_name = line.split(':', 1)[1].strip() if ':' in line else ''
                current_step = {
                    'type': 'action',
                    'tool_name': tool_name,
                    'tool_input': {}
                }
            
            elif line.startswith('Action Input:') or line.startswith('行动输入:'):
                if current_step.get('type') == 'action':
                    input_str = line.split(':', 1)[1].strip() if ':' in line else '{}'
                    try:
                        current_step['tool_input'] = json.loads(input_str)
                    except:
                        current_step['tool_input'] = {'query': input_str}
            
            elif line.startswith('Observation:') or line.startswith('观察:'):
                if current_step.get('type') == 'action':
                    current_step['observation'] = line.split(':', 1)[1].strip() if ':' in line else ''
                    steps.append(current_step)
                    current_step = {}
        
        if current_step:
            steps.append(current_step)
        
        return steps
    
    def _serialize_output_item(self, item: OutputItem) -> Dict[str, Any]:
        """Serialize output item to dict"""
        if isinstance(item, TextOutput):
            return {"type": "text", "text": item.text}
        elif isinstance(item, ToolUseOutput):
            return {
                "type": "tool_use",
                "tool_use": {
                    "id": item.tool_use.id,
                    "name": item.tool_use.name,
                    "input": item.tool_use.input
                }
            }
        elif isinstance(item, ToolResultOutput):
            return {
                "type": "tool_result",
                "tool_result": {
                    "tool_use_id": item.tool_result.tool_use_id,
                    "output": item.tool_result.output,
                    "is_error": item.tool_result.is_error
                }
            }
        else:
            return {"type": "unknown", "content": str(item)}
    
    def _calculate_usage(self, output_items: List[OutputItem]) -> Dict[str, int]:
        """Calculate token usage from output items"""
        text_tokens = 0
        tool_tokens = 0
        
        for item in output_items:
            if isinstance(item, TextOutput):
                # Rough estimation: 1 token per 4 chars (English) or 2 chars (Chinese)
                text_tokens += self._estimate_tokens(item.text)
            elif isinstance(item, (ToolUseOutput, ToolResultOutput)):
                tool_tokens += self._estimate_tokens(json.dumps(self._serialize_output_item(item)))
        
        total_tokens = text_tokens + tool_tokens
        
        return {
            "prompt_tokens": 0,  # Will be set by API based on input
            "completion_tokens": total_tokens,
            "total_tokens": total_tokens,
            "reasoning_tokens": text_tokens,
            "tool_tokens": tool_tokens
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0
        
        # Count Chinese characters
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        # Rough estimation
        return (chinese_chars // 2) + (other_chars // 4)
    
    async def stream_response_events(
        self,
        agent_stream: AsyncGenerator,
        response_id: Optional[str] = None,
        model: str = "gpt-4.1"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Convert agent streaming output to OpenAI Responses API streaming events
        
        Yields events in format:
        - response.created
        - response.output_item.delta
        - response.output_item.done
        - response.done
        """
        if not response_id:
            response_id = f"resp_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        created_timestamp = int(time.time())
        
        # Emit response.created event
        yield {
            "event": "response.created",
            "data": {
                "id": response_id,
                "object": "response",
                "created": created_timestamp,
                "model": model
            }
        }
        
        output_items = []
        current_text = ""
        output_index = 0
        
        # Process streaming chunks
        async for chunk in agent_stream:
            # Handle different chunk formats from LlamaIndex
            if hasattr(chunk, 'delta'):
                delta_text = chunk.delta
            elif isinstance(chunk, str):
                delta_text = chunk
            elif hasattr(chunk, 'response'):
                delta_text = chunk.response
            else:
                delta_text = str(chunk)
            
            if delta_text:
                current_text += delta_text
                
                # Emit text delta event
                yield {
                    "event": "response.output_item.delta",
                    "data": {
                        "output_index": output_index,
                        "item": {
                            "type": "text",
                            "text": delta_text
                        }
                    }
                }
        
        # Complete the current text item
        if current_text:
            yield {
                "event": "response.output_item.done",
                "data": {
                    "output_index": output_index,
                    "item": {
                        "type": "text",
                        "text": current_text
                    }
                }
            }
            
            output_items.append({
                "type": "text",
                "text": current_text
            })
        
        # Calculate final usage
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": self._estimate_tokens(current_text),
            "total_tokens": self._estimate_tokens(current_text)
        }
        
        # Emit response.done event
        yield {
            "event": "response.done",
            "data": {
                "id": response_id,
                "object": "response",
                "created": created_timestamp,
                "model": model,
                "output": output_items,
                "usage": usage
            }
        }
    
    def extract_tool_calls_from_agent(self, agent_response: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from agent response for transparency
        """
        tool_calls = []
        
        if hasattr(agent_response, 'sources'):
            for source in agent_response.sources:
                if hasattr(source, 'tool_name') and source.tool_name:
                    tool_call = {
                        "tool": source.tool_name,
                        "input": getattr(source, 'tool_input', {}),
                        "output": getattr(source, 'tool_output', None)
                    }
                    tool_calls.append(tool_call)
        
        return tool_calls