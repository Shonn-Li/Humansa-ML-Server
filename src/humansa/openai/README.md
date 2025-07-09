# OpenAI Integration for Humansa Agentic Agent

This module provides an alternative streaming implementation using OpenAI's Responses API with LlamaIndex, as an alternative to the manual comprehensive streaming handler.

## Overview

The OpenAI integration offers the following benefits:

- **Native OpenAI Streaming**: Leverages OpenAI's built-in streaming capabilities
- **Built-in Tool Calling**: Uses OpenAI's native function calling with proper streaming
- **Simplified Implementation**: Less manual event creation and management
- **Better Error Handling**: OpenAI handles many edge cases automatically
- **Web Search Integration**: Built-in web search capabilities through OpenAI

## Installation

Add these dependencies to your requirements.txt:

```bash
llama-index>=0.10.0
llama-index-llms-openai>=0.1.0
openai>=1.3.0
pydantic>=2.0.0
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Basic Integration

To use OpenAI streaming as an alternative, pass `openai=true` in your request parameters:

```python
from humansa.openai import get_openai_streaming_alternative

# Your existing agent response
agent_response = agent.execute_with_tools(user_query, tools)

# Use OpenAI streaming if requested
request_params = {'openai': True, 'model': 'gpt-4o-mini'}

async for event in get_openai_streaming_alternative(agent_response, request_params):
    print(f"Event: {event['type']}")
    # Handle streaming events...
```

### Direct OpenAI Usage

You can also use the OpenAI handler directly:

```python
from humansa.openai import stream_openai_response, create_simple_search_tool

# Set up tools
tools = [create_simple_search_tool()]

# Stream response directly
async for event in stream_openai_response(
    user_message="What are the symptoms of diabetes?",
    system_prompt="You are a helpful medical AI assistant.",
    tools=tools,
    model="gpt-4o-mini"
):
    # Handle streaming events...
```

### Tool Conversion

Convert existing Humansa tools to LlamaIndex format:

```python
from humansa.openai import convert_humansa_tools_to_llamaindex

# Your existing Humansa tools
humansa_tools = [
    {
        'name': 'search_medical_conditions',
        'description': 'Search for medical conditions',
        'function': your_search_function,
        'parameters': {'query': 'string'}
    }
]

# Convert to LlamaIndex format
llamaindex_tools = convert_humansa_tools_to_llamaindex(humansa_tools)
```

## Event Format

The OpenAI integration produces events compatible with the canonical streaming format:

```json
{
  "type": "response.created",
  "sequence_number": 0,
  "response": {
    "id": "resp_abc123",
    "object": "response",
    "created_at": 1234567890,
    "status": "in_progress",
    "model": "gpt-4o-mini",
    "output": []
  }
}
```

Event types include:

- `response.created`
- `response.in_progress`
- `response.output_item.added`
- `response.content_part.added`
- `response.output_text.delta`
- `response.output_text.done`
- `response.function_tool_call.*`
- `response.function_tool_result.*`
- `response.completed`
- `response.failed`

## Configuration Options

### Model Selection

```python
request_params = {
    'openai': True,
    'model': 'gpt-4o-mini'  # or 'gpt-4o', 'gpt-3.5-turbo', etc.
}
```

### Built-in Tools

OpenAI Responses API supports built-in tools:

```python
from llama_index.llms.openai import OpenAIResponses

llm = OpenAIResponses(
    model="gpt-4o-mini",
    built_in_tools=[
        {"type": "web_search_preview"},  # Built-in web search
        {"type": "image_generation"}     # Image generation
    ]
)
```

### Custom System Prompts

The integration automatically extracts system prompts from agent responses, or you can provide custom ones:

```python
custom_prompt = "You are a medical AI assistant specializing in symptom analysis."

async for event in stream_openai_response(
    user_message=user_query,
    system_prompt=custom_prompt,
    model="gpt-4o-mini"
):
    # Handle events...
```

## Integration Points

### Main Chat Endpoint

In your main chat endpoint, you can switch between streaming methods:

```python
async def chat_endpoint(request):
    # Execute Humansa agent
    agent_response = humansa_agent.execute_with_tools(
        user_query=request.message,
        tools=available_tools
    )

    # Choose streaming method based on parameters
    if request.params.get('openai', False):
        # Use OpenAI streaming
        stream = get_openai_streaming_alternative(agent_response, request.params)
    else:
        # Use comprehensive manual streaming
        stream = convert_agent_response_to_comprehensive_stream(agent_response)

    # Return streaming response
    return StreamingResponse(stream, media_type="text/event-stream")
```

### Error Handling

The OpenAI integration includes robust error handling:

```python
try:
    async for event in stream_openai_response(...):
        yield event
except Exception as e:
    yield {
        "type": "response.failed",
        "response": {"error": str(e)}
    }
```

## Comparison with Manual Streaming

| Feature                   | Manual Streaming | OpenAI Streaming |
| ------------------------- | ---------------- | ---------------- |
| Implementation Complexity | High             | Low              |
| Custom Event Control      | Full             | Limited          |
| Tool Calling              | Manual           | Native           |
| Web Search                | Custom           | Built-in         |
| Error Handling            | Manual           | Automatic        |
| Performance               | Custom optimized | OpenAI optimized |
| Cost                      | Depends on usage | OpenAI API costs |

## Best Practices

1. **Environment Variables**: Always set `OPENAI_API_KEY` securely
2. **Model Selection**: Use `gpt-4o-mini` for cost-effective streaming
3. **Tool Conversion**: Convert tools once and reuse
4. **Error Handling**: Always handle streaming errors gracefully
5. **System Prompts**: Provide clear, specific system prompts for better results

## Limitations

- Requires OpenAI API key and credits
- Limited to OpenAI's model capabilities
- Less fine-grained control over event timing
- Dependent on OpenAI API availability

## Future Enhancements

- Support for more built-in tools
- Custom tool result formatting
- Advanced reasoning with O-series models
- Image generation integration
- Multi-modal support (images, audio)

## Examples

See `examples.py` for complete working examples of all integration patterns.
