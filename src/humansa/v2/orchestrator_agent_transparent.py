"""
HUMANSA V2 Orchestrator Agent with Transparent Tool Calls
Captures and exposes all reasoning steps and tool invocations
in OpenAI Responses API format
"""

import os
import logging
import json
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple, Tuple
from datetime import datetime
import asyncio

# LlamaIndex imports
try:
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
    from llama_index.core import Settings
    from llama_index.llms.openai import OpenAI
    from llama_index.core.callbacks.base import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType
    
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    logging.warning("LlamaIndex not available - agent features disabled")

# Import consolidated tools
try:
    from humansa.tools.consolidated_tools import ConsolidatedHumansaTools, DynamicToolLoader
    CONSOLIDATED_TOOLS_AVAILABLE = True
except ImportError:
    CONSOLIDATED_TOOLS_AVAILABLE = False
    logging.warning("Consolidated tools not available")

logger = logging.getLogger(__name__)


class ToolCallCapture(BaseCallbackHandler):
    """Callback handler to capture tool calls and reasoning steps"""
    
    def __init__(self):
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[]
        )
        self.captured_steps = []
        self.current_thought = ""
        self.current_tool_id = 0
    
    def on_event_start(self, event_type: CBEventType, payload: Dict[str, Any], **kwargs) -> None:
        """Capture start of events"""
        if event_type == CBEventType.LLM:
            # Capture LLM thinking
            self.current_thought = ""
    
    def on_event_end(self, event_type: CBEventType, payload: Dict[str, Any], **kwargs) -> None:
        """Capture end of events"""
        if event_type == CBEventType.LLM:
            # Capture thought from LLM
            if payload and isinstance(payload, dict):
                response = payload.get("response", {})
                if hasattr(response, "message"):
                    content = response.message.content
                    if content and "Thought:" in content:
                        self.current_thought = content
                        self.captured_steps.append({
                            "type": "thought",
                            "content": content
                        })
        
        elif event_type == CBEventType.FUNCTION_CALL:
            # Capture tool call
            if payload:
                # Debug logging to understand payload structure
                logger.debug(f"FUNCTION_CALL payload type: {type(payload)}")
                logger.debug(f"FUNCTION_CALL payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
                logger.debug(f"FUNCTION_CALL payload: {str(payload)[:500]}")  # First 500 chars
                
                tool_id = f"tool_{self.current_tool_id}"
                self.current_tool_id += 1
                
                # Try different ways to get tool name
                function_call = payload.get("function_call", {})
                tool_name = "unknown"
                
                # Method 1: From function_call.name
                if function_call and "name" in function_call:
                    tool_name = function_call.get("name")
                # Method 2: From payload.tool_name
                elif "tool_name" in payload:
                    tool_name = payload.get("tool_name")
                # Method 3: From payload.tool
                elif "tool" in payload:
                    tool = payload.get("tool", {})
                    if hasattr(tool, "metadata") and hasattr(tool.metadata, "name"):
                        tool_name = tool.metadata.name
                    elif hasattr(tool, "name"):
                        tool_name = tool.name
                
                tool_output = payload.get("response")
                
                # Add tool use
                self.captured_steps.append({
                    "type": "tool_use",
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "tool_input": function_call.get("arguments", {})
                })
                
                # Add tool result
                self.captured_steps.append({
                    "type": "tool_result",
                    "tool_id": tool_id,
                    "output": str(tool_output) if tool_output else ""
                })
    
    def reset(self):
        """Reset captured data"""
        self.captured_steps = []
        self.current_thought = ""
        self.current_tool_id = 0
    
    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a trace - required by BaseCallbackHandler"""
        # Implementation for trace start
        if trace_id:
            logger.debug(f"Starting trace: {trace_id}")
    
    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """End a trace - required by BaseCallbackHandler"""
        # Implementation for trace end
        if trace_id:
            logger.debug(f"Ending trace: {trace_id}")


class HumansaOrchestratorAgentTransparent:
    """
    Orchestrator agent that captures and exposes all tool calls
    and reasoning steps in OpenAI Responses API format
    """
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        debug: bool = False,
        use_real_tools: bool = True,
        db_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the transparent orchestrator"""
        
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex is required for HumansaOrchestratorAgentTransparent")
        
        self.llm = llm or Settings.llm
        self.memory_manager = memory_manager
        self.debug = debug
        self.use_real_tools = use_real_tools and CONSOLIDATED_TOOLS_AVAILABLE
        
        # Initialize tool call capture
        self.tool_capture = ToolCallCapture()
        
        # Initialize debug handler if needed
        self.debug_handler = LlamaDebugHandler() if debug else None
        
        # Create callback manager with both handlers
        handlers = []
        if self.debug_handler:
            handlers.append(self.debug_handler)
        handlers.append(self.tool_capture)
        self.callback_manager = CallbackManager(handlers)
        
        # Initialize consolidated tool manager
        self.tool_manager = None
        self.dynamic_loader = None
        if self.use_real_tools:
            try:
                self.tool_manager = ConsolidatedHumansaTools(memory_manager=memory_manager)
                self.dynamic_loader = DynamicToolLoader(self.tool_manager)
                logger.info("✅ Initialized transparent orchestrator with tool capture")
            except Exception as e:
                logger.error(f"❌ Failed to initialize tools: {e}")
                self.use_real_tools = False
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use the official HUMANSA V2 system prompt
        from humansa.prompts.humansa_system_prompt_v2 import HUMANSA_REACT_PROMPT_V2
        
        # Strengthen identity enforcement
        identity_prefix = """【重要身份提醒】
你是诺亚新舟健康医疗助理小诺（HUMANSA）。
- 当被问"你是谁"时，必须回答："我是诺亚新舟健康医疗助理小诺，您的AI健康管家。"
- 公司口号：以爱行舟，亲近相守
- 公司规模：500多位三甲主任级名医专家，30+家高端综合名医诊所

"""
        
        # Get the complete system prompt with React format
        self.orchestrator_prompt = identity_prefix + HUMANSA_REACT_PROMPT_V2
        
        logger.info("✅ HumansaOrchestratorAgentTransparent initialized")
    
    def _is_identity_question(self, query: str) -> bool:
        """Check if the query is asking about identity"""
        identity_patterns = [
            "你是谁", "您是谁", "你叫什么", "您叫什么",
            "什么是小诺", "什么是humansa", "什么是诺亚新舟",
            "介绍一下你", "介绍一下您", "你是什么",
            "who are you", "what are you", "tell me about yourself",
            "你的身份", "您的身份", "你是做什么的"
        ]
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in identity_patterns)
    
    def _create_identity_response(self) -> str:
        """Create the standard HUMANSA identity response"""
        return (
            "我是诺亚新舟健康医疗助理小诺，您的AI健康管家。"
            "诺亚新舟（Humansa）以'以爱行舟，亲近相守'为理念，"
            "拥有500多位三甲主任级名医专家，在全国开设30+家高端综合名医诊所。"
            "我可以帮助您查询医生、预约挂号、了解医疗服务等。有什么可以帮助您的吗？"
        )
    
    def _create_agent_for_query(self, query: str) -> Tuple[ReActAgent, List[FunctionTool]]:
        """Create an agent with dynamically selected tools based on query, returns agent and tools"""
        if self.use_real_tools and self.dynamic_loader:
            # Select tools based on query context
            selected_tools = self.dynamic_loader.select_tools_for_query(query)
            logger.info(f"🎯 Selected {len(selected_tools)} tools for query")
        else:
            selected_tools = []
        
        # Create agent with selected tools
        agent = ReActAgent.from_tools(
            tools=selected_tools,
            llm=self.llm,
            verbose=self.debug,
            system_prompt=self.orchestrator_prompt,
            callback_manager=self.callback_manager,
            max_iterations=10
        )
        return agent, selected_tools
    
    async def process_query_with_transparency(
        self,
        query: str,
        user_id: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process query and return response in OpenAI Responses API format
        with full reasoning chain and tool calls exposed
        """
        
        logger.info(f"🎯 Processing query with transparency: {query[:100]}...")
        
        # Check if this is an identity question
        if self._is_identity_question(query):
            logger.info("🆔 Detected identity question - returning HUMANSA identity directly")
            identity_response = self._create_identity_response()
            
            return {
                "id": f"resp_{uuid.uuid4().hex[:12]}_{int(time.time())}",
                "object": "response",
                "created": int(time.time()),
                "model": "gpt-4-turbo",
                "output": [
                    {
                        "type": "text",
                        "text": identity_response
                    }
                ],
                "usage": {
                    "prompt_tokens": len(query) // 4,
                    "completion_tokens": len(identity_response) // 2,
                    "total_tokens": len(query) // 4 + len(identity_response) // 2
                },
                "metadata": {
                    "identity_response": True,
                    "tools_loaded": 0,
                    "tools_used": []
                }
            }
        
        # Reset tool capture
        self.tool_capture.reset()
        
        # Create agent with tools selected for this specific query
        agent, selected_tools = self._create_agent_for_query(query)
        
        # Build context
        context = self._build_context(user_id, messages)
        full_query = f"{context}当前查询：{query}" if context else query
        
        try:
            # Process query
            response = await asyncio.to_thread(agent.chat, full_query)
            
            # Build output array from captured steps
            output_items = self._build_output_array(response)
            
            # Extract tools used
            tools_used = list(set([
                step['tool_name'] 
                for step in self.tool_capture.captured_steps 
                if step['type'] == 'tool_use'
            ]))
            
            # Calculate usage
            usage = self._calculate_usage(output_items)
            
            # Build complete response
            return {
                "id": f"resp_{uuid.uuid4().hex[:12]}_{int(time.time())}",
                "object": "response",
                "created": int(time.time()),
                "model": "gpt-4-turbo",
                "output": output_items,
                "usage": usage,
                "metadata": {
                    "reasoning_tokens": usage.get("reasoning_tokens", 0),
                    "tool_tokens": usage.get("tool_tokens", 0),
                    "tools_loaded": len(selected_tools),
                    "tools_used": tools_used
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            # Return error in proper format
            return {
                "id": f"resp_error_{int(time.time())}",
                "object": "response",
                "created": int(time.time()),
                "model": "gpt-4-turbo",
                "output": [
                    {
                        "type": "text",
                        "text": f"抱歉，处理您的请求时遇到了问题：{str(e)}"
                    }
                ],
                "usage": {"total_tokens": 0},
                "metadata": {"error": str(e)}
            }
    
    async def stream_query_with_transparency(
        self,
        query: str,
        user_id: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response with proper event format
        """
        logger.info(f"🌊 Streaming query with transparency: {query[:100]}...")
        
        # Check if this is an identity question
        if self._is_identity_question(query):
            logger.info("🆔 Detected identity question in streaming - returning HUMANSA identity")
            identity_response = self._create_identity_response()
            
            # Create response ID
            response_id = f"resp_{uuid.uuid4().hex[:12]}_{int(time.time())}"
            created_timestamp = int(time.time())
            
            # Emit response.created
            yield {
                "event": "response.created",
                "data": {
                    "id": response_id,
                    "object": "response",
                    "created": created_timestamp,
                    "model": "gpt-4-turbo"
                }
            }
            
            # Emit identity text
            yield {
                "event": "response.output_item.done",
                "data": {
                    "output_index": 0,
                    "item": {
                        "type": "text",
                        "text": identity_response
                    }
                }
            }
            
            # Calculate usage
            usage = {
                "prompt_tokens": len(query) // 4,
                "completion_tokens": len(identity_response) // 2,
                "total_tokens": len(query) // 4 + len(identity_response) // 2
            }
            
            # Emit response.done
            yield {
                "event": "response.done",
                "data": {
                    "id": response_id,
                    "object": "response",
                    "created": created_timestamp,
                    "model": "gpt-4-turbo",
                    "output": [{"type": "text", "text": identity_response}],
                    "usage": usage,
                    "metadata": {
                        "identity_response": True,
                        "tools_loaded": 0,
                        "tools_used": []
                    }
                }
            }
            return
        
        # Reset tool capture
        self.tool_capture.reset()
        
        # Create response ID
        response_id = f"resp_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        created_timestamp = int(time.time())
        
        # Emit response.created event
        yield {
            "event": "response.created",
            "data": {
                "id": response_id,
                "object": "response",
                "created": created_timestamp,
                "model": "gpt-4-turbo"
            }
        }
        
        # Create agent
        agent, selected_tools = self._create_agent_for_query(query)
        
        # Build context
        context = self._build_context(user_id, messages)
        full_query = f"{context}当前查询：{query}" if context else query
        
        try:
            # Get streaming response
            streaming_response = agent.stream_chat(full_query)
            
            output_index = 0
            current_text = ""
            
            # Stream text chunks
            for chunk in streaming_response.response_gen:
                current_text += chunk
                
                # Emit text delta
                yield {
                    "event": "response.output_item.delta",
                    "data": {
                        "output_index": output_index,
                        "item": {
                            "type": "text",
                            "text": chunk
                        }
                    }
                }
            
            # Complete text item
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
            
            # Process captured tool calls
            output_items = [{"type": "text", "text": current_text}]
            
            # Add any tool calls that were captured
            for step in self.tool_capture.captured_steps:
                output_index += 1
                
                if step['type'] == 'tool_use':
                    item = {
                        "type": "tool_use",
                        "tool_use": {
                            "id": step['tool_id'],
                            "name": step['tool_name'],
                            "input": step['tool_input']
                        }
                    }
                    output_items.append(item)
                    
                    yield {
                        "event": "response.output_item.done",
                        "data": {
                            "output_index": output_index,
                            "item": item
                        }
                    }
                
                elif step['type'] == 'tool_result':
                    item = {
                        "type": "tool_result",
                        "tool_result": {
                            "tool_use_id": step['tool_id'],
                            "output": step['output']
                        }
                    }
                    output_items.append(item)
                    
                    yield {
                        "event": "response.output_item.done",
                        "data": {
                            "output_index": output_index,
                            "item": item
                        }
                    }
            
            # Calculate usage
            usage = self._calculate_usage(output_items)
            
            # Emit response.done
            yield {
                "event": "response.done",
                "data": {
                    "id": response_id,
                    "object": "response",
                    "created": created_timestamp,
                    "model": "gpt-4-turbo",
                    "output": output_items,
                    "usage": usage
                }
            }
            
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            # Emit error
            yield {
                "event": "response.output_item.done",
                "data": {
                    "output_index": 0,
                    "item": {
                        "type": "text",
                        "text": f"错误：{str(e)}"
                    }
                }
            }
            
            yield {
                "event": "response.done",
                "data": {
                    "id": response_id,
                    "object": "response",
                    "created": created_timestamp,
                    "model": "gpt-4-turbo",
                    "output": [{"type": "text", "text": f"错误：{str(e)}"}],
                    "usage": {"total_tokens": 0},
                    "error": str(e)
                }
            }
    
    def _build_context(self, user_id: Optional[str], messages: Optional[List[Dict[str, str]]]) -> str:
        """Build context from user history and messages"""
        context = ""
        
        # Add user context for tools
        if user_id:
            context += f"【用户信息】\n当前用户ID: {user_id}\n\n"
            context += f"【重要】在使用conversation_memory工具时，必须使用user_id='{user_id}'\n\n"
        
        # Add message history
        if messages:
            context += "对话历史：\n"
            for msg in messages[-6:]:  # Last 6 messages
                role = "用户" if msg["role"] == "user" else "助手"
                context += f"{role}: {msg['content']}\n"
            context += "\n"
        
        return context
    
    def _build_output_array(self, agent_response: Any) -> List[Dict[str, Any]]:
        """Build output array from agent response and captured steps"""
        output_items = []
        
        # Skip adding thinking steps to avoid exposing agent reasoning
        # Only process tool use and results for transparency
        for step in self.tool_capture.captured_steps:
            if step['type'] == 'thought':
                # Skip thought steps - they shouldn't be in final output
                continue
            
            elif step['type'] == 'tool_use':
                output_items.append({
                    "type": "tool_use",
                    "tool_use": {
                        "id": step['tool_id'],
                        "name": step['tool_name'],
                        "input": step['tool_input']
                    }
                })
            
            elif step['type'] == 'tool_result':
                output_items.append({
                    "type": "tool_result",
                    "tool_result": {
                        "tool_use_id": step['tool_id'],
                        "output": step['output']
                    }
                })
        
        # Add final response if not already captured
        final_response = str(agent_response)
        
        # Clean the response to remove thinking patterns
        final_response = self._clean_agent_response(final_response)
        
        if final_response and not any(
            item.get('type') == 'text' and item.get('text') == final_response 
            for item in output_items
        ):
            output_items.append({
                "type": "text",
                "text": final_response
            })
        
        # If no items captured, at least add the response
        if not output_items:
            output_items.append({
                "type": "text",
                "text": final_response
            })
        
        return output_items
    
    def _clean_agent_response(self, response: str) -> str:
        """Clean agent response to remove thinking patterns"""
        if not response:
            return response
        
        # Split into lines
        lines = response.split('\n')
        cleaned_lines = []
        skip_until_answer = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip thinking patterns
            if any(line_stripped.startswith(pattern) for pattern in [
                'The current language',
                'Action:',
                'Action Input:',
                'Observation:',
                'Thought:',
                '思考:',
                'I need to',
                'Let me',
                '用户',
                'Answer:'
            ]):
                # If we see "Answer:", extract what comes after
                if line_stripped.startswith('Answer:'):
                    answer_text = line_stripped[7:].strip()
                    if answer_text:
                        cleaned_lines.append(answer_text)
                skip_until_answer = True
                continue
            
            # Keep non-thinking lines
            if not skip_until_answer and line_stripped:
                cleaned_lines.append(line)
        
        # Join cleaned lines
        cleaned = '\n'.join(cleaned_lines).strip()
        
        # If we cleaned everything, return original
        if not cleaned:
            # Try to extract just the last line as it's often the answer
            last_line = lines[-1].strip() if lines else ""
            if last_line and not any(last_line.startswith(p) for p in ['Action:', 'Observation:']):
                return last_line
            return response
        
        return cleaned
    
    def _calculate_usage(self, output_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate token usage from output items"""
        text_tokens = 0
        tool_tokens = 0
        
        for item in output_items:
            if item['type'] == 'text':
                text_tokens += self._estimate_tokens(item['text'])
            elif item['type'] in ['tool_use', 'tool_result']:
                tool_tokens += self._estimate_tokens(json.dumps(item))
        
        total_tokens = text_tokens + tool_tokens
        
        return {
            "prompt_tokens": 0,  # Will be set by API
            "completion_tokens": total_tokens,
            "total_tokens": total_tokens,
            "reasoning_tokens": text_tokens,
            "tool_tokens": tool_tokens
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        if not text:
            return 0
        
        # Count Chinese characters
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        # Rough estimation
        return (chinese_chars // 2) + (other_chars // 4)