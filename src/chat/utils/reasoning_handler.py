"""
Unified Reasoning Handler for all LLM providers

This module provides a consistent interface for handling reasoning across different providers:
- DeepSeek: Direct API uses reasoning_content field, Azure uses <think> blocks
- O3/O4: Uses reasoning summaries with reasoning_effort parameter
- O1: Uses structured reasoning events (future support)
"""

import logging
from typing import Dict, List, Tuple, Optional, Any, AsyncGenerator
from enum import Enum
from dataclasses import dataclass

from .think_block_parser import ThinkBlockParser
from ..provider.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning formats"""
    STREAMING_FIELD = "streaming_field"      # DeepSeek direct API (reasoning_content field)
    EMBEDDED_TOKENS = "embedded_tokens"      # Azure DeepSeek (<think> blocks)
    SUMMARY = "summary"                      # O3/O4 (reasoning summaries)
    STRUCTURED_EVENTS = "structured_events"  # O1 models (future)
    NONE = "none"                           # No reasoning support


@dataclass
class ReasoningConfig:
    """Configuration for a model's reasoning capabilities"""
    reasoning_type: ReasoningType
    supports_streaming: bool
    effort_parameter: Optional[str] = None  # e.g., "reasoning_effort" for O3
    effort_levels: Optional[List[str]] = None  # e.g., ["low", "medium", "high"]


class ReasoningHandler:
    """
    Unified handler for reasoning across all LLM providers
    """
    
    # Model reasoning configurations
    MODEL_CONFIGS = {
        # DeepSeek models
        "deepseek-reasoner": ReasoningConfig(
            reasoning_type=ReasoningType.STREAMING_FIELD,
            supports_streaming=True
        ),
        "deepseek-r1": ReasoningConfig(
            reasoning_type=ReasoningType.STREAMING_FIELD,
            supports_streaming=True
        ),
        "deepseek-r1-0528": ReasoningConfig(
            reasoning_type=ReasoningType.EMBEDDED_TOKENS,  # Azure version
            supports_streaming=True
        ),
        "deepseek-v3-0324": ReasoningConfig(
            reasoning_type=ReasoningType.NONE,  # V3 doesn't have reasoning
            supports_streaming=False
        ),
        
        # O3/O4 models
        "o3": ReasoningConfig(
            reasoning_type=ReasoningType.SUMMARY,
            supports_streaming=False,
            effort_parameter="reasoning_effort",
            effort_levels=["low", "medium", "high"]
        ),
        "o3-mini": ReasoningConfig(
            reasoning_type=ReasoningType.SUMMARY,
            supports_streaming=False,
            effort_parameter="reasoning_effort",
            effort_levels=["low", "medium", "high"]
        ),
        "o4-mini": ReasoningConfig(
            reasoning_type=ReasoningType.SUMMARY,
            supports_streaming=False,
            effort_parameter="reasoning_effort",
            effort_levels=["low", "medium", "high"]
        ),
        
        # O1 models (future support)
        "o1": ReasoningConfig(
            reasoning_type=ReasoningType.STRUCTURED_EVENTS,
            supports_streaming=True
        ),
        "o1-mini": ReasoningConfig(
            reasoning_type=ReasoningType.STRUCTURED_EVENTS,
            supports_streaming=True
        ),
        "o1-preview": ReasoningConfig(
            reasoning_type=ReasoningType.STRUCTURED_EVENTS,
            supports_streaming=True
        ),
    }
    
    def __init__(self):
        self.think_parsers: Dict[str, ThinkBlockParser] = {}
    
    def get_reasoning_config(self, model: str, provider: LLMProvider) -> ReasoningConfig:
        """Get reasoning configuration for a model"""
        model_lower = model.lower()
        
        # Check exact match first
        if model_lower in self.MODEL_CONFIGS:
            config = self.MODEL_CONFIGS[model_lower]
            
            # Override for Azure DeepSeek models
            if provider == LLMProvider.AZURE_INFERENCE and model_lower.startswith("deepseek"):
                # Azure uses embedded tokens for all DeepSeek reasoning models
                if config.reasoning_type == ReasoningType.STREAMING_FIELD:
                    return ReasoningConfig(
                        reasoning_type=ReasoningType.EMBEDDED_TOKENS,
                        supports_streaming=True
                    )
            
            return config
        
        # Check prefix matches
        for model_key, config in self.MODEL_CONFIGS.items():
            if model_lower.startswith(model_key):
                # Override for Azure DeepSeek
                if provider == LLMProvider.AZURE_INFERENCE and "deepseek" in model_lower:
                    if config.reasoning_type == ReasoningType.STREAMING_FIELD:
                        return ReasoningConfig(
                            reasoning_type=ReasoningType.EMBEDDED_TOKENS,
                            supports_streaming=True
                        )
                return config
        
        # Default: no reasoning support
        return ReasoningConfig(reasoning_type=ReasoningType.NONE, supports_streaming=False)
    
    def create_parser(self, session_id: str, model: str, provider: LLMProvider) -> Optional[ThinkBlockParser]:
        """Create a parser for embedded token reasoning if needed"""
        config = self.get_reasoning_config(model, provider)
        
        if config.reasoning_type == ReasoningType.EMBEDDED_TOKENS:
            if session_id not in self.think_parsers:
                self.think_parsers[session_id] = ThinkBlockParser()
            return self.think_parsers[session_id]
        
        return None
    
    def extract_reasoning_from_response(
        self, 
        response_text: str, 
        model: str, 
        provider: LLMProvider,
        response_obj: Optional[Any] = None
    ) -> Tuple[str, List[str]]:
        """
        Extract reasoning from a non-streaming response
        
        Returns:
            Tuple of (clean_response_text, reasoning_blocks)
        """
        config = self.get_reasoning_config(model, provider)
        
        if config.reasoning_type == ReasoningType.EMBEDDED_TOKENS:
            # Extract <think> blocks
            clean_text, reasoning_blocks = ThinkBlockParser.extract_all_think_blocks(response_text)
            return clean_text, reasoning_blocks
        
        elif config.reasoning_type == ReasoningType.SUMMARY and response_obj:
            # Check for reasoning summary in response object
            reasoning_blocks = []
            if hasattr(response_obj, 'message') and hasattr(response_obj.message, 'additional_kwargs'):
                kwargs = response_obj.message.additional_kwargs
                if kwargs and "reasoning_summary" in kwargs:
                    reasoning_blocks = [kwargs["reasoning_summary"]]
            
            return response_text, reasoning_blocks
        
        # No reasoning to extract
        return response_text, []
    
    def process_streaming_chunk(
        self,
        chunk: Any,
        model: str,
        provider: LLMProvider,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process a streaming chunk for reasoning content
        
        Returns:
            Dict with keys:
            - has_reasoning: bool
            - reasoning_content: Optional[str]
            - regular_content: Optional[str]
            - reasoning_type: str (chunk/summary)
        """
        config = self.get_reasoning_config(model, provider)
        result = {
            "has_reasoning": False,
            "reasoning_content": None,
            "regular_content": None,
            "reasoning_type": None
        }
        
        # Handle embedded tokens (Azure DeepSeek)
        if config.reasoning_type == ReasoningType.EMBEDDED_TOKENS:
            parser = self.create_parser(session_id, model, provider)
            if parser and hasattr(chunk, 'delta') and chunk.delta:
                regular, reasoning, has_reasoning = parser.process_chunk(chunk.delta)
                result["regular_content"] = regular if regular else None
                result["reasoning_content"] = reasoning if reasoning else None
                result["has_reasoning"] = has_reasoning
                result["reasoning_type"] = "chunk"
        
        # Handle streaming field (Direct DeepSeek API)
        elif config.reasoning_type == ReasoningType.STREAMING_FIELD:
            if hasattr(chunk, 'raw') and chunk.raw:
                raw_chunk = chunk.raw
                if hasattr(raw_chunk, 'choices') and raw_chunk.choices:
                    choice = raw_chunk.choices[0]
                    if hasattr(choice, 'delta') and choice.delta:
                        delta = choice.delta
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            result["has_reasoning"] = True
                            result["reasoning_content"] = delta.reasoning_content
                            result["reasoning_type"] = "chunk"
        
        # Handle reasoning summaries (O3/O4)
        elif config.reasoning_type == ReasoningType.SUMMARY:
            # Check for reasoning summary in raw response
            if hasattr(chunk, 'raw') and isinstance(chunk.raw, dict):
                if "reasoning_summary" in chunk.raw:
                    result["has_reasoning"] = True
                    result["reasoning_content"] = chunk.raw["reasoning_summary"]
                    result["reasoning_type"] = "summary"
            
            # Also check in message additional_kwargs
            if hasattr(chunk, 'message') and hasattr(chunk.message, 'additional_kwargs'):
                kwargs = chunk.message.additional_kwargs
                if kwargs and "reasoning_summary" in kwargs:
                    result["has_reasoning"] = True
                    result["reasoning_content"] = kwargs["reasoning_summary"]
                    result["reasoning_type"] = "summary"
        
        return result
    
    def get_partial_reasoning(self, session_id: str) -> Optional[str]:
        """Get any partial reasoning content from a session's parser"""
        if session_id in self.think_parsers:
            return self.think_parsers[session_id].get_partial_reasoning()
        return None
    
    def cleanup_session(self, session_id: str):
        """Clean up parser for a session"""
        if session_id in self.think_parsers:
            del self.think_parsers[session_id]
    
    def get_effort_parameter(self, model: str) -> Optional[Tuple[str, List[str]]]:
        """
        Get effort parameter info for models that support it
        
        Returns:
            Tuple of (parameter_name, allowed_values) or None
        """
        model_lower = model.lower()
        
        # Check for exact or prefix match
        for model_key, config in self.MODEL_CONFIGS.items():
            if model_lower == model_key or model_lower.startswith(model_key):
                if config.effort_parameter and config.effort_levels:
                    return (config.effort_parameter, config.effort_levels)
        
        return None
    
    def format_reasoning_output(self, reasoning_blocks: List[str], reasoning_type: str = "chunk") -> str:
        """Format reasoning blocks for display"""
        if not reasoning_blocks:
            return ""
        
        if reasoning_type == "summary":
            # Single summary block
            return f"🧠 Reasoning Summary:\n{reasoning_blocks[0]}"
        else:
            # Multiple reasoning chunks
            if len(reasoning_blocks) == 1:
                return f"🧠 Reasoning:\n{reasoning_blocks[0]}"
            else:
                formatted = "🧠 Reasoning Process:\n"
                for i, block in enumerate(reasoning_blocks, 1):
                    formatted += f"\nStep {i}:\n{block}\n"
                return formatted


# Global instance
reasoning_handler = ReasoningHandler()