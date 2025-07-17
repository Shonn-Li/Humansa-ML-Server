# YouWoAI Streaming Output Format Documentation

## Overview

This document describes the comprehensive streaming format used by the YouWoAI system for handling AI responses, from the ML server through the backend to the frontend. The streaming format is designed to provide real-time feedback during AI processing, including reasoning steps, tool calls, and final responses.

## 1. ML Server Streaming Format

### 1.1 ComprehensiveResponseStreamingHandler

The ML server uses `ComprehensiveResponseStreamingHandler` located in:

- `/src/humansa/streaming/comprehensive_response_streaming_handler_fixed.py`

This handler converts agent responses into a structured streaming format following the OpenAI Realtime API specification.

### 1.2 Transport Protocol

**Content-Type**: `text/event-stream`

Format:

```
event: <event-name>
data: <single-line JSON>
```

### 1.3 Core Pattern: Output Item Envelope

**🔑 CRITICAL CONCEPT**: Every output item type follows the same envelope pattern:

1. **`response.output_item.added`** - Start any new item (allocate in-memory draft)
2. **[Type-specific streaming events]** - Stream content in real-time
3. **`response.output_item.done`** - Item finalized (persist JSON to DB)

This pattern applies to ALL output types: reasoning, web search, function calls, and assistant messages.

### 1.4 Complete Event Vocabulary

The ML server must emit events in this order:

| Phase                | Event                                                              | Fires When           | Backend Action                          |
| -------------------- | ------------------------------------------------------------------ | -------------------- | --------------------------------------- |
| **Lifecycle**        | `response.created`                                                 | request accepted     | –                                       |
|                      | `response.in_progress` (0-N)                                       | still working        | –                                       |
|                      | `response.completed` \| `response.failed` \| `response.incomplete` | terminal             | –                                       |
| **Generic Envelope** | `response.output_item.added`                                       | start any new item   | allocate in-memory draft (output_index) |
|                      | `response.output_item.done`                                        | item finalised       | persist JSON to DB                      |
| **Reasoning**        | `response.output_item.added` "type": "reasoning"                   | thinking step begins | draft                                   |
|                      | `response.reasoning_part.added` ("reasoning_text")                 | open text buffer     | –                                       |
|                      | `response.reasoning_text.delta`                                    | stream chunk         | append → push to UI                     |
|                      | `response.reasoning_text.done`                                     | text complete        | –                                       |
|                      | `response.reasoning_part.done`                                     | wrapper closed       | –                                       |
|                      | `response.output_item.done`                                        | reasoning item done  | write                                   |
| **Web Search**       | `response.output_item.added` ("web_search_call")                   | search starts        | draft                                   |
|                      | `response.web_search_call.in_progress`                             | worker ready         | UI badge                                |
|                      | `response.web_search_call.searching`                               | hitting SERP         | progress bar                            |
|                      | `response.web_search_call.completed`                               | results ready        | –                                       |
|                      | `response.output_item.done`                                        | search item done     | write                                   |
| **File Search**      | same trio: `file_search_call.*`                                    |                      |                                         |
| **Function Tool**    | `response.output_item.added` ("function_tool_call")                | call announced       | draft                                   |
|                      | `response.output_item.done`                                        | call item done       | write                                   |
|                      | (optional) `response.output_item.added` ("function_tool_result")   | create result item   | draft                                   |
|                      | (optional) `response.function_tool_result.delta`                   | stream result text   | append                                  |
|                      | (optional) `response.function_tool_result.done`                    | result text done     | –                                       |
|                      | (optional) `response.output_item.done`                             | result item done     | write                                   |
| **Assistant Answer** | `response.output_item.added` ("message")                           | answer begins        | draft                                   |
|                      | `response.content_part.added` ("output_text")                      | open text part       | buffer                                  |
|                      | `response.output_text.delta`                                       | token chunk          | append → UI                             |
|                      | `response.output_text.annotation.added`                            | citation arrives     | merge                                   |
|                      | `response.output_text.done`                                        | text complete        | –                                       |
|                      | `response.content_part.done`                                       | close part           | –                                       |
|                      | `response.output_item.done`                                        | answer item done     | write                                   |

## 2. Output Item Storage Format

### 2.1 Canonical JSON Structures

**🔑 KEY POINT**: Only `output_item.done` payloads are persisted to the database. The streaming events are for real-time UI updates only.

Each output item type has a specific canonical structure that must be stored:

#### 2.1.1 Reasoning Item

```json
{
  "id": "rs_e3f…",
  "type": "reasoning",
  "status": "completed",
  "content": [
    {
      "type": "reasoning_text",
      "text": "First I will search the web because …"
    }
  ]
}
```

#### 2.1.2 Web Search Call Item

```json
{
  "id": "ws_9ab…",
  "type": "web_search_call",
  "status": "completed",
  "action": {
    "query": "Elon Musk America Party",
    "search_engine": "serper"
  },
  "results": [
    {
      "url": "https://www.npr.org/…",
      "title": "Musk forms a new party",
      "snippet": "…"
    },
    {
      "url": "https://www.reuters.com/…",
      "title": "Reuters headline",
      "snippet": "…"
    }
  ]
}
```

#### 2.1.3 Function Tool Call Item

```json
{
  "id": "fc_47c…",
  "type": "function_tool_call",
  "status": "completed",
  "name": "get_stock_price",
  "arguments": "{ \"ticker\": \"TSLA\" }",
  "output": null // filled only after .completed
}
```

#### 2.1.4 Function Tool Result Item (Optional)

```json
{
  "id": "fr_47c…",
  "type": "function_tool_result",
  "status": "completed",
  "role": "tool",
  "content": [
    {
      "type": "output_text",
      "text": "TSLA is currently trading at $245.65"
    }
  ]
}
```

**Note**: If you don't want a separate result item, embed the `"output": "…"` directly in the call item and still fire `function_tool_call.completed` before `output_item.done`.

#### 2.1.5 Assistant Answer

```json
{
  "id": "msg_b57…",
  "type": "message",
  "role": "assistant",
  "status": "completed",
  "content": [
    {
      "type": "output_text",
      "text": "Based on recent reports, Elon Musk announced …",
      "annotations": [
        {
          "type": "url_citation",
          "start_index": 41,
          "end_index": 66,
          "title": "Reuters",
          "url": "https://www.reuters.com/…"
        }
      ]
    }
  ]
}
```

## 3. Streaming Response Flow Examples

### 3.1 Reasoning Flow

```
1. response.output_item.added (type: "reasoning")
   → Backend: Create draft reasoning item
   → Frontend: Show reasoning section

2. response.reasoning_part.added ("reasoning_text")
   → Backend: Open text buffer
   → Frontend: Prepare text display

3. response.reasoning_text.delta (multiple events)
   → Backend: Append to buffer
   → Frontend: Stream reasoning text

4. response.reasoning_text.done
   → Backend: Text complete
   → Frontend: Finalize text display

5. response.reasoning_part.done
   → Backend: Close wrapper
   → Frontend: Complete reasoning section

6. response.output_item.done
   → Backend: Write complete reasoning item to DB
   → Frontend: Mark reasoning as complete
```

### 3.2 Web Search Flow

```
1. response.output_item.added (type: "web_search_call")
   → Backend: Create draft search item
   → Frontend: Show search section

2. response.web_search_call.in_progress
   → Backend: Worker ready
   → Frontend: Show "Searching..." badge

3. response.web_search_call.searching
   → Backend: Hitting SERP
   → Frontend: Show progress bar

4. response.web_search_call.completed
   → Backend: Results ready
   → Frontend: Show search results

5. response.output_item.done
   → Backend: Write complete search item to DB
   → Frontend: Mark search as complete
```

### 3.3 Function Tool Flow

```
1. response.output_item.added (type: "function_tool_call")
   → Backend: Create draft call item
   → Frontend: Show function call

2. response.output_item.done (for call)
   → Backend: Write call item to DB
   → Frontend: Mark call as complete

3. response.output_item.added (type: "function_tool_result") [OPTIONAL]
   → Backend: Create draft result item
   → Frontend: Show result section

4. response.function_tool_result.delta (multiple events)
   → Backend: Append result text
   → Frontend: Stream result text

5. response.function_tool_result.done
   → Backend: Result text complete
   → Frontend: Finalize result display

6. response.output_item.done (for result)
   → Backend: Write result item to DB
   → Frontend: Mark result as complete
```

### 3.4 Assistant Answer Flow

```
1. response.output_item.added (type: "message")
   → Backend: Create draft message item
   → Frontend: Show assistant message

2. response.content_part.added ("output_text")
   → Backend: Open text buffer
   → Frontend: Prepare text display

3. response.output_text.delta (multiple events)
   → Backend: Append to buffer
   → Frontend: Stream assistant text

4. response.output_text.annotation.added (as needed)
   → Backend: Merge citation
   → Frontend: Show citation

5. response.output_text.done
   → Backend: Text complete
   → Frontend: Finalize text display

6. response.content_part.done
   → Backend: Close part
   → Frontend: Complete text section

7. response.output_item.done
   → Backend: Write complete message item to DB
   → Frontend: Mark message as complete
```

## 4. System Layer Responsibilities

### 4.1 Wiring Cheat-Sheet

| Layer           | Must Do                                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| **ML Server**   | Emit events in specification order. Keep `output_index` → draft map. On `output_item.done` flush full item into DB. |
| **Backend API** | Proxy SSE to browser. Persist only `output_item.done` objects. Provide `/history` endpoint returning stored array.  |
| **Frontend**    | Listen to SSE. Show deltas live. When page reloads, pull `/history` and replay.                                     |

### 4.2 Backend Server Processing

The backend server (`humansa-ai-conversation.service.ts`) processes streaming events:

```typescript
switch (eventType) {
  case "response.reasoning_text.delta":
    // Accumulate reasoning content for final message
    if (parsed.delta) {
      assistantReasoning += parsed.delta;
    }
    break;

  case "response.output_item.added":
    // New output item started - create draft
    if (parsed.item && parsed.item.id) {
      const draftItem = {
        ...parsed.item,
        created_at: new Date().toISOString(),
        output_index: parsed.output_index,
      };
      draftOutputItems.set(parsed.item.id, draftItem);
    }
    break;

  case "response.output_item.done":
    // 🔑 CRITICAL: Output item completed - finalize and persist
    if (parsed.item && parsed.item.id) {
      const draftItem = draftOutputItems.get(parsed.item.id);
      if (draftItem) {
        const completedItem = {
          ...draftItem,
          ...parsed.item,
          status: "completed",
          completed_at: new Date().toISOString(),
        };
        // Store in final output items array
        outputItems.push(completedItem);
        draftOutputItems.delete(parsed.item.id);
      }
    }
    break;

  case "response.output_text.delta":
    // Final response text delta (for main assistant message)
    if (parsed.delta) {
      finalResponseContent += parsed.delta;
    }
    break;
}
```

### 4.3 Database Storage

The backend stores the complete conversation message with output items:

```typescript
const assistantMessage: ConversationMessage = {
  role: "assistant",
  content: [{ type: "text", text: finalResponseContent || "" }],
  citations: assistantCitations.length > 0 ? assistantCitations : undefined,
  // Store reasoning content (plain text)
  reasoning: assistantReasoning || undefined,
  // 🔑 CRITICAL: Store output items from ML server
  output_items: outputItems || [],
  // Store thinking duration from backend timing
  thinking_duration_ms: thinkingDurationMs,
};
```

## 5. Frontend Processing

### 5.1 Event Stream Handling

The frontend processes the streaming events through Redux:

```typescript
// Handle streaming events
switch (eventType) {
  case "response.reasoning_text.delta":
    // Update reasoning display in real-time
    if (parsed.delta) {
      assistantReasoning += parsed.delta;
    }
    break;

  case "response.output_text.delta":
    // Update main response content in real-time
    if (parsed.delta) {
      finalResponseContent += parsed.delta;
    }
    break;

  case "response.output_item.added":
    // 🔑 CRITICAL: Add new output item to UI
    dispatch(addOutputItem(parsed.item));
    break;

  case "response.output_item.done":
    // 🔑 CRITICAL: Complete output item in UI
    dispatch(completeOutputItem(parsed.item));
    break;

  case "response.web_search_call.in_progress":
    // Show search progress
    dispatch(updateSearchStatus({ status: "searching" }));
    break;

  case "response.function_tool_result.delta":
    // Stream function tool results
    if (parsed.delta) {
      dispatch(appendToolResult(parsed.delta));
    }
    break;
}
```

### 5.2 UI Display

The frontend displays streaming content in real-time:

```typescript
// Display streaming content
const streamingContent = useSelector(selectHumansaStreamingContent);
const isStreaming = useSelector(selectHumansaIsStreaming);
const outputItems = useSelector(selectOutputItems);

// Show streaming indicator and content
if (isStreaming) {
  return (
    <View>
      {/* Display output items */}
      {outputItems.map((item) => (
        <OutputItemDisplay key={item.id} item={item} />
      ))}

      {/* Show streaming content */}
      <Text>{streamingContent}</Text>
      <ActivityIndicator />
    </View>
  );
}
```

### 5.3 History Replay

When the page reloads, the frontend pulls stored output items:

```typescript
// On page load, fetch stored output items
useEffect(() => {
  const fetchHistory = async () => {
    const response = await fetch("/history");
    const outputItems = await response.json();

    // Replay stored output items
    outputItems.forEach((item) => {
      dispatch(addOutputItem(item));
    });
  };

  fetchHistory();
}, []);
```

## 6. Complete Example: Multi-Step AI Response

Here's a complete example showing the output item envelope pattern for a complex AI response:

```
1. response.created
   → Frontend: Show "AI is thinking..."

2. response.in_progress
   → Frontend: Continue loading indicator

3. response.output_item.added (type: "reasoning")
   → Backend: Create draft reasoning item
   → Frontend: Show reasoning section

4. response.reasoning_text.delta (multiple)
   → Backend: Append to reasoning buffer
   → Frontend: Stream reasoning text

5. response.output_item.done (reasoning)
   → Backend: Write reasoning item to DB
   → Frontend: Mark reasoning as complete

6. response.output_item.added (type: "web_search_call")
   → Backend: Create draft search item
   → Frontend: Show search section

7. response.web_search_call.searching
   → Backend: Update search status
   → Frontend: Show progress bar

8. response.output_item.done (web_search_call)
   → Backend: Write search item to DB
   → Frontend: Mark search as complete

9. response.output_item.added (type: "function_tool_call")
   → Backend: Create draft tool call item
   → Frontend: Show function call

10. response.output_item.done (function_tool_call)
    → Backend: Write tool call item to DB
    → Frontend: Mark tool call as complete

11. response.output_item.added (type: "function_tool_result")
    → Backend: Create draft tool result item
    → Frontend: Show tool result section

12. response.function_tool_result.delta (multiple)
    → Backend: Append to result buffer
    → Frontend: Stream tool result text

13. response.output_item.done (function_tool_result)
    → Backend: Write tool result item to DB
    → Frontend: Mark tool result as complete

14. response.output_item.added (type: "message")
    → Backend: Create draft assistant message
    → Frontend: Show assistant message

15. response.output_text.delta (multiple)
    → Backend: Append to message buffer
    → Frontend: Stream final response

16. response.output_item.done (message)
    → Backend: Write message item to DB
    → Frontend: Mark message as complete

17. response.completed
    → Frontend: Hide loading, show complete response
```

**Key Points:**

- **Every output item** follows the `added → [streaming] → done` pattern
- **Only `output_item.done` events** trigger database writes
- **All intermediate events** are for real-time UI updates
- **Each item type** has specific streaming events between `added` and `done`

## 7. Data Persistence

### 7.1 Database Storage Strategy

**🔑 CRITICAL**: Only `output_item.done` events trigger database writes. All other events are for real-time UI updates only.

#### 7.1.1 Output Items Storage

Each output item is stored with complete metadata when `output_item.done` is received:

```json
{
  "id": "reasoning_abc123",
  "type": "reasoning",
  "status": "completed",
  "content": [
    {
      "type": "reasoning_text",
      "text": "I need to search for information about...",
      "annotations": []
    }
  ],
  "created_at": "2025-01-08T10:30:00Z",
  "completed_at": "2025-01-08T10:30:15Z",
  "output_index": 0
}
```

#### 7.1.2 Conversation Message

The final conversation message includes all structured data:

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Based on my research, here's what I found..."
    }
  ],
  "reasoning": "I need to search for information about...",
  "output_items": [
    {
      "id": "reasoning_abc123",
      "type": "reasoning",
      "status": "completed",
      "content": [...]
    },
    {
      "id": "tool_call_def456",
      "type": "function_tool_call",
      "status": "completed",
      "action": {
        "type": "web_search",
        "query": "latest AI developments",
        "tool_name": "web_search"
      }
    }
  ],
  "thinking_duration_ms": 5000,
  "citations": [...]
}
```

### 7.2 History Endpoint

The backend provides a `/history` endpoint returning stored output items array for replay:

```typescript
// GET /history?conversation_id=123
{
  "output_items": [
    {
      "id": "reasoning_abc123",
      "type": "reasoning",
      "status": "completed",
      "content": [...]
    },
    {
      "id": "search_def456",
      "type": "web_search_call",
      "status": "completed",
      "action": {...},
      "results": [...]
    }
  ]
}
```

## 8. Transport Format

### 8.1 Server-Sent Events (SSE)

**Transport**: `Content-Type: text/event-stream`

The streaming uses SSE format:

```
event: response.output_text.delta
data: {"type": "response.output_text.delta", "delta": "Hello", "sequence_number": 1}

event: response.output_text.delta
data: {"type": "response.output_text.delta", "delta": " world", "sequence_number": 2}

event: response.output_item.done
data: {"type": "response.output_item.done", "item": {"id": "msg_123", "type": "message", "status": "completed"}}

event: response.completed
data: {"type": "response.completed", "response": {"id": "resp_123", "status": "completed"}}
```

### 8.2 Error Handling

Errors are handled gracefully:

```
event: response.failed
data: {"type": "response.failed", "response": {"id": "resp_123", "status": "failed", "error": "Connection timeout"}}
```

### 8.3 Critical Transport Rules

1. **Event Line**: `event: <event-name>`
2. **Data Line**: `data: <single-line JSON>`
3. **No Multi-line JSON**: All JSON must be on a single line
4. **Sequence Numbers**: Each event has a `sequence_number` for ordering
5. **Response ID**: All events include the same `response_id` for grouping

## 9. Integration Points

### 9.1 ML Server → Backend

- **Endpoint**: `/humansa/response` (streaming)
- **Format**: SSE with comprehensive events following specification
- **Processing**: Real-time event forwarding to frontend
- **Responsibility**: Emit events in specification order, maintain `output_index` → draft map

### 9.2 Backend → Frontend

- **Endpoint**: `/v1-humansa/chat/completions` (streaming)
- **Format**: SSE forwarding from ML server
- **Processing**: Event parsing, state management, and database persistence
- **Responsibility**: Proxy SSE to browser, persist only `output_item.done` objects

### 9.3 Frontend State Management

- **Transport**: SSE event stream
- **Processing**: Real-time UI updates for all events
- **Responsibility**: Listen to SSE, show deltas live, pull `/history` on reload

### 9.4 Database Storage

- **Table**: `conversation_v1.messages`
- **Format**: JSON with `output_items` array
- **Indexing**: By conversation_id and message timestamp
- **Trigger**: Only on `output_item.done` events

### 9.5 History Replay

- **Endpoint**: `/history?conversation_id=123`
- **Format**: JSON array of completed output items
- **Usage**: Frontend pulls on page reload to replay stored items

## 10. Future Enhancements

### 10.1 Planned Features

- Citation streaming with `response.output_text.annotation.added`
- File attachment processing events
- Multi-modal content support
- Enhanced error recovery

### 10.2 Performance Optimizations

- Chunk size optimization for streaming
- Compression for large responses
- Connection pooling for ML server
- Caching for repeated operations

## 11. Implementation Checklist

### 11.1 ML Server Requirements

- [ ] Emit events in specification order
- [ ] Maintain `output_index` → draft map
- [ ] Fire `output_item.added` before any item-specific events
- [ ] Fire `output_item.done` after all item-specific events
- [ ] Include complete JSON payload in `output_item.done`
- [ ] Use proper SSE format: `event:` and `data:` lines

### 11.2 Backend Requirements

- [ ] Proxy SSE events to frontend
- [ ] Create draft items on `output_item.added`
- [ ] Persist only `output_item.done` payloads to database
- [ ] Provide `/history` endpoint for replay
- [ ] Handle connection errors gracefully

### 11.3 Frontend Requirements

- [ ] Listen to all SSE events
- [ ] Update UI in real-time for delta events
- [ ] Mark items complete on `output_item.done`
- [ ] Pull `/history` on page reload
- [ ] Handle connection reconnection

---

**🔑 CRITICAL REMINDER**: Every output item type (reasoning, web search, function calls, assistant messages) MUST follow the `output_item.added` → `[streaming events]` → `output_item.done` envelope pattern. This ensures consistent UI behavior and proper database persistence.

This comprehensive streaming format provides a robust foundation for real-time AI interaction while maintaining full traceability and persistence of all processing steps.
