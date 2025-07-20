# YouWoAI ML Server API Documentation

## Overview
The ML Server provides AI-powered chat, multi-agent processing, embedding, and analysis capabilities. It runs on port 5001 by default.

## Base URL
```
http://localhost:5001
```

## Endpoints

### 1. Chat Completion API
**Endpoint:** `POST /v1/chat/completions`

**Description:** OpenAI-compatible chat completion endpoint with citations and streaming support.

**Request Body:**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "model": "gpt-4o-mini",  // or other supported models
  "stream": false,          // Enable streaming response
  "user_id": "user123",     // Required for RAG functionality
  "attachments": [],        // Optional file attachments
  "enable_citations": true, // Enable citation generation
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response (Non-streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4o-mini",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! I'm doing well, thank you for asking."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

**Response (Streaming):**
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: [DONE]
```

### 2. Multi-Agent Response API
**Endpoint:** `POST /v1/multi-agent/response`

**Description:** Multi-agent workflow with specialized agents for routing, RAG, web search, attachments, response generation, and citations.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "What is the weather today?"}
  ],
  "model": "gpt-4o-mini",
  "stream": false,          // NOTE: Streaming not yet implemented
  "user_id": "user123",
  "enable_citations": true,
  "attachments": []
}
```

**Response:**
```json
{
  "status": "success",
  "response": "I'll help you with weather information...",
  "metadata": {
    "agent_results": {
      "router_agent": {
        "status": "success",
        "data": {
          "router_decision": {...},
          "enabled_agents": ["web_search", "response", "citation"]
        }
      },
      "web_search_agent": {...},
      "response_agent": {...},
      "citation_agent": {...}
    },
    "workflow_time": 2.345
  }
}
```

### 3. Link Analysis API
**Endpoint:** `POST /analyze_link`

**Description:** Analyzes web links and extracts content.

**Request Body:**
```json
{
  "link": "https://example.com/article",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "status": "success",
  "analysis": {
    "title": "Article Title",
    "content": "Extracted content...",
    "summary": "Brief summary..."
  }
}
```

### 4. URL Embedding APIs

#### Create URL Embedding
**Endpoint:** `POST /v1/embeddings/url/create`

**Description:** Creates embeddings for a URL's content.

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "user_id": "user123",
  "title": "Optional Title",
  "force_refresh": false
}
```

#### Search URL Embeddings
**Endpoint:** `POST /v1/embeddings/url/search`

**Description:** Searches through embedded URLs.

**Request Body:**
```json
{
  "query": "search query",
  "user_id": "user123",
  "limit": 10
}
```

#### Delete URL Embedding
**Endpoint:** `DELETE /v1/embeddings/url/{url_id}`

**Description:** Deletes a specific URL embedding.

#### List URL Embeddings
**Endpoint:** `GET /v1/embeddings/url/list?user_id={user_id}`

**Description:** Lists all URL embeddings for a user.

### 5. Admin Embedding APIs

#### Rebuild Embeddings
**Endpoint:** `POST /admin/embedding/rebuild`

**Description:** Rebuilds embeddings for notes and conversations.

**Request Body:**
```json
{
  "user_id": "user123",
  "type": "all"  // or "notes" or "conversations"
}
```

#### Query Statistics
**Endpoint:** `GET /admin/embedding/stats?user_id={user_id}`

**Description:** Gets embedding statistics for a user.

### 6. Health Check
**Endpoint:** `GET /health`

**Description:** Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## Supported Models

### OpenAI Models
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo

### Anthropic Models
- claude-3-5-sonnet-20241022
- claude-3-5-haiku-20241022
- claude-3-opus-20240229

### DeepSeek Models
- deepseek-chat
- deepseek-reasoner

### Gemini Models
- gemini-2.0-flash-exp
- gemini-1.5-pro
- gemini-1.5-flash

### Humansa Medical Models
- humansa-o3
- medical-gpt-4o

## Error Responses

All endpoints return standardized error responses:

```json
{
  "error": "Error description",
  "status": "error",
  "type": "error_type"  // e.g., "validation_error", "unhandled_exception"
}
```

## Authentication
Currently, the ML server relies on user_id parameter for user identification. In production, this should be replaced with proper authentication tokens.

## Rate Limiting
No rate limiting is currently implemented at the ML server level. This should be handled by the API gateway or backend server.

## Notes
1. The multi-agent endpoint does not currently support streaming
2. File attachments support images, PDFs, and text files
3. Citations are generated based on RAG results and web searches
4. The server uses async processing for better performance
5. All endpoints support CORS for web clients