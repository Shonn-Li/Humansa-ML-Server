# HUMANSA V2 Conversation API Documentation

## Overview

The HUMANSA V2 Conversation API provides an OpenAI-style interface for managing medical conversations with intelligent context management, automatic compression, and conversation state tracking.

## Key Features

- **Server-Managed Conversation IDs**: No need to pass full message history
- **Automatic Context Management**: Sliding window with token budget (8000 tokens)
- **Intelligent Compression**: LLM-based summarization for long conversations
- **Critical Information Preservation**: Allergies, medications, conditions always retained
- **Streaming Support**: Real-time response streaming with SSE
- **Multi-turn Conversations**: Seamless continuation of medical consultations

## API Endpoints

### 1. Create Conversation
```http
POST /v2/humansa/conversations
```

Creates a new conversation and processes the first message.

**Request Body:**
```json
{
    "user_id": "user123",
    "message": {
        "role": "user",
        "content": "你好，我最近总是头疼"
    }
}
```

**Response:**
```json
{
    "conversation_id": "conv_user123_abc123_1234567890",
    "created": 1234567890,
    "message": {
        "role": "assistant",
        "content": "您好！我了解您最近有头疼的困扰...",
        "timestamp": "2025-01-29T10:00:00Z"
    }
}
```

### 2. Add Message to Conversation
```http
POST /v2/humansa/conversations/{conversation_id}/messages
```

Adds a message to an existing conversation.

**Request Body:**
```json
{
    "message": {
        "role": "user",
        "content": "疼痛主要在前额，早上起床时最严重"
    }
}
```

**Response:**
```json
{
    "conversation_id": "conv_user123_abc123_1234567890",
    "message": {
        "role": "assistant",
        "content": "了解了，您的头痛主要集中在前额部位...",
        "timestamp": "2025-01-29T10:01:00Z"
    }
}
```

### 3. Get Conversation Details
```http
GET /v2/humansa/conversations/{conversation_id}
```

Retrieves conversation history and metadata.

**Response:**
```json
{
    "conversation_id": "conv_user123_abc123_1234567890",
    "user_id": "user123",
    "created": 1234567890,
    "last_updated": 1234567950,
    "turn_count": 5,
    "summary": "患者主诉头痛一周，前额痛，晨起加重...",
    "messages": [
        {
            "role": "user",
            "content": "你好，我最近总是头疼",
            "timestamp": "2025-01-29T10:00:00Z"
        },
        {
            "role": "assistant",
            "content": "您好！我了解您最近有头疼的困扰...",
            "timestamp": "2025-01-29T10:00:05Z"
        }
    ]
}
```

### 4. Stream Conversation Response
```http
POST /v2/humansa/conversations/{conversation_id}/stream
```

Streams response using Server-Sent Events (SSE).

**Request Body:**
```json
{
    "message": {
        "role": "user",
        "content": "我对阿司匹林过敏"
    }
}
```

**Response (SSE Stream):**
```
data: {"choices":[{"delta":{"content":"了解了，"},"index":0}]}

data: {"choices":[{"delta":{"content":"您对阿司匹林过敏"},"index":0}]}

data: [DONE]
```

### 5. Compress Conversation
```http
POST /v2/humansa/conversations/{conversation_id}/compress
```

Manually triggers conversation compression (usually automatic).

**Response:**
```json
{
    "conversation_id": "conv_user123_abc123_1234567890",
    "summary": "患者主诉：头痛一周，前额痛，晨起加重。过敏史：阿司匹林。建议：神经内科就诊...",
    "key_information": {
        "patient_name": null,
        "allergies": ["阿司匹林"],
        "symptoms": ["头痛", "前额痛", "晨起加重"],
        "medications": [],
        "appointment_info": {}
    },
    "compression_ratio": 0.75
}
```

### 6. Clean Up Old Conversations
```http
POST /v2/humansa/conversations/cleanup
```

Removes conversations older than specified hours.

**Request Body:**
```json
{
    "max_age_hours": 24
}
```

**Response:**
```json
{
    "cleaned_up": 15,
    "message": "Cleaned up 15 old conversations"
}
```

## Context Management

### Sliding Window Approach
- **Recent Messages**: Last 6 messages always included
- **Token Budget**: Maximum 8000 tokens per context
- **Critical Information**: Always preserved at top of context

### Automatic Compression
When context exceeds 6000 tokens:
1. Older messages compressed using LLM summarization
2. Medical information (allergies, conditions) extracted and preserved
3. Summary added to conversation state
4. Recent messages remain uncompressed

### Critical Information Tracking
The system automatically extracts and preserves:
- **Allergies**: Any mentioned allergies or drug sensitivities
- **Medical Conditions**: Diabetes, hypertension, heart disease, etc.
- **Current Medications**: All mentioned medications
- **Key Symptoms**: Primary complaints and symptoms

## Example Usage

### Python Client Example
```python
import aiohttp
import asyncio

async def medical_consultation():
    async with aiohttp.ClientSession() as session:
        # Create conversation
        response = await session.post(
            "http://localhost:5001/v2/humansa/conversations",
            json={
                "user_id": "patient_123",
                "message": {
                    "role": "user",
                    "content": "我最近总是失眠，已经两周了"
                }
            }
        )
        data = await response.json()
        conversation_id = data["conversation_id"]
        print(f"AI: {data['message']['content']}")
        
        # Continue conversation
        response = await session.post(
            f"http://localhost:5001/v2/humansa/conversations/{conversation_id}/messages",
            json={
                "message": {
                    "role": "user",
                    "content": "我有高血压，在吃氨氯地平"
                }
            }
        )
        data = await response.json()
        print(f"AI: {data['message']['content']}")

asyncio.run(medical_consultation())
```

### JavaScript/TypeScript Example
```typescript
// Create conversation
const response = await fetch('http://localhost:5001/v2/humansa/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: 'patient_123',
        message: {
            role: 'user',
            content: '我想预约心内科医生'
        }
    })
});

const { conversation_id, message } = await response.json();
console.log('AI:', message.content);

// Stream follow-up
const streamResponse = await fetch(
    `http://localhost:5001/v2/humansa/conversations/${conversation_id}/stream`,
    {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: {
                role: 'user',
                content: '周末上午有号吗？'
            }
        })
    }
);

const reader = streamResponse.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            
            const parsed = JSON.parse(data);
            if (parsed.choices?.[0]?.delta?.content) {
                process.stdout.write(parsed.choices[0].delta.content);
            }
        }
    }
}
```

## Best Practices

1. **User ID Management**: Use consistent user IDs across sessions
2. **Error Handling**: Always handle 404 for non-existent conversations
3. **Streaming**: Use streaming for better user experience
4. **Context Limits**: Be aware of token limits for very long conversations
5. **Cleanup**: Periodically clean up old conversations to save memory

## Migration from Full Message Passing

If migrating from passing full message arrays:

**Before (Full Messages):**
```json
{
    "messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "您好"},
        {"role": "user", "content": "我头疼"}
    ]
}
```

**After (Conversation API):**
```json
// First message
POST /v2/humansa/conversations
{ "user_id": "123", "message": {"role": "user", "content": "你好"} }

// Subsequent messages
POST /v2/humansa/conversations/{id}/messages
{ "message": {"role": "user", "content": "我头疼"} }
```

## Performance Considerations

- **Token Counting**: Uses tiktoken for accurate GPT-4 token counting
- **Compression**: Async LLM calls for summarization (adds ~1-2s latency)
- **Memory Usage**: ~1MB per active conversation
- **Cleanup**: Auto-cleanup after 24 hours (configurable)