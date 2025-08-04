"""
Direct O3 Client - Uses Azure OpenAI Responses API for O3 reasoning

Supports O3/O4 models with:
- Reasoning effort control (low/medium/high)
- Reasoning summaries (detailed/concise)
- Streaming reasoning deltas
- Azure OpenAI Responses API integration
"""

import os
import httpx
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator, Literal
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, ChatResponseGen, ChatResponseAsyncGen, MessageRole
from llama_index.core.llms import LLM
from llama_index.core.callbacks import CallbackManager
from pydantic import Field, PrivateAttr

logger = logging.getLogger(__name__)

class O3DirectClient(LLM):
    """
    Direct HTTP client for O3 models to work around Azure SDK limitations
    
    Supports:
    - O3, O3-mini, O4-mini models
    - Reasoning effort parameter (low/medium/high)
    - Developer messages
    - Reasoning summaries
    """
    
    # Define fields properly for Pydantic
    endpoint: str = Field(description="Azure endpoint URL")
    credential: str = Field(description="API key credential")
    model_name: str = Field(default="o3", description="Model name")
    max_tokens: int = Field(default=1000, description="Maximum tokens")
    reasoning_effort: Literal["low", "medium", "high"] = Field(default="medium", description="Reasoning effort level")
    reasoning_summary: Literal["detailed", "concise", "none"] = Field(default="detailed", description="Reasoning summary level")
    
    # Private attributes for HTTP clients
    _client: Optional[httpx.Client] = PrivateAttr(default=None)
    _async_client: Optional[httpx.AsyncClient] = PrivateAttr(default=None)
    _use_responses_api: bool = PrivateAttr(default=True)
    
    @classmethod
    def class_name(cls) -> str:
        """Get class name."""
        return "O3DirectClient"
    
    def __init__(
        self,
        endpoint: str,
        credential: str,
        model_name: str = "o3",
        max_tokens: int = 1000,
        reasoning_effort: Literal["low", "medium", "high"] = "medium",
        reasoning_summary: Literal["detailed", "concise", "none"] = "detailed",
        callback_manager: Optional[CallbackManager] = None,
        **kwargs
    ):
        # Ensure endpoint has proper format for OpenAI Responses API
        if not endpoint.endswith('/openai/v1/'):
            endpoint = endpoint.rstrip('/') + '/openai/v1/'
        
        # Pass fields to parent init
        super().__init__(
            endpoint=endpoint,
            credential=credential,
            model_name=model_name,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            reasoning_summary=reasoning_summary,
            callback_manager=callback_manager,
            **kwargs
        )
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "endpoint": self.endpoint,
            "reasoning_effort": self.reasoning_effort,
            "reasoning_summary": self.reasoning_summary
        }
    
    @property
    def _model_kwargs(self) -> Dict[str, Any]:
        """Model kwargs for O3"""
        kwargs = {
            "model": self.model_name,
            "max_completion_tokens": self.max_tokens
        }
        
        # Only add reasoning_effort for O3/O4 models
        if self.model_name.lower() in ["o3", "o3-mini", "o4-mini"]:
            kwargs["reasoning_effort"] = self.reasoning_effort
            
        return kwargs
    
    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers={"api-key": self.credential},
                params={"api-version": "preview"},
                timeout=300.0  # 5 minutes for O3 reasoning models
            )
        return self._client
    
    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                headers={"api-key": self.credential},
                params={"api-version": "preview"},
                timeout=300.0  # 5 minutes for O3 reasoning models
            )
        return self._async_client
    
    def _convert_messages_to_input(self, messages: List[ChatMessage]) -> Any:
        """Convert LlamaIndex messages to Responses API input format
        
        The Responses API accepts either a string or list of messages
        """
        # For single user message, return as string
        if len(messages) == 1 and messages[0].role == MessageRole.USER:
            return messages[0].content
        
        # Otherwise, return as list of role/content dicts
        result = []
        is_o3_model = self.model_name.lower() in ["o3", "o3-mini", "o4-mini"]
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # O3/O4 models use 'developer' instead of 'system'
                role = "developer" if is_o3_model else "system"
            else:
                role = msg.role.value
                
            result.append({"role": role, "content": msg.content})
        return result
    
    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Complete is not implemented for chat models"""
        raise NotImplementedError("Use chat() instead")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Sync chat using Azure OpenAI Responses API"""
        client = self._get_client()
        
        # Convert messages to input format
        input_data = self._convert_messages_to_input(messages)
        
        # Build reasoning config
        reasoning_config = {
            "effort": self.reasoning_effort,
            "summary": self.reasoning_summary
        }
        
        # Build payload for Responses API
        payload = {
            "model": self.model_name,
            "input": input_data,
            "max_output_tokens": kwargs.get("max_output_tokens", self.max_tokens)
        }
        
        # Add reasoning config if not disabled
        if self.reasoning_summary != "none":
            payload["reasoning"] = reasoning_config
        
        response = client.post(
            f"{self.endpoint}responses",
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"O3 API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract output and reasoning summary
        content = data.get("output", "")
        reasoning_summary = data.get("reasoning_summary", "")
        
        if reasoning_summary:
            logger.info(f"🧠 O3 reasoning summary: {reasoning_summary[:200]}...")
        
        response_obj = ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=content),
            raw=data
        )
        
        # Store reasoning summary in additional_kwargs if present
        if reasoning_summary:
            response_obj.message.additional_kwargs = {"reasoning_summary": reasoning_summary}
            
        return response_obj
    
    async def achat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Async chat using Azure OpenAI Responses API"""
        client = self._get_async_client()
        
        # Convert messages to input format
        input_data = self._convert_messages_to_input(messages)
        
        # Build reasoning config
        reasoning_config = {
            "effort": self.reasoning_effort,
            "summary": self.reasoning_summary
        }
        
        # Build payload for Responses API
        payload = {
            "model": self.model_name,
            "input": input_data,
            "max_output_tokens": kwargs.get("max_output_tokens", self.max_tokens)
        }
        
        # Add reasoning config if not disabled
        if self.reasoning_summary != "none":
            payload["reasoning"] = reasoning_config
        
        logger.info(f"🚀 O3DirectClient Responses API request:")
        logger.info(f"  Model: {self.model_name}")
        logger.info(f"  Reasoning: {reasoning_config}")
        logger.info(f"  Max tokens: {payload.get('max_output_tokens')}")
        
        response = await client.post(
            f"{self.endpoint}responses",
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"O3 API error: {response.status_code} - {response.text}")
            raise Exception(f"O3 API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract output and reasoning summary
        content = data.get("output", "")
        reasoning_summary = data.get("reasoning_summary", "")
        
        if reasoning_summary:
            logger.info(f"🧠 O3 reasoning summary: {reasoning_summary[:200]}...")
        
        logger.debug(f"O3DirectClient: Chat response: {content[:50] if content else 'No content'}...")
        
        response_obj = ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=content),
            raw=data
        )
        
        # Store reasoning summary in additional_kwargs if present
        if reasoning_summary:
            response_obj.message.additional_kwargs = {"reasoning_summary": reasoning_summary}
            
        return response_obj
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        """Sync streaming - not implemented"""
        raise NotImplementedError("Use astream_chat() for streaming")
    
    async def astream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponseAsyncGen:
        """Async streaming chat using Azure OpenAI Responses API"""
        client = self._get_async_client()
        
        # Convert messages to input format
        input_data = self._convert_messages_to_input(messages)
        
        # Build reasoning config
        reasoning_config = {
            "effort": self.reasoning_effort,
            "summary": self.reasoning_summary
        }
        
        # Build payload for Responses API
        payload = {
            "model": self.model_name,
            "input": input_data,
            "max_output_tokens": kwargs.get("max_output_tokens", self.max_tokens),
            "stream": True
        }
        
        # Add reasoning config if not disabled
        if self.reasoning_summary != "none":
            payload["reasoning"] = reasoning_config
        
        # Log the request for O3 debugging
        logger.info(f"🚀 O3DirectClient using Azure Responses API:")
        logger.info(f"  Model: {self.model_name}")
        logger.info(f"  Reasoning: {reasoning_config}")
        logger.info(f"  Max tokens: {payload.get('max_output_tokens')}")
        logger.info(f"  Endpoint: {self.endpoint}responses")
        logger.info(f"  Full payload: {json.dumps(payload, indent=2)}")
        
        async def stream_generator():
            # Initialize variables outside the try block so they're accessible in exception handlers
            accumulated_content = ""
            accumulated_reasoning = ""
            event_count = 0
            yielded_final = False
            
            try:
                async with client.stream(
                    "POST",
                    f"{self.endpoint}responses",
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"O3 API error: {response.status_code} - {error_text.decode()}")
                    
                    logger.debug(f"O3DirectClient: Starting Responses API stream")
                    last_event_time = None
                    
                    try:
                        async for line in response.aiter_lines():
                            line_stripped = line.strip()
                            if not line_stripped:
                                continue  # Skip empty lines
                            
                            if line_stripped.startswith("data: "):
                                data_str = line_stripped[6:]  # Remove "data: " prefix
                                if data_str == "[DONE]":
                                    logger.info(f"O3DirectClient: [DONE] marker received after {event_count} events")
                                    # Yield final response with complete content and reasoning (if any)
                                    if accumulated_content or accumulated_reasoning:
                                        logger.info(f"O3DirectClient: Final response - content: {len(accumulated_content)} chars, reasoning: {len(accumulated_reasoning)} chars")
                                        final_response = ChatResponse(
                                            message=ChatMessage(
                                                role=MessageRole.ASSISTANT, 
                                                content=accumulated_content,
                                                additional_kwargs={"reasoning_summary": accumulated_reasoning} if accumulated_reasoning else {}
                                            ),
                                            raw={
                                                "event_type": "done",
                                                "content": accumulated_content,
                                                "reasoning_summary": accumulated_reasoning if accumulated_reasoning else None
                                            }
                                        )
                                        yield final_response
                                        yielded_final = True
                                    break
                                
                                try:
                                    event = json.loads(data_str)
                                    event_count += 1
                                    
                                    # Get event type from the event structure
                                    event_type = event.get("type", "unknown")
                                    
                                    # Log more events for debugging (increased from 10 to 50)
                                    if event_count <= 50 or "done" in event_type.lower() or "completed" in event_type.lower():
                                        logger.info(f"🔍 Event {event_count}: {event_type}")
                                        if event_count <= 5 or "error" in event_type.lower():
                                            logger.debug(f"Event structure: {json.dumps(event, indent=2)[:500]}...")
                                    
                                    # Handle reasoning summary text delta events
                                    if event_type == "response.reasoning_summary_text.delta":
                                        reasoning_delta = event.get("delta", "")
                                        if reasoning_delta:
                                            accumulated_reasoning += reasoning_delta
                                            # Stream reasoning as a special chunk
                                            logger.info(f"🧠 Reasoning delta: {reasoning_delta[:50]}...")
                                            yield ChatResponse(
                                                message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                delta="",  # Empty content delta
                                                raw={
                                                    "reasoning_delta": reasoning_delta,
                                                    "event_type": "reasoning"
                                                }
                                            )
                                    
                                    # Handle reasoning summary text done event
                                    elif event_type == "response.reasoning_summary_text.done":
                                        logger.info(f"O3DirectClient: Reasoning summary text done event received")
                                        # After reasoning is done, we should expect output text events
                                        # Log the complete reasoning summary if available
                                        if "text" in event:
                                            complete_reasoning = event["text"]
                                            logger.info(f"🧠 Complete reasoning summary: {complete_reasoning[:200]}...")
                                            accumulated_reasoning = complete_reasoning
                                    
                                    # Handle reasoning summary part done event
                                    elif event_type == "response.reasoning_summary_part.done":
                                        logger.info(f"O3DirectClient: Reasoning summary part done event received")
                                    
                                    # Handle output item events that might trigger content
                                    elif event_type == "response.output_item.added":
                                        logger.info(f"O3DirectClient: Output item added event")
                                        if "item" in event and isinstance(event["item"], dict):
                                            item = event["item"]
                                            logger.debug(f"Output item type: {item.get('type')}, id: {item.get('id')}")
                                    
                                    # Handle output item done events
                                    elif event_type == "response.output_item.done":
                                        logger.info(f"O3DirectClient: Output item done event")
                                        if "item" in event and isinstance(event["item"], dict):
                                            item = event["item"]
                                            item_type = item.get("type")
                                            logger.debug(f"Output item done - type: {item_type}")
                                            
                                            # Check if this is a message item
                                            if item_type == "message" and "content" in item:
                                                content = item.get("content", [])
                                                if isinstance(content, list):
                                                    for content_item in content:
                                                        if isinstance(content_item, dict) and "text" in content_item:
                                                            text = content_item["text"]
                                                            if text and text not in accumulated_content:
                                                                logger.info(f"O3DirectClient: Found text in output item: {text[:100]}...")
                                                                accumulated_content = text
                                                                # Yield the complete content
                                                                yield ChatResponse(
                                                                    message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                                    delta=text,
                                                                    raw={
                                                                        "event_type": "content",
                                                                        "source": "output_item_done"
                                                                    }
                                                                )
                                    
                                    # Handle content part added events
                                    elif event_type == "response.content_part.added":
                                        logger.info(f"O3DirectClient: Content part added event")
                                        if "part" in event and isinstance(event["part"], dict):
                                            part = event["part"]
                                            part_type = part.get("type")
                                            logger.debug(f"Content part type: {part_type}, content: {json.dumps(part)[:200]}...")
                                    
                                    # Handle output text delta events
                                    elif event_type == "response.output_text.delta":
                                        content_delta = event.get("delta", "")
                                        if content_delta:
                                            accumulated_content += content_delta
                                            logger.info(f"O3DirectClient: Content chunk {event_count}: {content_delta[:50]}...")
                                            yield ChatResponse(
                                                message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                delta=content_delta,
                                                raw={
                                                    "event_type": "content"
                                                }
                                            )
                                            logger.debug(f"O3DirectClient: Successfully yielded content chunk {event_count}")
                                    
                                    # Handle output text done event (might contain final text)
                                    elif event_type == "response.output_text.done":
                                        logger.debug(f"O3DirectClient: Output text done event received")
                                        # Check if event contains the complete text
                                        if "text" in event:
                                            final_text = event["text"]
                                            if final_text and final_text != accumulated_content:
                                                logger.info(f"O3DirectClient: Final text from done event: {final_text[:100]}...")
                                                # Update accumulated content
                                                accumulated_content = final_text
                                    
                                    # Handle content part done event
                                    elif event_type == "response.content_part.done":
                                        logger.info(f"O3DirectClient: Content part done event received")
                                        # Check for any final content in the part
                                        if "part" in event and isinstance(event["part"], dict):
                                            part = event["part"]
                                            part_type = part.get("type")
                                            logger.debug(f"Content part done - type: {part_type}, full part: {json.dumps(part)[:500]}...")
                                            
                                            # Handle text type parts
                                            if part_type == "text" and "text" in part:
                                                final_text = part["text"]
                                                if final_text and final_text != accumulated_content:
                                                    logger.info(f"O3DirectClient: Final text from content part: {final_text[:100]}...")
                                                    accumulated_content = final_text
                                                    # Yield the complete text
                                                    yield ChatResponse(
                                                        message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                        delta=final_text,
                                                        raw={
                                                            "event_type": "content",
                                                            "source": "content_part_done"
                                                        }
                                                    )
                                    
                                    # Handle completed event (sometimes comes before done)
                                    elif event_type == "response.completed":
                                        logger.debug(f"O3DirectClient: Response completed event received")
                                        # Continue to wait for done event
                                    
                                    # Handle done event
                                    elif event_type == "response.done":
                                        logger.info(f"O3DirectClient: Response done event received")
                                        logger.debug(f"Full done event structure: {json.dumps(event)[:1000]}...")
                                        
                                        # Check if event contains final response data
                                        if "response" in event and isinstance(event["response"], dict):
                                            response_data = event["response"]
                                            
                                            # Check for output in response (might be at top level)
                                            if "output" in response_data:
                                                final_output = response_data["output"]
                                                if isinstance(final_output, str) and final_output:
                                                    if final_output != accumulated_content:
                                                        logger.info(f"O3DirectClient: Final output string from done event: {final_output[:100]}...")
                                                        accumulated_content = final_output
                                                        # Yield the final content
                                                        yield ChatResponse(
                                                            message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                            delta=final_output,
                                                            raw={
                                                                "event_type": "content",
                                                                "source": "response_done"
                                                            }
                                                        )
                                                elif isinstance(final_output, list) and final_output:
                                                    # Handle list of outputs
                                                    for output_item in final_output:
                                                        if isinstance(output_item, dict):
                                                            # Check for direct text field
                                                            if "text" in output_item:
                                                                text_content = output_item["text"]
                                                                if text_content and text_content != accumulated_content:
                                                                    accumulated_content = text_content
                                                                    logger.info(f"O3DirectClient: Final text from output item: {text_content[:100]}...")
                                                                    yield ChatResponse(
                                                                        message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                                        delta=text_content,
                                                                        raw={
                                                                            "event_type": "content",
                                                                            "source": "response_done_list"
                                                                        }
                                                                    )
                                                            # Check for content field with nested structure
                                                            elif "content" in output_item:
                                                                for content_item in output_item["content"]:
                                                                    if isinstance(content_item, dict) and "text" in content_item:
                                                                        accumulated_content = content_item["text"]
                                                                        logger.info(f"O3DirectClient: Final text from output list: {accumulated_content[:100]}...")
                                            
                                            # Also check for output_items array (Azure Responses API format)
                                            if "output_items" in response_data and isinstance(response_data["output_items"], list):
                                                for item in response_data["output_items"]:
                                                    if isinstance(item, dict):
                                                        item_type = item.get("type")
                                                        if item_type == "text" and "text" in item:
                                                            text_content = item["text"]
                                                            if text_content and text_content != accumulated_content:
                                                                accumulated_content = text_content
                                                                logger.info(f"O3DirectClient: Final text from output_items: {text_content[:100]}...")
                                                                yield ChatResponse(
                                                                    message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                                    delta=text_content,
                                                                    raw={
                                                                        "event_type": "content",
                                                                        "source": "response_done_output_items"
                                                                    }
                                                                )
                                            
                                            # Check for reasoning summary in response
                                            if "reasoning_summary" in response_data and response_data["reasoning_summary"]:
                                                accumulated_reasoning = response_data["reasoning_summary"]
                                                logger.info(f"🧠 O3 reasoning summary from done event: {accumulated_reasoning[:200]}...")
                                        
                                        # Also check for output at the top level of the event
                                        if "output" in event:
                                            top_level_output = event["output"]
                                            if isinstance(top_level_output, str) and top_level_output and top_level_output != accumulated_content:
                                                accumulated_content = top_level_output
                                                logger.info(f"O3DirectClient: Final output from top-level: {top_level_output[:100]}...")
                                                yield ChatResponse(
                                                    message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                                    delta=top_level_output,
                                                    raw={
                                                        "event_type": "content",
                                                        "source": "event_top_level"
                                                    }
                                                )
                                        
                                        # Mark that we've seen the done event but don't break yet
                                        # Let the stream close naturally
                                        logger.info(f"O3DirectClient: Marked done event, accumulated content: {len(accumulated_content)} chars")
                                    
                                    # Log any unhandled event types
                                    else:
                                        if event_count <= 30:  # Log first 30 unhandled events
                                            logger.info(f"O3DirectClient: Unhandled event type: {event_type}")
                                            # Log more details for debugging
                                            if "item" in event or "part" in event or "output" in event or "content" in event:
                                                logger.debug(f"Event details: {json.dumps(event)[:300]}...")
                                    
                                except json.JSONDecodeError as e:
                                    logger.warning(f"O3DirectClient: Failed to parse event: {e}")
                                    continue
                    
                    except httpx.StreamClosed as e:
                        # Stream closed - could be normal or due to timeout
                        logger.warning(f"O3DirectClient: Stream closed after {event_count} events - this may be due to timeout if response is incomplete")
                        logger.debug(f"StreamClosed details: {e}")
                        pass
                    except httpx.TimeoutException as e:
                        # Explicit timeout
                        logger.error(f"O3DirectClient: Request timed out after {event_count} events - consider increasing timeout for O3 models")
                        logger.error(f"Timeout details: {e}")
                        # Continue to yield accumulated content
                    
                    # If we exit the loop without yielding final content, yield what we have
                    if not yielded_final and (accumulated_content or accumulated_reasoning):
                        logger.info(f"O3DirectClient: Yielding final content/reasoning after stream close")
                        yield ChatResponse(
                            message=ChatMessage(
                                role=MessageRole.ASSISTANT, 
                                content=accumulated_content,
                                additional_kwargs={"reasoning_summary": accumulated_reasoning} if accumulated_reasoning else {}
                            ),
                            raw={
                                "event_type": "stream_ended",
                                "content": accumulated_content,
                                "reasoning": accumulated_reasoning
                            }
                        )
            except Exception as e:
                logger.error(f"O3DirectClient: Stream error: {e}", exc_info=True)
                # Yield any accumulated content before raising
                if accumulated_content:
                    yield ChatResponse(
                        message=ChatMessage(
                            role=MessageRole.ASSISTANT, 
                            content=accumulated_content,
                            additional_kwargs={"error": str(e)}
                        ),
                        raw={
                            "event_type": "error",
                            "error": str(e),
                            "content": accumulated_content
                        }
                    )
                raise
        
        return stream_generator()
    
    async def acomplete(self, prompt: str, **kwargs: Any) -> str:
        """Async complete is not implemented for chat models"""
        raise NotImplementedError("Use achat() instead")
    
    def stream_complete(self, prompt: str, **kwargs: Any):
        """Stream complete is not implemented for chat models"""
        raise NotImplementedError("Use stream_chat() instead")
    
    async def astream_complete(self, prompt: str, **kwargs: Any):
        """Async stream complete is not implemented for chat models"""
        raise NotImplementedError("Use astream_chat() instead")
    
    def __del__(self):
        """Cleanup clients"""
        if hasattr(self, '_client') and self._client:
            self._client.close()
        if hasattr(self, '_async_client') and self._async_client:
            # Note: Can't await in __del__, so we just let it be garbage collected
            pass