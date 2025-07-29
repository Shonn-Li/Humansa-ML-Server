# YouWoAI ML Server Streaming API Standard

## Overview

This document defines the complete streaming API standard for YouWoAI ML Server endpoints. All streaming endpoints MUST implement this format to ensure consistency across the system.

## 1. Complete Event Vocabulary

### 1.1 Lifecycle Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.created` | Request accepted | Initialize response | `response: {id, object, created_at, status, model, output}` |
| `response.in_progress` | Processing continues | Keep-alive signal | `response: {id, status}` |
| `response.completed` | All processing done | Success termination | `response: {id, status, object, output}` |
| `response.failed` | Error occurred | Error termination | `response: {id, status, error}` |
| `response.incomplete` | Partial completion | Partial termination | `response: {id, status, reason}` |

### 1.2 Output Item Envelope (Universal Pattern)

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.output_item.added` | Start any item | Allocate draft | `output_index, item: {id, type, ...}` |
| `response.output_item.done` | Complete any item | Finalize & persist | `output_index, item: {id, type, status: "completed", ...}` |

### 1.3 Reasoning Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.reasoning_part.added` | Start reasoning text | Open text buffer | `item_id, output_index, content_index, part: {type: "reasoning_text", text: ""}` |
| `response.reasoning_text.delta` | Stream reasoning | Real-time thinking | `item_id, output_index, content_index, delta` |
| `response.reasoning_text.done` | Complete reasoning | Finalize text | `item_id, output_index, content_index, text` |
| `response.reasoning_part.done` | Close reasoning part | Complete buffer | `item_id, output_index, content_index, part: {type, text}` |

### 1.4 Web Search Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.web_search_call.in_progress` | Search worker ready | Show progress | `output_index, item_id` |
| `response.web_search_call.searching` | Hitting search API | Show activity | `output_index, item_id` |
| `response.web_search_call.completed` | Results available | Show completion | `output_index, item_id` |

### 1.5 File Search Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.file_search_call.in_progress` | File search started | Show progress | `output_index, item_id` |
| `response.file_search_call.searching` | Searching files | Show activity | `output_index, item_id` |
| `response.file_search_call.completed` | Search complete | Show completion | `output_index, item_id` |

### 1.6 Function Tool Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.function_tool_result.delta` | Stream tool output | Real-time results | `item_id, delta` |
| `response.function_tool_result.done` | Tool complete | Finalize output | `item_id` |

### 1.7 Assistant Message Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.content_part.added` | Start message content | Open content buffer | `item_id, output_index, content_index, part: {type, text: ""}` |
| `response.output_text.delta` | Stream response text | Real-time response | `item_id, output_index, content_index, delta` |
| `response.output_text.annotation.added` | Add citation | Insert reference | `item_id, output_index, content_index, annotation` |
| `response.output_text.done` | Complete response text | Finalize text | `item_id, output_index, content_index, text` |
| `response.content_part.done` | Complete content part | Close content buffer | `item_id, output_index, content_index, part` |

### 1.8 Custom Events

| Event | When | Purpose | Required Fields |
|-------|------|---------|----------------|
| `response.citations` | Citations ready | Provide references | `citations: [{id, title, url, type, snippet}]` |
| `response.title_generated` | Title created | Update conversation | `title` |
| `response.usage` | Usage calculated | Track tokens | `usage: {prompt_tokens, completion_tokens, total_tokens}` |

## 2. Output Item Types & Structures

### 2.1 Reasoning Item

```json
{
  "id": "rs_abc123",
  "type": "reasoning", 
  "status": "completed",
  "content": [
    {
      "type": "reasoning_text",
      "text": "I need to search for information about..."
    }
  ],
  "created_at": "2025-01-08T10:30:00Z",
  "completed_at": "2025-01-08T10:30:15Z",
  "output_index": 0
}
```

### 2.2 Web Search Call Item

```json
{
  "id": "ws_def456",
  "type": "web_search_call",
  "status": "completed", 
  "action": {
    "type": "search",
    "query": "latest AI developments",
    "search_engine": "serper"
  },
  "results": [
    {
      "url": "https://example.com/article",
      "title": "AI Breakthrough",
      "snippet": "Recent developments in AI..."
    }
  ],
  "created_at": "2025-01-08T10:30:16Z",
  "completed_at": "2025-01-08T10:30:20Z", 
  "output_index": 1
}
```

### 2.3 File Search Call Item

```json
{
  "id": "fs_ghi789",
  "type": "file_search_call",
  "status": "completed",
  "action": {
    "type": "search",
    "query": "project requirements",
    "search_scope": "user_files"
  },
  "results": [
    {
      "file_id": "file_123",
      "filename": "requirements.txt", 
      "snippet": "The project requires..."
    }
  ],
  "created_at": "2025-01-08T10:30:21Z",
  "completed_at": "2025-01-08T10:30:25Z",
  "output_index": 2
}
```

### 2.4 Function Tool Call Item

```json
{
  "id": "fc_jkl012",
  "type": "function_tool_call",
  "status": "completed",
  "name": "get_weather",
  "arguments": "{\"location\": \"San Francisco\"}",
  "output": "Current temperature: 72°F, sunny",
  "created_at": "2025-01-08T10:30:26Z",
  "completed_at": "2025-01-08T10:30:28Z",
  "output_index": 3
}
```

### 2.5 Function Tool Result Item (Optional Separate Item)

```json
{
  "id": "fr_mno345", 
  "type": "function_tool_result",
  "status": "completed",
  "role": "tool",
  "content": [
    {
      "type": "output_text",
      "text": "Current temperature: 72°F, sunny"
    }
  ],
  "created_at": "2025-01-08T10:30:28Z",
  "completed_at": "2025-01-08T10:30:29Z",
  "output_index": 4
}
```

### 2.6 Assistant Message Item

```json
{
  "id": "msg_pqr678",
  "type": "message",
  "role": "assistant", 
  "status": "completed",
  "content": [
    {
      "type": "output_text",
      "text": "Based on my research, here's what I found...",
      "annotations": [
        {
          "type": "url_citation",
          "start_index": 25,
          "end_index": 50,
          "title": "AI Breakthrough",
          "url": "https://example.com/article"
        }
      ]
    }
  ],
  "created_at": "2025-01-08T10:30:30Z",
  "completed_at": "2025-01-08T10:30:45Z",
  "output_index": 5
}
```

## 3. Complete Event Sequence Examples

### 3.1 Multi-Agent Workflow with All Event Types

```
1. response.created
2. response.in_progress

// Router Reasoning
3. response.output_item.added (type: "reasoning")
4. response.reasoning_part.added 
5. response.reasoning_text.delta (multiple)
6. response.reasoning_text.done
7. response.reasoning_part.done
8. response.output_item.done

// Web Search  
9. response.output_item.added (type: "web_search_call")
10. response.web_search_call.in_progress
11. response.web_search_call.searching
12. response.web_search_call.completed
13. response.output_item.done

// File Search
14. response.output_item.added (type: "file_search_call") 
15. response.file_search_call.in_progress
16. response.file_search_call.searching
17. response.file_search_call.completed
18. response.output_item.done

// Function Tool Call
19. response.output_item.added (type: "function_tool_call")
20. response.output_item.done

// Function Tool Result (Optional)
21. response.output_item.added (type: "function_tool_result")
22. response.function_tool_result.delta (multiple)
23. response.function_tool_result.done
24. response.output_item.done

// Assistant Response
25. response.output_item.added (type: "message")
26. response.content_part.added
27. response.output_text.delta (multiple)
28. response.output_text.annotation.added (as needed)
29. response.output_text.done
30. response.content_part.done  
31. response.output_item.done

// Custom Events
32. response.citations
33. response.title_generated
34. response.usage

// Completion
35. response.completed
```

## 4. Implementation Requirements

### 4.1 Event Ordering Rules

1. **Lifecycle events** must always be first (`response.created`) and last (`response.completed/failed`)
2. **Output items** must follow the envelope pattern: `added` → [streaming events] → `done`
3. **Text streaming** must follow: `part.added` → `text.delta` (multiple) → `text.done` → `part.done`
4. **Search events** must be in order: `in_progress` → `searching` → `completed`

### 4.2 Required Fields

Every event must include:
- `type`: Event type string
- `sequence_number`: Incrementing integer for ordering

Event-specific required fields as defined in tables above.

### 4.3 Error Handling

- Use `response.failed` for terminal errors
- Include meaningful error messages in `error` field
- Always send `[DONE]` after any terminal event

### 4.4 Performance Guidelines

- Batch small deltas to avoid excessive events
- Use appropriate buffer sizes for streaming text
- Include timing information for debugging

## 5. Testing Requirements

All streaming endpoints must pass these test cases:

1. **Complete Event Sequence** - All required events in correct order
2. **Error Handling** - Proper failure events and recovery
3. **Event Structure** - All required fields present and valid
4. **Timing Constraints** - Events within reasonable time bounds
5. **Text Streaming** - Proper delta aggregation and completion

## 6. SSE Transport Format

```
event: data
data: {"type": "response.created", "sequence_number": 0, "response": {...}}

event: data  
data: {"type": "response.output_item.added", "sequence_number": 1, "output_index": 0, "item": {...}}

event: data
data: {"type": "response.reasoning_text.delta", "sequence_number": 2, "item_id": "rs_123", "delta": "I need to..."}

event: data
data: [DONE]
```

## 7. Validation Schema

Each endpoint should validate events against this schema:

- Event type must be from approved vocabulary
- Required fields must be present
- Field types must match specifications  
- Sequence numbers must increment
- Output indexes must be consistent

This standard ensures all YouWoAI ML Server endpoints provide consistent, rich streaming experiences that the backend and frontend can rely on.