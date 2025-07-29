# YouWoAI Multi-Agent Streaming V2 Flow Diagram

```mermaid
graph TD
%% ===========================================
%% 🤖 YOUWOAI MULTI-AGENT V2 STREAMING ARCHITECTURE
%% ===========================================
%% This diagram shows the new multi-agent streaming workflow with OpenAI-compatible
%% streaming events that support real-time thinking, function tools, and output items.
%%
%% KEY FEATURES:
%% 1. OPENAI COMPATIBLE: Full SSE streaming with proper event vocabulary
%% 2. REAL-TIME THINKING: Stream reasoning process as agents think
%% 3. OUTPUT ITEMS: Proper envelope pattern (added → streaming → done)
%% 4. CODE INTERPRETER: Python execution with streaming results
%% 5. COMPREHENSIVE EVENTS: 26+ event types for rich streaming experience
%% ===========================================

%% ===========================================
%% CLIENT REQUEST & STREAMING SETUP
%% ===========================================
START["Client Request to /v1/multi-agent/response"] --> VALIDATE{Validate Request}
VALIDATE -->|Invalid| ERROR_RESP[Return Error Response]
VALIDATE -->|Valid| STREAM_CHECK{Stream Parameter?}

STREAM_CHECK -->|stream: false| NON_STREAMING[Non-Streaming Workflow]
STREAM_CHECK -->|stream: true| STREAMING_INIT[Initialize Streaming State]

STREAMING_INIT --> RESPONSE_ID[Generate Response ID]
RESPONSE_ID --> SEQUENCE_NUM[Initialize Sequence Number: 0]
SEQUENCE_NUM --> OUTPUT_INDEX[Initialize Output Index: -1]

%% ===========================================
%% PHASE 1: LIFECYCLE - RESPONSE CREATED
%% ===========================================
OUTPUT_INDEX --> RESPONSE_CREATED["🚀 EMIT: response.created<br/>• response: {id, object, created_at, status, model, output}<br/>• sequence_number: 0"]

RESPONSE_CREATED --> RESPONSE_IN_PROGRESS["⚡ EMIT: response.in_progress<br/>• response: {id, status}<br/>• sequence_number: 1"]

%% ===========================================
%% PHASE 2: ROUTER AGENT - STREAM THINKING
%% ===========================================
RESPONSE_IN_PROGRESS --> ROUTER_THINKING["💭 ROUTER AGENT THINKING<br/>📦 OUTPUT ITEM: reasoning"]

ROUTER_THINKING --> ROUTER_ITEM_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 0<br/>• item: {id, type: 'reasoning', content: []}"]

ROUTER_ITEM_ADDED --> ROUTER_PART_ADDED["🧠 EMIT: response.reasoning_part.added<br/>• item_id, output_index: 0, content_index: 0<br/>• part: {type: 'reasoning_text', text: ''}"]

ROUTER_PART_ADDED --> ROUTER_TEXT_DELTA["💬 EMIT: response.reasoning_text.delta<br/>• item_id, output_index: 0, content_index: 0<br/>• delta: 'Analyzing query and routing...'"]

ROUTER_TEXT_DELTA --> ROUTER_TEXT_DONE["✅ EMIT: response.reasoning_text.done<br/>• item_id, output_index: 0, content_index: 0<br/>• text: 'Complete reasoning text'"]

ROUTER_TEXT_DONE --> ROUTER_PART_DONE["🏁 EMIT: response.reasoning_part.done<br/>• item_id, output_index: 0, content_index: 0<br/>• part: {type, text}"]

ROUTER_PART_DONE --> ROUTER_EXECUTE[Execute Router Agent Logic]
ROUTER_EXECUTE --> ROUTER_ITEM_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 0<br/>• item: {id, type: 'reasoning', content: [...]}"]

%% ===========================================
%% PHASE 3: CONTEXT AGENTS - PARALLEL STREAMING
%% ===========================================
ROUTER_ITEM_DONE --> CONTEXT_AGENTS{Which Agents Enabled?}

%% Web Search Agent Branch
CONTEXT_AGENTS --> WEB_SEARCH_BRANCH[Web Search Agent]
WEB_SEARCH_BRANCH --> WEB_ITEM_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 1<br/>• item: {id, type: 'web_search_call', status: 'in_progress'}"]

WEB_ITEM_ADDED --> WEB_IN_PROGRESS["🔍 EMIT: response.web_search_call.in_progress<br/>• output_index: 1, item_id"]

WEB_IN_PROGRESS --> WEB_SEARCHING["🌐 EMIT: response.web_search_call.searching<br/>• output_index: 1, item_id"]

WEB_SEARCHING --> WEB_COMPLETED["✅ EMIT: response.web_search_call.completed<br/>• output_index: 1, item_id"]

WEB_COMPLETED --> WEB_ITEM_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 1<br/>• item: {id, type: 'web_search_call', status: 'completed', action: {...}, results: [...]}"]

%% RAG Agent Branch (File Search)
CONTEXT_AGENTS --> RAG_BRANCH[RAG Agent]
RAG_BRANCH --> FILE_ITEM_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 2<br/>• item: {id, type: 'file_search_call', status: 'in_progress'}"]

FILE_ITEM_ADDED --> FILE_IN_PROGRESS["📁 EMIT: response.file_search_call.in_progress<br/>• output_index: 2, item_id"]

FILE_IN_PROGRESS --> FILE_SEARCHING["🔍 EMIT: response.file_search_call.searching<br/>• output_index: 2, item_id"]

FILE_SEARCHING --> FILE_COMPLETED["✅ EMIT: response.file_search_call.completed<br/>• output_index: 2, item_id"]

FILE_COMPLETED --> FILE_ITEM_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 2<br/>• item: {id, type: 'file_search_call', status: 'completed', action: {...}, results: [...]}"]

%% Code Interpreter Agent Branch
CONTEXT_AGENTS --> CODE_BRANCH[Code Interpreter Agent]
CODE_BRANCH --> CODE_TOOL_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 3<br/>• item: {id, type: 'function_tool_call', name: 'python_interpreter'}"]

CODE_TOOL_ADDED --> CODE_TOOL_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 3<br/>• item: {id, type: 'function_tool_call', status: 'completed', output: '...'}"]

CODE_TOOL_DONE --> CODE_RESULT_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 3<br/>• item: {id, type: 'function_tool_result', role: 'tool'}"]

CODE_RESULT_ADDED --> CODE_RESULT_DELTA["💻 EMIT: response.function_tool_result.delta<br/>• item_id<br/>• delta: 'Code execution completed successfully...'"]

CODE_RESULT_DELTA --> CODE_RESULT_DONE["✅ EMIT: response.function_tool_result.done<br/>• item_id"]

CODE_RESULT_DONE --> CODE_RESULT_ITEM_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 3<br/>• item: {id, type: 'function_tool_result', content: [...]}"]

%% Attachment Agent Branch
CONTEXT_AGENTS --> ATTACH_BRANCH[Attachment Agent]
ATTACH_BRANCH --> ATTACH_TOOL_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 4<br/>• item: {id, type: 'function_tool_call', name: 'process_attachments'}"]

ATTACH_TOOL_ADDED --> ATTACH_TOOL_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 4<br/>• item: {id, type: 'function_tool_call', status: 'completed'}"]

%% ===========================================
%% PHASE 4: RESPONSE AGENT - STREAM FINAL RESPONSE
%% ===========================================
WEB_ITEM_DONE --> RESPONSE_PHASE[Response Agent Phase]
FILE_ITEM_DONE --> RESPONSE_PHASE
CODE_RESULT_ITEM_DONE --> RESPONSE_PHASE
ATTACH_TOOL_DONE --> RESPONSE_PHASE

RESPONSE_PHASE --> MSG_ITEM_ADDED["📦 EMIT: response.output_item.added<br/>• output_index: 5<br/>• item: {id, type: 'message', role: 'assistant'}"]

MSG_ITEM_ADDED --> CONTENT_PART_ADDED["📝 EMIT: response.content_part.added<br/>• item_id, output_index: 5, content_index: 0<br/>• part: {type: 'output_text', text: ''}"]

CONTENT_PART_ADDED --> OUTPUT_TEXT_DELTA["💬 EMIT: response.output_text.delta<br/>• item_id, output_index: 5, content_index: 0<br/>• delta: 'Based on my analysis...'"]

OUTPUT_TEXT_DELTA --> OUTPUT_ANNOTATION["📌 EMIT: response.output_text.annotation.added<br/>• item_id, output_index: 5, content_index: 0<br/>• annotation: {type: 'url_citation', ...}"]

OUTPUT_ANNOTATION --> OUTPUT_TEXT_DONE["✅ EMIT: response.output_text.done<br/>• item_id, output_index: 5, content_index: 0<br/>• text: 'Complete response text'"]

OUTPUT_TEXT_DONE --> CONTENT_PART_DONE["🏁 EMIT: response.content_part.done<br/>• item_id, output_index: 5, content_index: 0<br/>• part: {type: 'output_text', text: '...', annotations: [...]}"]

CONTENT_PART_DONE --> MSG_ITEM_DONE["📦 EMIT: response.output_item.done<br/>• output_index: 5<br/>• item: {id, type: 'message', role: 'assistant', content: [...]}"]

%% ===========================================
%% PHASE 5: CUSTOM EVENTS
%% ===========================================
MSG_ITEM_DONE --> CITATIONS_EVENT["📚 EMIT: response.citations<br/>• citations: [{id, title, url, type, snippet}, ...]"]

CITATIONS_EVENT --> TITLE_EVENT["📋 EMIT: response.title_generated<br/>• title: 'AI Development Discussion'"]

TITLE_EVENT --> USAGE_EVENT["📊 EMIT: response.usage<br/>• usage: {prompt_tokens, completion_tokens, total_tokens}"]

%% ===========================================
%% PHASE 6: LIFECYCLE - RESPONSE COMPLETED
%% ===========================================
USAGE_EVENT --> RESPONSE_COMPLETED["🏁 EMIT: response.completed<br/>• response: {id, status: 'completed', object: 'response', output: []}"]

RESPONSE_COMPLETED --> SSE_DONE["📡 SSE: [DONE]"]
SSE_DONE --> END[Return to Client]

%% ===========================================
%% ERROR HANDLING
%% ===========================================
RESPONSE_CREATED -.->|Error| RESPONSE_FAILED["❌ EMIT: response.failed<br/>• response: {id, status: 'failed', error: 'Error message'}"]
RESPONSE_FAILED --> SSE_DONE

%% ===========================================
%% NON-STREAMING PATH
%% ===========================================
NON_STREAMING --> NS_ROUTER[Execute Router Agent]
NS_ROUTER --> NS_CONTEXT[Execute Context Agents in Parallel]
NS_CONTEXT --> NS_RESPONSE[Execute Response Agent]
NS_RESPONSE --> NS_CITATION[Execute Citation Agent]
NS_CITATION --> NS_FORMAT[Format OpenAI Response]
NS_FORMAT --> END

%% ===========================================
%% STREAMING EVENT VOCABULARY LEGEND
%% ===========================================
STREAMING_LEGEND["🎯 STREAMING EVENT VOCABULARY (26+ Events)<br/><br/>🔄 LIFECYCLE (4 events):<br/>• response.created/in_progress/completed/failed<br/><br/>📦 OUTPUT ITEM ENVELOPE (2 events):<br/>• response.output_item.added/done<br/><br/>💭 REASONING (4 events):<br/>• response.reasoning_part.added/done<br/>• response.reasoning_text.delta/done<br/><br/>🔍 SEARCH (6 events):<br/>• response.web_search_call.in_progress/searching/completed<br/>• response.file_search_call.in_progress/searching/completed<br/><br/>⚙️ FUNCTION TOOLS (2 events):<br/>• response.function_tool_result.delta/done<br/><br/>📝 MESSAGE (5 events):<br/>• response.content_part.added/done<br/>• response.output_text.delta/annotation.added/done<br/><br/>🎨 CUSTOM (3 events):<br/>• response.citations/title_generated/usage"]

%% ===========================================
%% AGENT CAPABILITIES MATRIX
%% ===========================================
AGENT_MATRIX["🤖 AGENT CAPABILITIES MATRIX<br/><br/>🧭 RouterAgent:<br/>• Query analysis & routing<br/>• Reasoning stream<br/>• Agent enablement logic<br/><br/>🧠 RAGAgent:<br/>• Knowledge base search<br/>• File search streaming<br/>• Vector similarity matching<br/><br/>🌐 WebSearchAgent:<br/>• Real-time web search<br/>• Search progress streaming<br/>• Result caching<br/><br/>📎 AttachmentAgent:<br/>• File processing<br/>• Function tool calls<br/>• Multi-format support<br/><br/>💻 CodeInterpreterAgent:<br/>• Python code execution<br/>• Streaming results<br/>• Secure sandboxing<br/><br/>🎯 ResponseAgent:<br/>• LLM response generation<br/>• Context combination<br/>• Streaming support<br/><br/>📚 CitationAgent:<br/>• Source attribution<br/>• Citation formatting<br/>• Reference tracking"]

%% ===========================================
%% SSE TRANSPORT FORMAT
%% ===========================================
SSE_FORMAT["📡 SSE TRANSPORT FORMAT<br/><br/>event: data<br/>data: {\"type\": \"response.created\", \"sequence_number\": 0, \"response\": {...}}<br/><br/>event: data<br/>data: {\"type\": \"response.reasoning_text.delta\", \"sequence_number\": 4, \"item_id\": \"reasoning_123\", \"delta\": \"I need to...\"}<br/><br/>event: data<br/>data: {\"type\": \"response.output_text.delta\", \"sequence_number\": 25, \"item_id\": \"msg_456\", \"delta\": \"Based on...\"}<br/><br/>event: data<br/>data: [DONE]"]

%% ===========================================
%% OPENAI COMPATIBILITY
%% ===========================================
OPENAI_COMPAT["🔗 OPENAI COMPATIBILITY<br/><br/>✅ SSE Transport Protocol<br/>✅ Output Item Envelope Pattern<br/>✅ Reasoning Streams<br/>✅ Function Tool Calls<br/>✅ Text Delta Streaming<br/>✅ Annotation System<br/>✅ Citation Support<br/>✅ Usage Tracking<br/>✅ Proper Error Handling<br/>✅ Sequence Numbering"]
```

## Streaming Event Sequence Example

```
1. response.created
2. response.in_progress

// Router Agent Thinking
3. response.output_item.added (type: "reasoning")
4. response.reasoning_part.added
5. response.reasoning_text.delta (multiple chunks)
6. response.reasoning_text.done
7. response.reasoning_part.done
8. response.output_item.done

// Web Search Agent
9. response.output_item.added (type: "web_search_call")
10. response.web_search_call.in_progress
11. response.web_search_call.searching
12. response.web_search_call.completed
13. response.output_item.done

// Code Interpreter Agent
14. response.output_item.added (type: "function_tool_call")
15. response.output_item.done
16. response.output_item.added (type: "function_tool_result")
17. response.function_tool_result.delta (multiple chunks)
18. response.function_tool_result.done
19. response.output_item.done

// Response Agent
20. response.output_item.added (type: "message")
21. response.content_part.added
22. response.output_text.delta (multiple chunks)
23. response.output_text.annotation.added (citations)
24. response.output_text.done
25. response.content_part.done
26. response.output_item.done

// Custom Events
27. response.citations
28. response.title_generated
29. response.usage

// Completion
30. response.completed
```

## Agent Trigger Logic

### Code Interpreter Agent
**Triggers when query contains:**
- `code`, `python`, `execute`, `calculate`
- `plot`, `graph`, `analyze data`, `statistics`
- `math`, `solve`
- Code blocks: ` ```python ` or ` import `

### Web Search Agent
**Triggers when router selects:**
- `web_search` tool
- Current events queries
- Real-time information requests

### RAG Agent
**Triggers when router selects:**
- `knowledge_base_notes`
- `knowledge_base_conversations` 
- `knowledge_base_full`

### Attachment Agent
**Triggers when:**
- Request contains `attachments` array
- Router selects `attachments` tool
- File processing needed

## Performance Characteristics

- **Real-time Streaming**: Events sent as agents process
- **Parallel Execution**: Context agents run simultaneously
- **Progressive Updates**: Users see thinking process
- **Error Resilience**: Individual agent failures don't break workflow
- **Resource Efficient**: Streaming reduces memory usage
- **OpenAI Compatible**: Direct drop-in replacement for OpenAI API

## Integration Points

- **Backend Server**: Processes streaming events and stores output_items
- **Frontend**: Renders real-time agent thinking and results
- **Mobile App**: Compatible with React Native streaming
- **API Gateway**: Standard SSE transport protocol
- **Database**: Persists complete conversation with output items