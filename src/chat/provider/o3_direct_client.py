"""
Direct O3 Client - Workaround for Azure SDK limitations

Supports O3/O4 models with:
- Reasoning effort control (low/medium/high)
- Developer messages instead of system messages
- Reasoning summaries in responses
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
    
    # Private attributes for HTTP clients
    _client: Optional[httpx.Client] = PrivateAttr(default=None)
    _async_client: Optional[httpx.AsyncClient] = PrivateAttr(default=None)
    
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
        callback_manager: Optional[CallbackManager] = None,
        **kwargs
    ):
        # Pass fields to parent init
        super().__init__(
            endpoint=endpoint.rstrip('/'),
            credential=credential,
            model_name=model_name,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            callback_manager=callback_manager,
            **kwargs
        )
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "endpoint": self.endpoint,
            "reasoning_effort": self.reasoning_effort
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
                timeout=60.0
            )
        return self._client
    
    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                headers={"api-key": self.credential},
                timeout=60.0
            )
        return self._async_client
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert LlamaIndex messages to API format
        
        O3/O4 models use 'developer' role instead of 'system'
        """
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
        """Sync chat"""
        client = self._get_client()
        
        # Build payload with model-specific kwargs
        payload = {
            "messages": self._convert_messages(messages),
            **self._model_kwargs
        }
        
        # Override with any provided kwargs
        if "max_completion_tokens" in kwargs:
            payload["max_completion_tokens"] = kwargs["max_completion_tokens"]
        if "reasoning_effort" in kwargs:
            payload["reasoning_effort"] = kwargs["reasoning_effort"]
        
        response = client.post(
            f"{self.endpoint}/chat/completions",
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"O3 API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract content and reasoning summary
        choice = data["choices"][0]
        message = choice["message"]
        content = message.get("content", "")
        
        # Check for reasoning summary (if available in response)
        reasoning_summary = None
        if "reasoning_summary" in message:
            reasoning_summary = message["reasoning_summary"]
            logger.info(f"🧠 O3 reasoning summary: {reasoning_summary[:100]}...")
        
        response_obj = ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=content),
            raw=data
        )
        
        # Store reasoning summary in additional_kwargs if present
        if reasoning_summary:
            response_obj.message.additional_kwargs = {"reasoning_summary": reasoning_summary}
            
        return response_obj
    
    async def achat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Async chat"""
        client = self._get_async_client()
        
        # Build payload with model-specific kwargs
        payload = {
            "messages": self._convert_messages(messages),
            **self._model_kwargs
        }
        
        # Override with any provided kwargs
        if "max_completion_tokens" in kwargs:
            payload["max_completion_tokens"] = kwargs["max_completion_tokens"]
        if "reasoning_effort" in kwargs:
            payload["reasoning_effort"] = kwargs["reasoning_effort"]
        
        logger.debug(f"O3 Direct Client request: {json.dumps(payload, indent=2)}")
        
        response = await client.post(
            f"{self.endpoint}/chat/completions",
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"O3 API error: {response.status_code} - {response.text}")
            raise Exception(f"O3 API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract content and reasoning summary
        content = ""
        reasoning_summary = None
        
        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")
            
            # Check for reasoning summary
            if "reasoning_summary" in message:
                reasoning_summary = message["reasoning_summary"]
                logger.info(f"🧠 O3 reasoning summary: {reasoning_summary[:100]}...")
        
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
        """Async streaming chat"""
        client = self._get_async_client()
        
        # Build payload with model-specific kwargs
        payload = {
            "messages": self._convert_messages(messages),
            **self._model_kwargs,
            "stream": True
        }
        
        # Override with any provided kwargs
        if "max_completion_tokens" in kwargs:
            payload["max_completion_tokens"] = kwargs["max_completion_tokens"]
        if "reasoning_effort" in kwargs:
            payload["reasoning_effort"] = kwargs["reasoning_effort"]
        
        async def stream_generator():
            async with client.stream(
                "POST",
                f"{self.endpoint}/chat/completions",
                json=payload
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"O3 API error: {response.status_code}")
                
                logger.debug(f"O3DirectClient: Starting stream response")
                chunk_count = 0
                
                accumulated_content = ""
                reasoning_summary = None
                
                async for line in response.aiter_lines():
                    if line.strip() and line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            logger.debug(f"O3DirectClient: Stream complete, {chunk_count} chunks")
                            # Yield final response with reasoning summary if available
                            if reasoning_summary:
                                logger.info(f"🧠 O3 streaming reasoning summary: {reasoning_summary[:100]}...")
                                final_response = ChatResponse(
                                    message=ChatMessage(
                                        role=MessageRole.ASSISTANT, 
                                        content=accumulated_content,
                                        additional_kwargs={"reasoning_summary": reasoning_summary}
                                    ),
                                    raw={"reasoning_summary": reasoning_summary}
                                )
                                yield final_response
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            if "choices" in chunk and chunk["choices"]:
                                choice = chunk["choices"][0]
                                delta = choice.get("delta", {})
                                
                                # Check for content
                                content = delta.get("content", "")
                                if content:
                                    chunk_count += 1
                                    accumulated_content += content
                                    logger.debug(f"O3DirectClient: Yielding chunk {chunk_count}: {content[:20]}...")
                                    yield ChatResponse(
                                        message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                        delta=content,
                                        raw=chunk
                                    )
                                
                                # Check for reasoning summary in delta or message
                                if "reasoning_summary" in delta:
                                    reasoning_summary = delta["reasoning_summary"]
                                elif "message" in choice and "reasoning_summary" in choice["message"]:
                                    reasoning_summary = choice["message"]["reasoning_summary"]
                                    
                        except json.JSONDecodeError as e:
                            logger.warning(f"O3DirectClient: Failed to parse chunk: {e}")
                            continue
        
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