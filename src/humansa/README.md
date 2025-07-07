# Humansa AI-Agent Module

This module provides AI-agent functionality with tool calling capabilities for the YouWoAI platform. It's designed to work alongside the existing modular architecture while providing enhanced agent-based reasoning and tool execution.

## Overview

The Humansa AI-Agent module extends the existing YouWoAI chat system with:

- **AI-Agent Reasoning**: Intelligent query analysis and tool selection
- **Tool Calling**: Execute specific tools based on query requirements
- **Modular Architecture**: Reuses existing modules for core functionality
- **Enhanced Context**: Combines regular context with tool execution results

## Architecture

```
humansa/
├── __init__.py
├── endpoints/
│   ├── __init__.py
│   └── humansa_chat_endpoint.py    # Main chat endpoint
├── tools/
│   ├── __init__.py
│   └── humansa_tools.py           # Tool management and execution
├── agent/
│   ├── __init__.py
│   └── humansa_agent.py           # Agent reasoning and decision making
└── README.md
```

## Endpoint

### POST /v1-humansa/chat/completions

The main AI-agent chat completion endpoint that provides enhanced functionality over the standard chat endpoint.

**Request Format:**

```json
{
  "messages": [{ "role": "user", "content": "Your question here" }],
  "model": "gpt-4.1-nano",
  "stream": false,
  "user_id": "user_123",
  "tools_enabled": true,
  "agent_reasoning": true,
  "enable_rag": true,
  "enable_web_search": false,
  "context": {
    "user_id": "user_123",
    "note_ids": [],
    "folder_ids": [],
    "conversation_ids": []
  },
  "attachments": []
}
```

**Response Format:**

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Response content here"
      }
    }
  ],
  "humansa_enhanced": true,
  "humansa_metadata": {
    "tools_used": ["embedding_search", "context_retrieval"],
    "agent_confidence": 0.85
  }
}
```

## Key Features

### 1. Agent-Based Reasoning

The `HumansaAgent` class analyzes incoming queries to determine:

- Query intent and complexity
- Required tools for processing
- Confidence in tool selection
- Reasoning behind decisions

### 2. Tool Management

The `HumansaToolManager` class provides:

- **embedding_search**: Advanced embedding search operations
- **context_retrieval**: Enhanced context retrieval
- **similarity_analysis**: Content similarity analysis
- **content_summarization**: Automated content summarization
- **knowledge_extraction**: Structured knowledge extraction

### 3. Modular Integration

The humansa module reuses existing YouWoAI modules:

- **RAG Processor**: For retrieval-augmented generation
- **LLM Provider**: For model selection and execution
- **Citation Engine**: For response citations
- **Query Transformer**: For query enhancement
- **File Attachment Manager**: For file processing
- **Web Search Processor**: For web search capabilities

## Usage Examples

### Basic Query

```bash
curl -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Find information about AI trends"}],
    "model": "gpt-4.1-nano",
    "user_id": "user_123",
    "tools_enabled": true,
    "agent_reasoning": true
  }'
```

### Streaming Response

```bash
curl -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Analyze this content"}],
    "model": "gpt-4.1-nano",
    "stream": true,
    "user_id": "user_123",
    "tools_enabled": true,
    "agent_reasoning": true
  }'
```

### With Context and Attachments

```bash
curl -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Summarize my notes"}],
    "model": "gpt-4.1-nano",
    "user_id": "user_123",
    "tools_enabled": true,
    "agent_reasoning": true,
    "context": {
      "user_id": "user_123",
      "note_ids": ["note_1", "note_2"]
    }
  }'
```

## Customization

### Adding New Tools

To add a new tool:

1. Add the tool function to `HumansaToolManager`:

```python
async def _my_custom_tool(self, query: str, context: List, user_id: str) -> Dict[str, Any]:
    # Your tool implementation
    return {"result": "tool output"}
```

2. Register the tool in `__init__`:

```python
self.available_tools['my_custom_tool'] = self._my_custom_tool
```

3. Update the agent reasoning patterns if needed:

```python
self.reasoning_patterns['my_custom_tool'] = ['keyword1', 'keyword2']
```

### Modifying Agent Reasoning

The agent reasoning can be customized by modifying the `HumansaAgent` class:

- Update `reasoning_patterns` for tool selection
- Modify `_analyze_query_content` for better intent detection
- Adjust `_calculate_confidence` for different confidence scoring

## Integration with Existing System

The humansa module is designed to work alongside the existing YouWoAI system:

1. **Shared Dependencies**: Uses the same LLM providers, embedding systems, and database connections
2. **Modular Design**: Can be enabled/disabled without affecting other endpoints
3. **Backward Compatibility**: Standard chat endpoint remains unchanged
4. **Resource Sharing**: Reuses existing caching, logging, and monitoring systems

## Development Notes

- All tool implementations are currently placeholder functions
- The module is designed for gradual enhancement and customization
- Logging is comprehensive for debugging and monitoring
- Error handling is robust with graceful degradation
- Performance monitoring is built-in for optimization

## Future Enhancements

Planned enhancements include:

- Advanced tool implementations
- Tool chaining and orchestration
- Custom agent personality and behavior
- Integration with external APIs
- Performance optimization
- Advanced caching strategies
