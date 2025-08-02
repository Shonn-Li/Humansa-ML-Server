"""
Direct O3 Client - Workaround for Azure SDK limitations
"""

import os
import httpx
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, ChatResponseGen, ChatResponseAsyncGen, MessageRole
from llama_index.core.llms import LLM
from llama_index.core.callbacks import CallbackManager
from pydantic import Field, PrivateAttr

logger = logging.getLogger(__name__)

class O3DirectClient(LLM):
    """
    Direct HTTP client for O3 models to work around Azure SDK limitations
    """
    
    # Define fields properly for Pydantic
    endpoint: str = Field(description="Azure endpoint URL")
    credential: str = Field(description="API key credential")
    model_name: str = Field(default="o3", description="Model name")
    max_tokens: int = Field(default=1000, description="Maximum tokens")
    
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
        callback_manager: Optional[CallbackManager] = None,
        **kwargs
    ):
        # Pass fields to parent init
        super().__init__(
            endpoint=endpoint.rstrip('/'),
            credential=credential,
            model_name=model_name,
            max_tokens=max_tokens,
            callback_manager=callback_manager,
            **kwargs
        )
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "endpoint": self.endpoint
        }
    
    @property
    def _model_kwargs(self) -> Dict[str, Any]:
        """Model kwargs for O3"""
        return {
            "model": self.model_name,
            "max_completion_tokens": self.max_tokens
        }
    
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
        """Convert LlamaIndex messages to API format"""
        result = []
        for msg in messages:
            role = "system" if msg.role == MessageRole.SYSTEM else msg.role.value
            result.append({"role": role, "content": msg.content})
        return result
    
    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Complete is not implemented for chat models"""
        raise NotImplementedError("Use chat() instead")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Sync chat"""
        client = self._get_client()
        
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "max_completion_tokens": kwargs.get("max_completion_tokens", self.max_tokens)
        }
        
        response = client.post(
            f"{self.endpoint}/chat/completions",
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"O3 API error: {response.status_code} - {response.text}")
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=content),
            raw=data
        )
    
    async def achat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Async chat"""
        client = self._get_async_client()
        
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "max_completion_tokens": kwargs.get("max_completion_tokens", self.max_tokens)
        }
        
        logger.debug(f"O3 Direct Client request: {json.dumps(payload, indent=2)}")
        
        response = await client.post(
            f"{self.endpoint}/chat/completions",
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"O3 API error: {response.status_code} - {response.text}")
            raise Exception(f"O3 API error: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Handle potential None content
        content = ""
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
        
        logger.debug(f"O3DirectClient: Chat response: {content[:50] if content else 'No content'}...")
        
        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=content),
            raw=data
        )
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        """Sync streaming - not implemented"""
        raise NotImplementedError("Use astream_chat() for streaming")
    
    async def astream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponseAsyncGen:
        """Async streaming chat"""
        client = self._get_async_client()
        
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "max_completion_tokens": kwargs.get("max_completion_tokens", self.max_tokens),
            "stream": True
        }
        
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
                
                async for line in response.aiter_lines():
                    if line.strip() and line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            logger.debug(f"O3DirectClient: Stream complete, {chunk_count} chunks")
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunk_count += 1
                                    logger.debug(f"O3DirectClient: Yielding chunk {chunk_count}: {content[:20]}...")
                                    yield ChatResponse(
                                        message=ChatMessage(role=MessageRole.ASSISTANT, content=""),
                                        delta=content,
                                        raw=chunk
                                    )
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