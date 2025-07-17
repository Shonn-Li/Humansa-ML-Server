# Multi-Agent Response Endpoint v1 Documentation

## Overview

The Multi-Agent Response Endpoint (`/v1/multi-agent/response`) is a new endpoint that implements a multi-agent workflow where different specialized agents handle different aspects of the response generation process. This represents a shift from the current context-aggregation-first approach to an autonomous agent-based workflow.

## Architecture

### Agent Types

The system consists of 6 specialized agents:

1. **RouterAgent** - Routes queries to appropriate agents based on intent
2. **RAGAgent** - Retrieves relevant context from notes and conversations
3. **WebSearchAgent** - Performs web searches when needed
4. **AttachmentAgent** - Processes file attachments (images, PDFs, etc.)
5. **ResponseAgent** - Generates the final response using gathered context
6. **CitationAgent** - Adds citations and references to responses

### Workflow Phases

The multi-agent workflow operates in 4 distinct phases:

1. **Phase 1: Routing** - RouterAgent analyzes the query and determines which agents to activate
2. **Phase 2: Context Gathering** - RAG, WebSearch, and Attachment agents execute in parallel
3. **Phase 3: Response Generation** - ResponseAgent generates the final response using all gathered context
4. **Phase 4: Citation Processing** - CitationAgent adds citations if enabled

## API Specification

### Endpoint

```
POST /v1/multi-agent/response
```

### Request Format

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Your question here"
    }
  ],
  "user_id": 12345,
  "model": "gpt-4o-mini",
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 4000,

  // Agent control (optional)
  "enabled_agents": ["router", "rag", "response"],
  "agent_config": {},

  // Context parameters (optional)
  "note_ids": [1, 2, 3],
  "folder_ids": [10, 11],
  "conversation_ids": [20, 21],
  "attachments": ["https://example.com/document.pdf"],

  // System prompt configuration (optional)
  "completion_type": "system",
  "system_prompt": "Custom system prompt",

  // Response configuration (optional)
  "enable_citations": true,
  "generate_title": false
}
```

### Response Format

```json
{
  "status": "success",
  "data": {
    "response": "Generated response text with context",
    "model": "gpt-4o-mini",
    "usage": {
      "workflow_time": 2.45,
      "enabled_agents": ["router", "rag", "response", "citation"],
      "total_agents": 4
    },
    "metadata": {
      "agent_results": {
        "router_agent": {
          "success": true,
          "data": {
            "router_decision": {...},
            "enabled_agents": ["rag", "response"],
            "condensed_query": "Enhanced query with context"
          },
          "execution_time": 0.25
        },
        "rag_agent": {
          "success": true,
          "data": {
            "total_chunks": 5,
            "used_note_ids": [1, 2],
            "used_conversation_ids": [20]
          },
          "execution_time": 0.80
        },
        "response_agent": {
          "success": true,
          "data": {
            "response": "Generated response",
            "context_used": true,
            "context_summary": {
              "rag_chunks": 5,
              "web_results": 0,
              "attachments": 0
            }
          },
          "execution_time": 1.20
        }
      },
      "context_summary": {
        "rag_chunks": 5,
        "web_results": 0,
        "attachments": 0
      },
      "citations": [
        {
          "id": "note_1",
          "text": "Citation text",
          "source": "user_note"
        }
      ]
    }
  }
}
```

## Key Features

### 1. Autonomous Agent Workflow

- Each agent is autonomous and can be invoked independently
- Agents execute in parallel where possible (Phase 2)
- Router determines which agents to activate based on query intent

### 2. Context Priority System

- **1st Priority**: File Attachments (images always included, text filtered by similarity)
- **2nd Priority**: Knowledge Base (RAG) - split by type (notes_only, conversations_only, knowledge_base)
- **3rd Priority**: Web Search Results

### 3. Split RAG Implementation

- Router selects search type: `notes_only`, `conversations_only`, or `knowledge_base` (mixed)
- RAG processor dispatches to type-specific search methods
- Eliminates mixing unrelated content types in search results

### 4. Query Transformation

- Uses condensed queries enhanced with conversation context
- Better search results and routing decisions
- Preserves original intent while adding context

### 5. System Prompt Management

- ML server manages configurable system prompts
- Supports `completion_type`: "system" (YouWoAI) or "completion" (legacy)
- Custom system_prompt parameter support
- Dynamic date injection using Python's date.today()

## Usage Examples

### 1. Simple Conversation

```json
{
  "messages": [{ "role": "user", "content": "Hello! How are you today?" }],
  "user_id": 12345,
  "model": "gpt-4o-mini",
  "stream": false,
  "enable_citations": false,
  "completion_type": "system"
}
```

### 2. RAG-Enabled Query

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What are the key points from my notes about AI trends?"
    }
  ],
  "user_id": 12345,
  "model": "gpt-4o-mini",
  "stream": false,
  "enable_citations": true,
  "completion_type": "system"
}
```

### 3. Web Search Query

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What are the latest developments in AI in 2025?"
    }
  ],
  "user_id": 12345,
  "model": "gpt-4o-mini",
  "stream": false,
  "enable_citations": true,
  "completion_type": "system"
}
```

### 4. File Attachment Processing

```json
{
  "messages": [
    { "role": "user", "content": "Analyze this document for key insights" }
  ],
  "user_id": 12345,
  "model": "gpt-4o-mini",
  "stream": false,
  "attachments": ["https://example.com/document.pdf"],
  "enable_citations": true,
  "completion_type": "system"
}
```

### 5. Mixed Workflow with Specific Context

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Based on my previous conversations and notes, what should I focus on for my AI project?"
    }
  ],
  "user_id": 12345,
  "model": "gpt-4o-mini",
  "stream": false,
  "note_ids": [1, 2, 3],
  "conversation_ids": [10, 11],
  "enable_citations": true,
  "completion_type": "system"
}
```

## Agent Configuration

### Router Agent

- Always executes first
- Determines which agents to activate
- Transforms query with conversation context
- Uses intelligent routing based on query intent

### RAG Agent

- Retrieves context from notes and conversations
- Supports split RAG (notes_only, conversations_only, knowledge_base)
- Handles targeted search (specific IDs) vs full context search
- Creates embeddings synchronously for targeted searches

### Web Search Agent

- Performs web searches for current information
- Uses cache for repeated queries
- Configurable number of results
- Integrates with existing web search processor

### Attachment Agent

- Processes file attachments (images, PDFs, etc.)
- Images always included (no similarity filtering)
- Text content filtered by similarity (≥ 0.7)
- Supports multiple file types

### Response Agent

- Generates final response using gathered context
- Manages system prompt injection
- Supports both streaming and non-streaming modes
- Context priority ordering: attachments → RAG → web

### Citation Agent

- Adds citations to responses
- Maps content to source references
- Supports multiple source types (notes, conversations, web, attachments)
- Configurable citation format

## Performance Characteristics

### Execution Times (typical)

- Router Agent: ~0.25s
- RAG Agent: ~0.80s (parallel)
- Web Search Agent: ~1.20s (parallel)
- Attachment Agent: ~2.00s (parallel)
- Response Agent: ~1.20s (sequential)
- Citation Agent: ~0.30s (sequential)

### Total Workflow Time

- Simple conversation: ~1.5s
- RAG-enabled: ~2.5s
- Web search: ~3.0s
- File attachments: ~4.0s
- Mixed workflow: ~3.5s

## Error Handling

Each agent handles errors independently:

- Agent failures don't stop the workflow
- Failed agents return error information in metadata
- Fallback behaviors for critical failures
- Detailed error logging for debugging

## Differences from Current Implementation

### Current (Context Aggregation First)

1. Aggregate all context sources
2. Build unified context
3. Generate response with all context

### New (Multi-Agent Workflow)

1. Router analyzes query intent
2. Activate only relevant agents
3. Agents execute in parallel
4. Generate response with targeted context

### Benefits

- **Better Performance**: Only relevant agents execute
- **Improved Accuracy**: Targeted context retrieval
- **Enhanced Scalability**: Parallel agent execution
- **Better Debugging**: Individual agent metrics
- **More Flexibility**: Agent-specific configuration

## Testing

Use the provided test script to verify functionality:

```bash
cd YouWoAI-ML-Server
python test_multi_agent_endpoint.py
```

The test script includes:

- Server health checks
- Multiple test scenarios
- Performance metrics
- Error handling validation

## Integration

### Backend Integration

The multi-agent endpoint is designed to work alongside the existing modular chat endpoint. It can be used as a drop-in replacement or as a separate service for testing multi-agent workflows.

### Frontend Integration

The response format is compatible with existing frontend code. The additional metadata provides enhanced debugging and analytics capabilities.

## Future Enhancements

### Planned Features

1. **Agent Streaming**: Individual agent streaming updates
2. **Agent Caching**: Cache agent results for similar queries
3. **Agent Orchestration**: More sophisticated agent coordination
4. **Agent Learning**: Adaptive agent selection based on performance
5. **Agent Monitoring**: Real-time agent performance tracking

### Configuration Options

1. **Agent Timeouts**: Configurable timeout per agent
2. **Agent Retries**: Automatic retry on agent failures
3. **Agent Priorities**: Weight-based agent selection
4. **Agent Policies**: Custom agent activation rules
