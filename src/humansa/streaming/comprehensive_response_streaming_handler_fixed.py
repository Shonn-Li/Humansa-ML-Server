"""
Comprehensive Response Streaming Handler for Humansa Agentic Agent

Implements the full specification for event-driven streaming with proper lifecycle,
output items, reasoning, web search, function calls, and assistant messages.

Each ReAct step (Thought/Action/Observation) gets its own output_item wrapper.
Proper content part streaming with delta chunks and completion events.
"""

import json
import logging
import time
import uuid
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)


class ComprehensiveResponseStreamingHandler:
    """
    Comprehensive streaming handler implementing the full specification.

    Properly parses ReAct agent trace and creates correct output items
    with proper lifecycle events for each step.
    """

    def __init__(self, model: str = "gpt-4.1-nano"):
        self.model = model
        self.response_id = f"resp_{uuid.uuid4().hex[:8]}"
        self.output_index = 0

    def generate_output_id(self, prefix: str = "item") -> str:
        """Generate unique output item ID."""
        self.output_index += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def create_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured SSE event."""
        return {
            "event": event_type,
            "data": data,
            "id": self.response_id,
            "timestamp": datetime.now().isoformat()
        }

    async def stream_agent_response(self, agent_response: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Convert agent response to comprehensive streaming format.

        Args:
            agent_response: Response from HumansaAgenticAgent.execute_with_tools()

        Yields:
            Comprehensive streaming events following the specification
        """
        try:
            # Phase 1: Lifecycle - response.created
            yield self.create_event("response.created", {
                "response_id": self.response_id,
                "model": self.model,
                "created": int(time.time())
            })

            # Phase 2: response.in_progress
            yield self.create_event("response.in_progress", {})

            # Extract agent data
            agent_trace = agent_response.get('agent_trace', '')
            tool_calls_observed = agent_response.get('tool_calls_observed', [])
            final_response = agent_response.get('agent_response', '')

            logger.info(f"🔄 Starting comprehensive streaming conversion")
            logger.info(f"📝 Agent trace: {len(agent_trace)} chars")
            logger.info(f"🛠️ Tool calls: {len(tool_calls_observed)}")

            # Phase 3: Parse and stream ReAct trace properly
            if agent_trace:
                react_steps = self._parse_react_trace(agent_trace)
                logger.info(f"🧠 Parsed {len(react_steps)} ReAct steps")

                for step in react_steps:
                    async for event in self._stream_react_step(step, tool_calls_observed):
                        yield event

            # Phase 4: Stream final assistant answer
            final_answer = self._extract_final_answer(
                agent_trace, final_response)
            if final_answer:
                async for event in self._stream_assistant_message(final_answer):
                    yield event

            # Phase 5: Lifecycle - response.completed
            yield self.create_event("response.completed", {
                "response_id": self.response_id,
                "total_output_items": self.output_index
            })

            logger.info(
                f"✅ Comprehensive streaming completed - {self.output_index} output items")

        except Exception as e:
            logger.error(f"❌ Comprehensive streaming failed: {e}")

            # Phase 5 (error): Lifecycle - response.failed
            yield self.create_event("response.failed", {
                "response_id": self.response_id,
                "error": str(e)
            })

    def _parse_react_trace(self, agent_trace: str) -> List[Dict[str, Any]]:
        """Parse ReAct agent trace into structured steps."""
        if not agent_trace:
            return []

        steps = []
        lines = agent_trace.split('\n')
        current_step = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect ReAct step types
            if line.startswith('Thought:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'thought',
                    'content': line[8:].strip()  # Remove "Thought:" prefix
                }
            elif line.startswith('Action:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'action',
                    'content': line[7:].strip()  # Remove "Action:" prefix
                }
            elif line.startswith('Observation:'):
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'type': 'observation',
                    # Remove "Observation:" prefix
                    'content': line[12:].strip()
                }
            elif line.startswith('Answer:') or line.startswith('Final Answer:'):
                if current_step:
                    steps.append(current_step)
                # Don't create a step for Answer - that's handled separately
                break
            elif current_step:
                # Continue current step content
                current_step['content'] += ' ' + line

        # Add final step if exists
        if current_step:
            steps.append(current_step)

        return steps

    async def _stream_react_step(self, step: Dict[str, Any], tool_calls: List[Dict]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a single ReAct step with proper output item lifecycle."""
        step_type = step.get('type')
        content = step.get('content', '')

        if step_type == 'thought':
            # Stream reasoning step
            async for event in self._stream_reasoning_step(content):
                yield event

        elif step_type == 'action':
            # Parse action to determine if it's web search or function call
            if self._is_web_search_action(content):
                async for event in self._stream_web_search_action(content, tool_calls):
                    yield event
            else:
                async for event in self._stream_function_call_action(content, tool_calls):
                    yield event

        elif step_type == 'observation':
            # For observations, we might want to stream them as function results
            # But they're often already handled by the action, so we might skip
            pass

    async def _stream_reasoning_step(self, thought_content: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a reasoning step with proper lifecycle."""
        reasoning_id = self.generate_output_id("rs")

        # Start reasoning output item
        yield self.create_event("response.output_item.added", {
            "output_index": self.output_index,
            "item": {
                "id": reasoning_id,
                "type": "reasoning",
                "status": "in_progress"
            }
        })

        # Add reasoning text part
        yield self.create_event("response.reasoning_part.added", {
            "item_id": reasoning_id,
            "part_type": "reasoning_text"
        })

        # Stream reasoning text in chunks (clean content, no "Thought:" prefix)
        for chunk in self._chunk_text(thought_content, chunk_size=50):
            yield self.create_event("response.reasoning_text.delta", {
                "item_id": reasoning_id,
                "delta": chunk
            })

        # Complete reasoning text
        yield self.create_event("response.reasoning_text.done", {
            "item_id": reasoning_id
        })

        # Complete reasoning part
        yield self.create_event("response.reasoning_part.done", {
            "item_id": reasoning_id
        })

        # Complete reasoning output item
        yield self.create_event("response.output_item.done", {
            "output_index": self.output_index,
            "item": {
                "id": reasoning_id,
                "type": "reasoning",
                "status": "completed",
                "content": [
                    {
                        "type": "reasoning_text",
                        "text": thought_content
                    }
                ]
            }
        })

    def _is_web_search_action(self, action_content: str) -> bool:
        """Determine if an action is a web search."""
        search_indicators = ['search', 'web_search',
                             'internet', 'google', 'bing']
        return any(indicator in action_content.lower() for indicator in search_indicators)

    async def _stream_web_search_action(self, action_content: str, tool_calls: List[Dict]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream web search action with proper lifecycle."""
        search_id = self.generate_output_id("ws")

        # Extract query from action content
        query = self._extract_search_query(action_content)

        # Add web search output item
        yield self.create_event("response.output_item.added", {
            "output_index": self.output_index,
            "item": {
                "id": search_id,
                "type": "web_search_call",
                "status": "in_progress",
                "action": {
                    "query": query,
                    "search_engine": "serper"
                }
            }
        })

        # Web search in progress
        yield self.create_event("response.web_search_call.in_progress", {
            "item_id": search_id,
            "query": query
        })

        # Web search searching
        yield self.create_event("response.web_search_call.searching", {
            "item_id": search_id
        })

        # Find matching tool call result
        search_result = self._find_matching_tool_result(
            'web_search', tool_calls)
        results = []

        if search_result:
            results = self._extract_search_results(search_result)

        # Web search completed
        yield self.create_event("response.web_search_call.completed", {
            "item_id": search_id,
            "results_count": len(results)
        })

        # Complete web search output item
        yield self.create_event("response.output_item.done", {
            "output_index": self.output_index,
            "item": {
                "id": search_id,
                "type": "web_search_call",
                "status": "completed",
                "action": {
                    "query": query,
                    "search_engine": "serper"
                },
                "results": results
            }
        })

    async def _stream_function_call_action(self, action_content: str, tool_calls: List[Dict]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream function call action with separate call and result items."""

        # Parse function call from action
        func_name, func_args = self._parse_function_call(action_content)
        matching_tool_call = self._find_matching_tool_result(
            func_name, tool_calls)

        # Stream function call item
        call_id = self.generate_output_id("fc")

        yield self.create_event("response.output_item.added", {
            "output_index": self.output_index,
            "item": {
                "id": call_id,
                "type": "function_tool_call",
                "status": "in_progress",
                "name": func_name,
                "arguments": json.dumps(func_args) if isinstance(func_args, dict) else str(func_args)
            }
        })

        # Complete function call (without output - that goes in separate item)
        yield self.create_event("response.output_item.done", {
            "output_index": self.output_index,
            "item": {
                "id": call_id,
                "type": "function_tool_call",
                "status": "completed",
                "name": func_name,
                "arguments": json.dumps(func_args) if isinstance(func_args, dict) else str(func_args),
                "output": None  # No output in call item when we create separate result item
            }
        })

        # Stream function result item if we have a result
        if matching_tool_call and matching_tool_call.get('result'):
            async for event in self._stream_function_result_item(matching_tool_call['result']):
                yield event

    async def _stream_function_result_item(self, tool_result: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream function tool result as separate item."""
        result_id = self.generate_output_id("fr")

        # Convert result to clean text
        result_text = self._clean_tool_result(tool_result)

        yield self.create_event("response.output_item.added", {
            "output_index": self.output_index,
            "item": {
                "id": result_id,
                "type": "function_tool_result",
                "status": "in_progress",
                "role": "tool"
            }
        })

        # Stream result text in chunks (only the text content, not raw JSON)
        for chunk in self._chunk_text(result_text, chunk_size=100):
            yield self.create_event("response.function_tool_result.delta", {
                "item_id": result_id,
                "delta": chunk
            })

        # Complete function tool result
        yield self.create_event("response.function_tool_result.done", {
            "item_id": result_id
        })

        # Complete function tool result output item
        yield self.create_event("response.output_item.done", {
            "output_index": self.output_index,
            "item": {
                "id": result_id,
                "type": "function_tool_result",
                "status": "completed",
                "role": "tool",
                "content": [
                    {
                        "type": "output_text",
                        "text": result_text
                    }
                ]
            }
        })

    async def _stream_assistant_message(self, final_answer: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream assistant message as output item with content parts."""
        message_id = self.generate_output_id("msg")

        # Add assistant message output item
        yield self.create_event("response.output_item.added", {
            "output_index": self.output_index,
            "item": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "status": "in_progress"
            }
        })

        # Add content part
        yield self.create_event("response.content_part.added", {
            "item_id": message_id,
            "part_type": "output_text"
        })

        # Stream output text in chunks
        for chunk in self._chunk_text(final_answer, chunk_size=50):
            yield self.create_event("response.output_text.delta", {
                "item_id": message_id,
                "delta": chunk
            })

        # Complete output text
        yield self.create_event("response.output_text.done", {
            "item_id": message_id
        })

        # Complete content part
        yield self.create_event("response.content_part.done", {
            "item_id": message_id
        })

        # Complete assistant message output item
        yield self.create_event("response.output_item.done", {
            "output_index": self.output_index,
            "item": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": final_answer,
                        "annotations": []  # TODO: Add citations when available
                    }
                ]
            }
        })

    def _extract_search_query(self, action_content: str) -> str:
        """Extract search query from action content."""
        # Try to extract query from various formats
        if 'query' in action_content.lower():
            # Look for quoted strings after 'query'
            import re
            match = re.search(
                r'query["\']?\s*[:=]\s*["\']([^"\']+)["\']', action_content, re.IGNORECASE)
            if match:
                return match.group(1)

        # Fallback: use the action content itself
        return action_content.strip()

    def _parse_function_call(self, action_content: str) -> tuple:
        """Parse function name and arguments from action content."""
        try:
            # Try to parse JSON-like content
            if '{' in action_content and '}' in action_content:
                start_idx = action_content.find('{')
                end_idx = action_content.rfind('}') + 1
                json_part = action_content[start_idx:end_idx]

                # Clean up the JSON - replace single quotes with double quotes
                json_part = json_part.replace("'", '"').replace(
                    'True', 'true').replace('False', 'false')

                try:
                    parsed = json.loads(json_part)
                    tool_name = parsed.get('tool', parsed.get(
                        'function', 'unknown_function'))
                    arguments = parsed.get('arguments', parsed.get('args', {}))
                    return tool_name, arguments
                except json.JSONDecodeError:
                    pass

            # Fallback
            return 'unknown_function', {'action': action_content}
        except Exception:
            return 'unknown_function', {'action': action_content}

    def _find_matching_tool_result(self, tool_name: str, tool_calls: List[Dict]) -> Optional[Dict]:
        """Find matching tool call result."""
        for tool_call in tool_calls:
            call_tool_name = tool_call.get(
                'tool_name') or tool_call.get('name', '')
            if tool_name.lower() in call_tool_name.lower() or call_tool_name.lower() in tool_name.lower():
                return tool_call
        return None

    def _extract_search_results(self, search_result: Dict) -> List[Dict]:
        """Extract clean search results from tool result."""
        result_data = search_result.get('result', {})
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except:
                return []

        results = result_data.get('results', [])
        clean_results = []

        for result in results[:5]:  # Limit to top 5 results
            clean_results.append({
                "url": result.get('url', ''),
                "title": result.get('title', ''),
                "snippet": result.get('snippet', '')
            })

        return clean_results

    def _clean_tool_result(self, tool_result: Any) -> str:
        """Convert tool result to clean text format."""
        if isinstance(tool_result, dict):
            # Extract meaningful text from dict
            if 'results' in tool_result:
                results = tool_result['results']
                if isinstance(results, list):
                    summaries = []
                    for result in results[:3]:  # Top 3 results
                        title = result.get('title', '')
                        snippet = result.get('snippet', '')
                        if title and snippet:
                            summaries.append(f"{title}: {snippet}")
                    return '\n'.join(summaries)

            # Try to extract other meaningful fields
            text_parts = []
            for key in ['summary', 'content', 'text', 'description']:
                if key in tool_result:
                    text_parts.append(str(tool_result[key]))

            if text_parts:
                return ' '.join(text_parts)

        # Fallback: convert to string but clean it up
        result_str = str(tool_result)
        # Remove Python-style formatting
        result_str = result_str.replace("'", '"').replace(
            'True', 'true').replace('False', 'false')
        return result_str

    def _extract_final_answer(self, agent_trace: str, final_response: str) -> str:
        """Extract final answer from agent trace or response."""
        # Look for Answer: or Final Answer: in trace
        if agent_trace:
            lines = agent_trace.split('\n')
            for line in reversed(lines):
                if line.strip().startswith(('Answer:', 'Final Answer:')):
                    return line.split(':', 1)[1].strip()

        # Use final response if available
        if final_response and final_response.strip():
            return final_response.strip()

        return "I have completed the analysis based on the available information."

    def _chunk_text(self, text: str, chunk_size: int = 50) -> List[str]:
        """Split text into smaller chunks for streaming."""
        if not text:
            return []

        chunks = []
        words = text.split()
        current_chunk = []

        for word in words:
            current_chunk.append(word)
            if len(' '.join(current_chunk)) >= chunk_size:
                chunks.append(' '.join(current_chunk) + ' ')
                current_chunk = []

        # Add remaining words
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks


async def convert_agent_response_to_comprehensive_stream(agent_response: Dict[str, Any],
                                                         model: str = "gpt-4.1-nano") -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to convert agent response to comprehensive streaming format.

    Args:
        agent_response: Response from HumansaAgenticAgent.execute_with_tools()
        model: Model name for the response

    Yields:
        Comprehensive streaming events following the specification
    """
    handler = ComprehensiveResponseStreamingHandler(model)
    async for event in handler.stream_agent_response(agent_response):
        yield event
