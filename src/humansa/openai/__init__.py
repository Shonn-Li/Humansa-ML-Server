"""
OpenAI module for Humansa Agentic Agent

Provides OpenAI Responses API integration as an alternative streaming solution.
"""

from .openai_response_streaming_handler import OpenAIResponseStreamingHandler, stream_openai_response
from .utils import convert_tool_calls_to_openai_format

from .tool_converter import (
    convert_humansa_tools_to_llamaindex,
    convert_doctor_tools_to_llamaindex,
    create_simple_search_tool,
    execute_tool_safely,
    ToolExecutionResult
)

from .openai_integration import (
    handle_openai_streaming,
    get_openai_streaming_alternative,
    should_use_openai_streaming
)

__all__ = [
    "OpenAIResponseStreamingHandler",
    "stream_openai_response",
    "convert_humansa_tools_to_llamaindex",
    "convert_doctor_tools_to_llamaindex",
    "create_simple_search_tool",
    "execute_tool_safely",
    "ToolExecutionResult",
    "handle_openai_streaming",
    "get_openai_streaming_alternative",
    "should_use_openai_streaming",
    "convert_tool_calls_to_openai_format"
]
