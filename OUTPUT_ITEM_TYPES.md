# OpenAI Response API Output Item Types

## Overview
The OpenAI Response API uses a streaming format with various output item types to represent different stages of processing. Here's a comprehensive list of output items and event types used in the YouWoAI multi-agent system.

## Output Item Types

### 1. **Reasoning Item**
- **Type**: `reasoning`
- **Purpose**: Shows agent thinking/processing steps
- **Item ID Pattern**: `{agent}_xxxxxxxx` (e.g., `router_e82b2a2d`)
- **Events**:
  - `response.output_item.added` - Item created
  - `response.reasoning_part.added` - Content part added
  - `response.reasoning_text.delta` - Streaming text chunks
  - `response.reasoning_text.done` - Text complete
  - `response.reasoning_part.done` - Part complete
  - `response.output_item.done` - Item complete

### 2. **Message Item**
- **Type**: `message`
- **Purpose**: Final response content
- **Item ID Pattern**: `msg_xxxxxxxx`
- **Events**:
  - `response.output_item.added` - Message item created
  - `response.output_text.delta` - Streaming response text
  - `response.output_text.done` - Text complete
  - `response.output_item.done` - Message complete

### 3. **Tool Call Items**

#### a. Web Search Call
- **Type**: `web_search_call`
- **Item ID Pattern**: `ws_xxxxxxxx`
- **Events**:
  - `response.output_item.added` - Web search initiated
  - `response.web_search_call.in_progress` - Search executing
  - `response.web_search_call.completed` - Search complete
  - `response.output_item.done` - Item complete

#### b. File Search Call (RAG)
- **Type**: `file_search_call`
- **Item ID Pattern**: `rag_xxxxxxxx`
- **Events**:
  - `response.output_item.added` - RAG search initiated
  - `response.file_search_call.in_progress` - Search executing
  - `response.file_search_call.completed` - Search complete
  - `response.output_item.done` - Item complete

#### c. Function Tool Call
- **Type**: `function_tool_call`
- **Purpose**: Code execution, calculations
- **Events**:
  - `response.output_item.added` - Function call initiated
  - `response.function_tool_call.in_progress` - Executing
  - `response.function_tool_call.completed` - Complete
  - `response.output_item.done` - Item complete

### 4. **Citation Item**
- **Type**: `citation`
- **Item ID Pattern**: `cit_xxxxxxxx`
- **Purpose**: Adding citations to response
- **Events**:
  - `response.output_item.added` - Citation processing started
  - `response.reasoning_text.delta` - Citation reasoning
  - `response.content_part.added` - Citation content added
  - `response.content_part.done` - Citation content complete
  - `response.output_item.done` - Citation complete

### 5. **Attachment Processing**
- **Type**: `attachment`
- **Item ID Pattern**: `attachment_xxxxxxxx`
- **Purpose**: Processing uploaded files/URLs
- **Events**:
  - `response.output_item.added` - Attachment processing started
  - `response.attachment.in_progress` - Processing file
  - `response.attachment.completed` - Processing complete
  - `response.output_item.done` - Item complete

## Complete Event Flow Example

Here's a typical flow for a query with attachments that triggers multiple agents:

```
1. response.created
   └─ Initial response object created

2. response.in_progress
   └─ Processing started

3. response.output_item.added (type: reasoning, id: router_xxx)
   ├─ response.reasoning_part.added
   ├─ response.reasoning_text.delta: "Analyzing query and routing..."
   ├─ response.reasoning_text.done
   ├─ response.reasoning_part.done
   └─ response.output_item.done
       └─ Content: "Query routed to agents: attachment, rag, response, citation"

4. response.output_item.added (type: attachment, id: attachment_xxx)
   ├─ response.attachment.in_progress
   ├─ response.attachment.completed
   └─ response.output_item.done

5. response.output_item.added (type: file_search_call, id: rag_xxx)
   ├─ response.file_search_call.in_progress
   ├─ response.file_search_call.completed
   └─ response.output_item.done

6. response.output_item.added (type: message, id: msg_xxx)
   ├─ response.output_text.delta: "Based on the document..."
   ├─ response.output_text.delta: "... more content ..."
   ├─ response.output_text.done
   └─ response.output_item.done

7. response.output_item.added (type: citation, id: cit_xxx)
   ├─ response.reasoning_text.delta: "Adding citations..."
   ├─ response.content_part.added
   ├─ response.content_part.done
   └─ response.output_item.done

8. response.usage
   └─ metadata: {
         agent_results: {
           router_agent: {status: "success"},
           attachment_agent: {status: "success"},
           rag_agent: {status: "success"},
           response_agent: {status: "success"},
           citation_agent: {status: "success"}
         },
         workflow_time: 3.45
       }

9. response.done
   └─ Processing complete
```

## Agent Detection from Output Items

### ID Prefixes:
- `router_` → Router Agent
- `ws_` → Web Search Agent
- `rag_` → RAG Agent
- `attachment_` → Attachment Agent
- `cit_` → Citation Agent
- `msg_` → Response Agent
- `code_` → Code Interpreter Agent

### From Reasoning Text:
Look for "routed to agents:" in reasoning text to see which agents will be executed.

## Citation Format in Responses

### Streaming Mode:
- Citations appear in `response.output_text.delta` events
- Format: `[1]`, `[2]`, etc. inline with text
- Sources section at end with full citations

### Non-Streaming Mode:
- Complete response in `choices[0].message.content`
- Same citation format as streaming

## Metadata Structure

The final `response.usage` event contains:
```json
{
  "type": "response.usage",
  "metadata": {
    "agent_results": {
      "router_agent": {"status": "success", "data": {}},
      "attachment_agent": {"status": "success", "data": {"files_processed": 1}},
      "rag_agent": {"status": "success", "data": {"documents_found": 3}},
      "response_agent": {"status": "success", "data": {}},
      "citation_agent": {"status": "success", "data": {"citations_added": 4}}
    },
    "workflow_time": 3.45,
    "total_tokens": 1250,
    "model": "gpt-4o-nano"
  }
}
```

## Testing Commands

Run the detailed logging test suite:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python tests/test_with_detailed_logging.py
```

This will create structured logs in:
```
test_logs/
└── YYYYMMDD_HHMMSS/
    ├── output_item_analysis.json
    ├── Simple_Query.json
    ├── Simple_Query_readable.txt
    ├── Single_PDF_Attachment_Stream.json
    ├── Single_PDF_Attachment_Stream_readable.txt
    └── ... (one pair per test)
```

Each test log contains:
- Complete output item flow with timestamps
- Agent execution tracking
- Raw events for debugging
- Human-readable summaries
- Citation detection and validation