"""
OpenAI integration utility for the comprehensive streaming handler.

Provides the alternative OpenAI path when openai=true is passed in params.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from .openai_response_streaming_handler import stream_openai_response
from .tool_converter import convert_humansa_tools_to_llamaindex, create_simple_search_tool

logger = logging.getLogger(__name__)


async def handle_openai_streaming(agent_response: Dict[str, Any],
                                  request_params: Dict[str, Any] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handle OpenAI-based streaming as an alternative to comprehensive manual streaming.

    Args:
        agent_response: Response from HumansaAgenticAgent.execute_with_tools()
        request_params: Request parameters that may contain openai=true

    Yields:
        Streaming events using OpenAI Responses API
    """
    try:
        # Extract relevant information from agent response
        final_response = agent_response.get('agent_response', '')
        tool_calls_observed = agent_response.get('tool_calls_observed', [])

        # Determine system prompt from agent trace or use default
        system_prompt = extract_system_prompt_from_response(agent_response)

        # Get model from request params or use default
        model = request_params.get(
            'model', 'gpt-4o-mini') if request_params else 'gpt-4o-mini'

        # Convert tools if available
        tools = None
        if tool_calls_observed:
            # For now, we'll use the simple search tool as an example
            # In a real implementation, you'd convert the actual tools used
            tools = [create_simple_search_tool()]
            logger.info(f"🔧 Using {len(tools)} tools for OpenAI streaming")

        # For OpenAI streaming, we use the final response as the user message
        # In a real implementation, you'd extract the original user query
        user_message = extract_user_message_from_response(agent_response)

        logger.info(f"🔄 Starting OpenAI streaming alternative")

        # Stream using OpenAI Responses API
        async for event in stream_openai_response(
            user_message=user_message,
            system_prompt=system_prompt,
            tools=tools,
            model=model
        ):
            yield event

        logger.info(f"✅ OpenAI streaming alternative completed")

    except Exception as e:
        logger.error(f"❌ OpenAI streaming alternative failed: {e}")
        import traceback
        traceback.print_exc()

        # Yield error event
        yield {
            "type": "response.failed",
            "sequence_number": 0,
            "response": {
                "id": f"resp_openai_error",
                "status": "failed",
                "error": f"OpenAI streaming failed: {str(e)}"
            }
        }


def extract_system_prompt_from_response(agent_response: Dict[str, Any]) -> str:
    """
    Extract or construct system prompt from agent response.

    Args:
        agent_response: Response from HumansaAgenticAgent

    Returns:
        System prompt string
    """
    # Try to extract from agent trace
    agent_trace = agent_response.get('agent_trace', '')

    # Look for system-like instructions in the trace
    if 'system' in agent_trace.lower() or 'instructions' in agent_trace.lower():
        lines = agent_trace.split('\n')
        for line in lines:
            if 'system' in line.lower() and len(line) > 20:
                return line.strip()

    # Default system prompt for medical/doctor assistant
    return """You are a knowledgeable medical AI assistant. You provide helpful, accurate, and evidence-based information about health and medical topics. You can search for information, analyze symptoms, and suggest treatment options, but you always remind users to consult with healthcare professionals for proper diagnosis and treatment."""


def extract_user_message_from_response(agent_response: Dict[str, Any]) -> str:
    """
    Extract original user message from agent response.

    Args:
        agent_response: Response from HumansaAgenticAgent

    Returns:
        User message string
    """
    # Try to extract from various sources

    # Check if there's a user_query field
    if 'user_query' in agent_response:
        return agent_response['user_query']

    # Try to extract from agent trace
    agent_trace = agent_response.get('agent_trace', '')
    if agent_trace:
        lines = agent_trace.split('\n')
        for line in lines:
            if line.strip().startswith(('User:', 'Query:', 'Question:')):
                return line.split(':', 1)[1].strip()

    # Try to extract from final response (last resort)
    final_response = agent_response.get('agent_response', '')
    if final_response:
        # If the final response seems to be answering a question,
        # we can infer what the question might have been
        if any(keyword in final_response.lower() for keyword in ['symptom', 'condition', 'treatment', 'medical']):
            return "Please provide medical information and analysis based on the available data."

    # Default fallback
    return "Please provide helpful information and assistance."


def should_use_openai_streaming(request_params: Dict[str, Any] = None) -> bool:
    """
    Determine if OpenAI streaming should be used based on request parameters.

    Args:
        request_params: Request parameters

    Returns:
        True if OpenAI streaming should be used
    """
    if not request_params:
        return False

    # Check for explicit openai flag
    return request_params.get('openai', False) or request_params.get('use_openai', False)


async def get_openai_streaming_alternative(agent_response: Dict[str, Any],
                                           request_params: Dict[str, Any] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Get OpenAI streaming alternative if requested.

    This is the main entry point for OpenAI streaming integration.

    Args:
        agent_response: Response from HumansaAgenticAgent.execute_with_tools()
        request_params: Request parameters that may contain openai=true

    Yields:
        Streaming events using either OpenAI or comprehensive handler
    """
    if should_use_openai_streaming(request_params):
        logger.info("🤖 Using OpenAI Responses API for streaming")
        async for event in handle_openai_streaming(agent_response, request_params):
            yield event
    else:
        logger.info("🔄 Using comprehensive manual streaming handler")
        # Import and use the original comprehensive handler
        from ..streaming.comprehensive_response_streaming_handler_fixed import convert_agent_response_to_comprehensive_stream
        async for event in convert_agent_response_to_comprehensive_stream(agent_response):
            yield event
