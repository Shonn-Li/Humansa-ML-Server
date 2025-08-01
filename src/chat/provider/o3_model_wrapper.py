"""
O3/O4 Model Wrapper for Azure AI Inference

This wrapper handles the special requirements for O3 and O4 models:
1. Converts max_tokens to max_completion_tokens
2. Removes temperature parameter (must use default of 1.0)
3. Handles streaming properly
"""

import logging
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, CompletionResponse
from llama_index.llms.azure_inference import AzureAICompletionsModel
from llama_index.core.callbacks import CallbackManager
import json

logger = logging.getLogger(__name__)

class O3ModelWrapper(AzureAICompletionsModel):
    """
    Wrapper for O3/O4 models that handles their special parameter requirements
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the wrapper"""
        # Store original model name before calling super()
        model_name = kwargs.get('model_name', '')
        is_o3 = self._is_o3_model_static(model_name)
        
        # Remove temperature for O3/O4 models
        if is_o3 and 'temperature' in kwargs:
            logger.info(f"Removing temperature parameter for {model_name}")
            kwargs.pop('temperature')
            
        super().__init__(*args, **kwargs)
        
        # Set attributes after parent initialization
        self._original_model = model_name
        self._is_o3 = is_o3
    
    @staticmethod
    def _is_o3_model_static(model_name: str) -> bool:
        """Check if this is an O3 or O4 model"""
        if not model_name:
            return False
        model_lower = model_name.lower()
        return any(m in model_lower for m in ['o3', 'o4-mini', 'o4'])
    
    def _prepare_chat_params(self, **kwargs) -> Dict[str, Any]:
        """Prepare parameters for chat completion"""
        params = super()._prepare_chat_params(**kwargs)
        
        if self._is_o3:
            # Convert max_tokens to max_completion_tokens
            if 'max_tokens' in params:
                params['max_completion_tokens'] = params.pop('max_tokens')
                logger.debug(f"Converted max_tokens to max_completion_tokens for {self._original_model}")
            
            # Remove temperature (O3/O4 only support default of 1.0)
            if 'temperature' in params:
                params.pop('temperature')
                logger.debug(f"Removed temperature parameter for {self._original_model}")
        
        return params
    
    async def achat(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Async chat with parameter adjustment for O3/O4"""
        # Adjust parameters for O3/O4
        if self._is_o3:
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
            if 'temperature' in kwargs:
                kwargs.pop('temperature')
        
        return await super().achat(messages, **kwargs)
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Sync chat with parameter adjustment for O3/O4"""
        # Adjust parameters for O3/O4
        if self._is_o3:
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
            if 'temperature' in kwargs:
                kwargs.pop('temperature')
        
        return super().chat(messages, **kwargs)
    
    async def astream_chat(self, messages: List[ChatMessage], **kwargs) -> AsyncGenerator:
        """Async streaming chat with parameter adjustment for O3/O4"""
        # Adjust parameters for O3/O4
        if self._is_o3:
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
            if 'temperature' in kwargs:
                kwargs.pop('temperature')
        
        async for chunk in super().astream_chat(messages, **kwargs):
            yield chunk
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs):
        """Sync streaming chat with parameter adjustment for O3/O4"""
        # Adjust parameters for O3/O4
        if self._is_o3:
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
            if 'temperature' in kwargs:
                kwargs.pop('temperature')
        
        return super().stream_chat(messages, **kwargs)
    
    # Override the internal method that prepares API requests
    def _prepare_payload(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Prepare the API payload with O3/O4 adjustments"""
        # Get base payload
        payload = {
            "messages": messages,
            "model": self.model_name,
            **kwargs
        }
        
        if self._is_o3:
            # Convert max_tokens to max_completion_tokens
            if 'max_tokens' in payload:
                payload['max_completion_tokens'] = payload.pop('max_tokens')
            
            # Remove temperature
            if 'temperature' in payload:
                payload.pop('temperature')
            
            logger.debug(f"Adjusted payload for {self._original_model}: {json.dumps(payload, indent=2)}")
        
        return payload


def create_azure_llm_with_o3_support(
    endpoint: str,
    credential: str,
    model_name: str,
    temperature: float = 0.7,
    callback_manager: Optional[CallbackManager] = None,
    **kwargs
) -> Union[AzureAICompletionsModel, O3ModelWrapper]:
    """
    Factory function to create the appropriate Azure LLM instance
    
    Returns O3ModelWrapper for O3/O4 models, regular AzureAICompletionsModel otherwise
    """
    is_o3_model = O3ModelWrapper._is_o3_model_static(model_name)
    
    if is_o3_model:
        logger.info(f"Creating O3ModelWrapper for {model_name}")
        return O3ModelWrapper(
            endpoint=endpoint,
            credential=credential,
            model_name=model_name,
            callback_manager=callback_manager,
            **kwargs
        )
    else:
        # Regular Azure model
        return AzureAICompletionsModel(
            endpoint=endpoint,
            credential=credential,
            model_name=model_name,
            temperature=temperature,
            callback_manager=callback_manager,
            **kwargs
        )