````markdown
# YouWoAI Multi-Agent Modular Flow Diagram

```mermaid
graph TD
%% ===========================================
%% 🤖 YOUWOAI MULTI-AGENT V1 ARCHITECTURE
%% ===========================================
%% This diagram shows the new multi-agent workflow where specialized agents
%% handle different aspects of response generation autonomously.
%%
%% KEY ARCHITECTURAL CHANGES:
%% 1. AGENT AUTONOMY: Each agent is self-contained and can execute independently
%% 2. WORKFLOW ORCHESTRATION: Multi-agent orchestrator manages agent lifecycle
%% 3. PARALLEL EXECUTION: Context agents run in parallel for efficiency
%% 4. MODULAR DESIGN: Easy to add/remove agents without affecting others
%% 5. EXISTING INFRASTRUCTURE: Leverages all existing modular components
%% ===========================================

%% ===========================================
%% CLIENT REQUEST & ENDPOINT ENTRY
%% ===========================================
START["Client Request to /v1/multi-agent/response"] --> VALIDATE{Validate Request}
VALIDATE -->|Invalid| ERROR_RESP[Return Error Response]
VALIDATE -->|Valid| PARSE_REQUEST[Parse MultiAgentRequest]

PARSE_REQUEST --> ORCHESTRATOR_INIT[Initialize MultiAgentOrchestrator]
ORCHESTRATOR_INIT --> WORKFLOW_START[Start Multi-Agent Workflow]

%% ===========================================
%% PHASE 1: ROUTER AGENT (ALWAYS FIRST)
%% ===========================================
WORKFLOW_START --> ROUTER_AGENT["🧭 ROUTER AGENT<br/>📍 RouterAgent(BaseAgent)<br/>• ALWAYS executes first<br/>• Determines workflow path<br/>• Enables appropriate agents<br/>• Uses existing IntelligentRouter"]

ROUTER_AGENT --> ROUTER_EXECUTE[Execute Router Agent]
ROUTER_EXECUTE --> ROUTER_TRANSFORM[Query Transformation]
ROUTER_TRANSFORM --> ROUTER_DECISION[Router Decision Making]
ROUTER_DECISION --> ROUTER_ENABLE[Enable Appropriate Agents]

ROUTER_ENABLE --> AGENT_ENABLEMENT["Agent Enablement Logic<br/>• knowledge_base_* → RAGAgent<br/>• web_search → WebSearchAgent<br/>• attachments → AttachmentAgent<br/>• ALWAYS → ResponseAgent<br/>• enable_citations → CitationAgent"]

%% ===========================================
%% PHASE 2: PARALLEL CONTEXT AGENTS
%% ===========================================
AGENT_ENABLEMENT --> PARALLEL_AGENTS{Which Agents Enabled?}

PARALLEL_AGENTS --> RAG_AGENT_BRANCH[RAG Agent Branch]
PARALLEL_AGENTS --> WEB_AGENT_BRANCH[Web Search Agent Branch]
PARALLEL_AGENTS --> ATTACH_AGENT_BRANCH[Attachment Agent Branch]

%% RAG Agent Branch
RAG_AGENT_BRANCH --> RAG_AGENT["🧠 RAG AGENT<br/>📍 RAGAgent(BaseAgent)<br/>• Retrieves knowledge base context<br/>• Uses existing RAGProcessor<br/>• Supports split RAG (notes/conversations/mixed)"]

RAG_AGENT --> RAG_EXECUTE[Execute RAG Agent]
RAG_EXECUTE --> RAG_PROCESS[RAG Processing Flow]
RAG_PROCESS --> RAG_CONTEXT[RAG Context Result]

%% Web Search Agent Branch
WEB_AGENT_BRANCH --> WEB_AGENT["🌐 WEB SEARCH AGENT<br/>📍 WebSearchAgent(BaseAgent)<br/>• Performs web searches<br/>• Uses existing WebSearchProcessor<br/>• Handles caching"]

WEB_AGENT --> WEB_EXECUTE[Execute Web Search Agent]
WEB_EXECUTE --> WEB_PROCESS[Web Search Processing Flow]
WEB_PROCESS --> WEB_CONTEXT[Web Search Context Result]

%% Attachment Agent Branch
ATTACH_AGENT_BRANCH --> ATTACH_AGENT["📎 ATTACHMENT AGENT<br/>📍 AttachmentAgent(BaseAgent)<br/>• Processes file attachments<br/>• Uses existing FileAttachmentManager<br/>• Handles images, PDFs, etc."]

ATTACH_AGENT --> ATTACH_EXECUTE[Execute Attachment Agent]
ATTACH_EXECUTE --> ATTACH_PROCESS[Attachment Processing Flow]
ATTACH_PROCESS --> ATTACH_CONTEXT[Attachment Context Result]

%% ===========================================
%% PHASE 3: RESPONSE GENERATION AGENT
%% ===========================================
RAG_CONTEXT --> CONTEXT_READY[All Context Agents Complete]
WEB_CONTEXT --> CONTEXT_READY
ATTACH_CONTEXT --> CONTEXT_READY

CONTEXT_READY --> RESPONSE_AGENT["🎯 RESPONSE AGENT<br/>📍 ResponseAgent(BaseAgent)<br/>• Generates final response<br/>• Combines all contexts<br/>• Uses existing LLMProviderSelector<br/>• Handles system prompts"]

RESPONSE_AGENT --> RESPONSE_EXECUTE[Execute Response Agent]
RESPONSE_EXECUTE --> RESPONSE_CONTEXT[Build Combined Context]
RESPONSE_CONTEXT --> RESPONSE_MESSAGES[Prepare Messages]
RESPONSE_MESSAGES --> RESPONSE_LLM[Generate LLM Response]
RESPONSE_LLM --> RESPONSE_RESULT[Response Result]

%% ===========================================
%% PHASE 4: CITATION AGENT (OPTIONAL)
%% ===========================================
RESPONSE_RESULT --> CITATION_CHECK{Citations Enabled?}
CITATION_CHECK -->|Yes| CITATION_AGENT["📚 CITATION AGENT<br/>📍 CitationAgent(BaseAgent)<br/>• Adds citations to response<br/>• Uses existing CitationEngine<br/>• Processes all context sources"]

CITATION_AGENT --> CITATION_EXECUTE[Execute Citation Agent]
CITATION_EXECUTE --> CITATION_PROCESS[Citation Processing Flow]
CITATION_PROCESS --> CITATION_RESULT[Cited Response Result]

CITATION_CHECK -->|No| FINAL_RESPONSE[Final Response Assembly]
CITATION_RESULT --> FINAL_RESPONSE

%% ===========================================
%% FINAL RESPONSE ASSEMBLY
%% ===========================================
FINAL_RESPONSE --> RESPONSE_FORMAT[Format Multi-Agent Response]
RESPONSE_FORMAT --> RESPONSE_METADATA[Add Metadata & Usage Stats]
RESPONSE_METADATA --> END[Return to Client]

%% ===========================================
%% EXTERNAL EXISTING INFRASTRUCTURE
%% ===========================================
EXISTING_INFRA["🏗️ EXISTING INFRASTRUCTURE<br/>• IntelligentRouter<br/>• RAGProcessor<br/>• WebSearchProcessor<br/>• FileAttachmentManager<br/>• LLMProviderSelector<br/>• CitationEngine<br/>• QueryTransformer<br/>• SystemPromptManager"]

%% ===========================================
%% AGENT EXECUTION PATTERNS
%% ===========================================
AGENT_PATTERN["🔄 AGENT EXECUTION PATTERN<br/>• BaseAgent.execute() wrapper<br/>• Error handling & timing<br/>• Standardized result format<br/>• Async/await support<br/>• Context passing"]

%% ===========================================
%% STREAMING SUPPORT (FUTURE)
%% ===========================================
STREAMING_FUTURE["🌊 STREAMING SUPPORT (FUTURE)<br/>• Agent-level streaming<br/>• Progressive context updates<br/>• Real-time agent status<br/>• Incremental response building"]
```
````

## RAG Agent Detailed Flow

```mermaid
graph TD
%% ===========================================
%% RAG AGENT INTERNAL FLOW
%% ===========================================
RAG_START[RAG Agent Execute] --> RAG_INIT[Initialize RAG Agent]
RAG_INIT --> RAG_PARAMS[Extract Parameters]

RAG_PARAMS --> RAG_ROUTER_QUERY[Get Condensed Query from Router]
RAG_ROUTER_QUERY --> RAG_SEARCH_TYPE[Get Search Type from Router]
RAG_SEARCH_TYPE --> RAG_PROCESSOR[Initialize RAG Processor]

RAG_PROCESSOR --> RAG_PROCESS_REQUEST[Process RAG Request]
RAG_PROCESS_REQUEST --> RAG_ID_RESOLUTION[ID Resolution]
RAG_ID_RESOLUTION --> RAG_EMBEDDING[Query Embedding]
RAG_EMBEDDING --> RAG_SEARCH[Vector Search]

RAG_SEARCH --> RAG_SEARCH_DISPATCH{Search Type?}
RAG_SEARCH_DISPATCH -->|notes_only| RAG_NOTES_ONLY[Notes Only Search]
RAG_SEARCH_DISPATCH -->|conversations_only| RAG_CONV_ONLY[Conversations Only Search]
RAG_SEARCH_DISPATCH -->|knowledge_base| RAG_MIXED[Mixed Search]

RAG_NOTES_ONLY --> RAG_CONTEXT_BUILD[Build RAG Context]
RAG_CONV_ONLY --> RAG_CONTEXT_BUILD
RAG_MIXED --> RAG_CONTEXT_BUILD

RAG_CONTEXT_BUILD --> RAG_RESULT[RAG Agent Result]
RAG_RESULT --> RAG_METADATA[Add Metadata]
RAG_METADATA --> RAG_COMPLETE[RAG Agent Complete]
```

## Web Search Agent Detailed Flow

```mermaid
graph TD
%% ===========================================
%% WEB SEARCH AGENT INTERNAL FLOW
%% ===========================================
WEB_START[Web Search Agent Execute] --> WEB_INIT[Initialize Web Search Agent]
WEB_INIT --> WEB_PARAMS[Extract Parameters]

WEB_PARAMS --> WEB_ROUTER_QUERY[Get Condensed Query from Router]
WEB_ROUTER_QUERY --> WEB_PROCESSOR[Initialize Web Search Processor]

WEB_PROCESSOR --> WEB_CACHE_CHECK[Check Search Cache]
WEB_CACHE_CHECK --> WEB_CACHE_HIT{Cache Hit?}

WEB_CACHE_HIT -->|Yes| WEB_CACHED[Use Cached Results]
WEB_CACHE_HIT -->|No| WEB_FRESH[Perform Fresh Search]

WEB_FRESH --> WEB_PROVIDER[Search Provider API]
WEB_PROVIDER --> WEB_CACHE_STORE[Store in Cache]
WEB_CACHE_STORE --> WEB_CONTEXT_BUILD[Build Web Context]

WEB_CACHED --> WEB_CONTEXT_BUILD
WEB_CONTEXT_BUILD --> WEB_RESULT[Web Search Agent Result]
WEB_RESULT --> WEB_METADATA[Add Metadata]
WEB_METADATA --> WEB_COMPLETE[Web Search Agent Complete]
```

## Attachment Agent Detailed Flow

```mermaid
graph TD
%% ===========================================
%% ATTACHMENT AGENT INTERNAL FLOW
%% ===========================================
ATTACH_START[Attachment Agent Execute] --> ATTACH_INIT[Initialize Attachment Agent]
ATTACH_INIT --> ATTACH_PARAMS[Extract Parameters]

ATTACH_PARAMS --> ATTACH_CHECK{Attachments Present?}
ATTACH_CHECK -->|No| ATTACH_EMPTY[Return Empty Context]
ATTACH_CHECK -->|Yes| ATTACH_ROUTER_QUERY[Get Condensed Query from Router]

ATTACH_ROUTER_QUERY --> ATTACH_PROCESSOR[Initialize File Attachment Manager]
ATTACH_PROCESSOR --> ATTACH_PROCESS[Process Attachments]

ATTACH_PROCESS --> ATTACH_EXTRACT[Extract URLs]
ATTACH_EXTRACT --> ATTACH_EMBED_CHECK[Check URL Embeddings]
ATTACH_EMBED_CHECK --> ATTACH_MISSING{Missing Embeddings?}

ATTACH_MISSING -->|Yes| ATTACH_DOWNLOAD[Download & Process Files]
ATTACH_MISSING -->|No| ATTACH_SEARCH[Search Existing Embeddings]

ATTACH_DOWNLOAD --> ATTACH_FILE_TYPE[Detect File Type]
ATTACH_FILE_TYPE --> ATTACH_IMG_PROCESS[Image Processing]
ATTACH_FILE_TYPE --> ATTACH_PDF_PROCESS[PDF Processing]
ATTACH_FILE_TYPE --> ATTACH_OTHER_PROCESS[Other File Processing]

ATTACH_IMG_PROCESS --> ATTACH_EMBED_CREATE[Create Embeddings]
ATTACH_PDF_PROCESS --> ATTACH_EMBED_CREATE
ATTACH_OTHER_PROCESS --> ATTACH_EMBED_CREATE

ATTACH_EMBED_CREATE --> ATTACH_STORE[Store in Database]
ATTACH_STORE --> ATTACH_SEARCH

ATTACH_SEARCH --> ATTACH_SEPARATE[Separate Images & Text]
ATTACH_SEPARATE --> ATTACH_IMAGES[Process Image Chunks]
ATTACH_SEPARATE --> ATTACH_TEXT[Process Text Chunks]

ATTACH_IMAGES --> ATTACH_CONTEXT_BUILD[Build Attachment Context]
ATTACH_TEXT --> ATTACH_CONTEXT_BUILD

ATTACH_CONTEXT_BUILD --> ATTACH_RESULT[Attachment Agent Result]
ATTACH_EMPTY --> ATTACH_RESULT
ATTACH_RESULT --> ATTACH_METADATA[Add Metadata]
ATTACH_METADATA --> ATTACH_COMPLETE[Attachment Agent Complete]
```

## Response Agent Detailed Flow

```mermaid
graph TD
%% ===========================================
%% RESPONSE AGENT INTERNAL FLOW
%% ===========================================
RESP_START[Response Agent Execute] --> RESP_INIT[Initialize Response Agent]
RESP_INIT --> RESP_PARAMS[Extract Parameters]

RESP_PARAMS --> RESP_LLM_INIT[Initialize LLM Provider]
RESP_LLM_INIT --> RESP_SYSTEM_PROMPT[Initialize System Prompt Manager]

RESP_SYSTEM_PROMPT --> RESP_CONTEXT_BUILD[Build Combined Context]
RESP_CONTEXT_BUILD --> RESP_RAG_CONTEXT[Add RAG Context]
RESP_RAG_CONTEXT --> RESP_WEB_CONTEXT[Add Web Context]
RESP_WEB_CONTEXT --> RESP_ATTACH_CONTEXT[Add Attachment Context]

RESP_ATTACH_CONTEXT --> RESP_MESSAGES[Prepare Messages]
RESP_MESSAGES --> RESP_SYSTEM_CHECK[Check System Message]
RESP_SYSTEM_CHECK --> RESP_SYSTEM_INJECT[Inject System Prompt if Needed]

RESP_SYSTEM_INJECT --> RESP_CONTEXT_INSERT[Insert Context Before Last User Message]
RESP_CONTEXT_INSERT --> RESP_CONVERT[Convert to ChatMessage Objects]

RESP_CONVERT --> RESP_STREAM_CHECK{Streaming Enabled?}
RESP_STREAM_CHECK -->|Yes| RESP_STREAM["Stream Response (Future)"]
RESP_STREAM_CHECK -->|No| RESP_DIRECT[Direct Response]

RESP_DIRECT --> RESP_LLM_CALL["Call LLM.achat()"]
RESP_LLM_CALL --> RESP_EXTRACT[Extract Response Content]

RESP_EXTRACT --> RESP_RESULT[Response Agent Result]
RESP_STREAM --> RESP_RESULT
RESP_RESULT --> RESP_METADATA[Add Context Summary]
RESP_METADATA --> RESP_COMPLETE[Response Agent Complete]
```

## Citation Agent Detailed Flow

```mermaid
graph TD
%% ===========================================
%% CITATION AGENT INTERNAL FLOW
%% ===========================================
CIT_START[Citation Agent Execute] --> CIT_INIT[Initialize Citation Agent]
CIT_INIT --> CIT_PARAMS[Extract Parameters]

CIT_PARAMS --> CIT_RESPONSE[Get Response from Response Agent]
CIT_RESPONSE --> CIT_CHECK{Response Available?}

CIT_CHECK -->|No| CIT_EMPTY[Return Empty Citations]
CIT_CHECK -->|Yes| CIT_ENGINE[Initialize Citation Engine]

CIT_ENGINE --> CIT_SOURCES[Build Source Data]
CIT_SOURCES --> CIT_RAG_SOURCES[Add RAG Sources]
CIT_RAG_SOURCES --> CIT_WEB_SOURCES[Add Web Sources]
CIT_WEB_SOURCES --> CIT_ATTACH_SOURCES[Add Attachment Sources]

CIT_ATTACH_SOURCES --> CIT_PROCESS[Process Citations]
CIT_PROCESS --> CIT_PARSE[Parse Response for Citations]
CIT_PARSE --> CIT_MAP[Map to Source References]
CIT_MAP --> CIT_FORMAT[Format Citations]

CIT_FORMAT --> CIT_RESULT[Citation Agent Result]
CIT_EMPTY --> CIT_RESULT
CIT_RESULT --> CIT_METADATA[Add Citation Count]
CIT_METADATA --> CIT_COMPLETE[Citation Agent Complete]
```

## Multi-Agent Orchestrator Flow

```mermaid
graph TD
%% ===========================================
%% MULTI-AGENT ORCHESTRATOR FLOW
%% ===========================================
ORCH_START[Orchestrator Execute Workflow] --> ORCH_INIT[Initialize Orchestrator]
ORCH_INIT --> ORCH_AGENTS[Initialize All Agents]

ORCH_AGENTS --> ORCH_ROUTER["Router Agent (Phase 1)"]
ORCH_ROUTER --> ORCH_ROUTER_RESULT[Router Result]

ORCH_ROUTER_RESULT --> ORCH_ENABLED[Determine Enabled Agents]
ORCH_ENABLED --> ORCH_CONTEXT_AGENTS[Identify Context Agents]

ORCH_CONTEXT_AGENTS --> ORCH_PARALLEL[Execute Context Agents in Parallel]
ORCH_PARALLEL --> ORCH_RAG_TASK[RAG Agent Task]
ORCH_PARALLEL --> ORCH_WEB_TASK[Web Search Agent Task]
ORCH_PARALLEL --> ORCH_ATTACH_TASK[Attachment Agent Task]

ORCH_RAG_TASK --> ORCH_WAIT[Wait for All Context Agents]
ORCH_WEB_TASK --> ORCH_WAIT
ORCH_ATTACH_TASK --> ORCH_WAIT

ORCH_WAIT --> ORCH_CONTEXT_COMPLETE[Context Agents Complete]
ORCH_CONTEXT_COMPLETE --> ORCH_RESPONSE["Response Agent (Phase 3)"]
ORCH_RESPONSE --> ORCH_RESPONSE_RESULT[Response Result]

ORCH_RESPONSE_RESULT --> ORCH_CITATION_CHECK{Citation Agent Enabled?}
ORCH_CITATION_CHECK -->|Yes| ORCH_CITATION["Citation Agent (Phase 4)"]
ORCH_CITATION_CHECK -->|No| ORCH_FINAL[Final Response Assembly]

ORCH_CITATION --> ORCH_CITATION_RESULT[Citation Result]
ORCH_CITATION_RESULT --> ORCH_FINAL

ORCH_FINAL --> ORCH_METADATA[Add Workflow Metadata]
ORCH_METADATA --> ORCH_USAGE[Calculate Usage Stats]
ORCH_USAGE --> ORCH_COMPLETE[Orchestrator Complete]
```

## Agent Base Class Pattern

```mermaid
graph TD
%% ===========================================
%% BASE AGENT EXECUTION PATTERN
%% ===========================================
BASE_START["Agent.execute()"] --> BASE_TIMER[Start Execution Timer]
BASE_TIMER --> BASE_LOG[Log Agent Start]

BASE_LOG --> BASE_TRY[Try Block]
BASE_TRY --> BASE_IMPL["Call _execute_impl()"]
BASE_IMPL --> BASE_SUCCESS[Success Path]

BASE_SUCCESS --> BASE_RESULT[Create AgentResult]
BASE_RESULT --> BASE_TIME[Calculate Execution Time]
BASE_TIME --> BASE_LOG_SUCCESS[Log Success]

BASE_TRY --> BASE_CATCH[Catch Exception]
BASE_CATCH --> BASE_ERROR[Error Path]
BASE_ERROR --> BASE_ERROR_RESULT[Create Error AgentResult]
BASE_ERROR_RESULT --> BASE_LOG_ERROR[Log Error]

BASE_LOG_SUCCESS --> BASE_RETURN[Return Result]
BASE_LOG_ERROR --> BASE_RETURN
BASE_RETURN --> BASE_COMPLETE[Agent Complete]
```

## Request/Response Data Flow

```mermaid
graph TD
%% ===========================================
%% DATA FLOW THROUGH AGENTS
%% ===========================================
DATA_START[MultiAgentRequest] --> DATA_PARSE[Parse Request Data]
DATA_PARSE --> DATA_ROUTER[Router Agent Context]

DATA_ROUTER --> DATA_ROUTER_OUT[Router Output]
DATA_ROUTER_OUT --> DATA_CONTEXT[Context Agent Inputs]

DATA_CONTEXT --> DATA_RAG_IN[RAG Agent Input]
DATA_CONTEXT --> DATA_WEB_IN[Web Agent Input]
DATA_CONTEXT --> DATA_ATTACH_IN[Attachment Agent Input]

DATA_RAG_IN --> DATA_RAG_OUT[RAG Agent Output]
DATA_WEB_IN --> DATA_WEB_OUT[Web Agent Output]
DATA_ATTACH_IN --> DATA_ATTACH_OUT[Attachment Agent Output]

DATA_RAG_OUT --> DATA_RESPONSE_IN[Response Agent Input]
DATA_WEB_OUT --> DATA_RESPONSE_IN
DATA_ATTACH_OUT --> DATA_RESPONSE_IN

DATA_RESPONSE_IN --> DATA_RESPONSE_OUT[Response Agent Output]
DATA_RESPONSE_OUT --> DATA_CITATION_IN[Citation Agent Input]
DATA_CITATION_IN --> DATA_CITATION_OUT[Citation Agent Output]

DATA_CITATION_OUT --> DATA_FINAL[Final Response Assembly]
DATA_FINAL --> DATA_METADATA[Add Metadata & Usage]
DATA_METADATA --> DATA_RETURN[Return to Client]
```

## Agent Communication & Context Passing

```mermaid
graph TD
%% ===========================================
%% AGENT COMMUNICATION PATTERNS
%% ===========================================
COMM_START[Agent Communication] --> COMM_CONTEXT[Shared Context Dict]
COMM_CONTEXT --> COMM_ROUTER[Router Agent]

COMM_ROUTER --> COMM_ROUTER_DATA[Router Data]
COMM_ROUTER_DATA --> COMM_SHARED["context['router_agent']"]

COMM_SHARED --> COMM_RAG[RAG Agent Reads]
COMM_SHARED --> COMM_WEB[Web Agent Reads]
COMM_SHARED --> COMM_ATTACH[Attachment Agent Reads]

COMM_RAG --> COMM_RAG_STORE["context['rag_agent']"]
COMM_WEB --> COMM_WEB_STORE["context['web_search_agent']"]
COMM_ATTACH --> COMM_ATTACH_STORE["context['attachment_agent']"]

COMM_RAG_STORE --> COMM_RESPONSE[Response Agent Reads All]
COMM_WEB_STORE --> COMM_RESPONSE
COMM_ATTACH_STORE --> COMM_RESPONSE

COMM_RESPONSE --> COMM_RESPONSE_STORE["context['response_agent']"]
COMM_RESPONSE_STORE --> COMM_CITATION[Citation Agent Reads All]

COMM_CITATION --> COMM_FINAL[Final Result Assembly]
```

## Error Handling & Recovery

```mermaid
graph TD
%% ===========================================
%% ERROR HANDLING PATTERNS
%% ===========================================
ERROR_START[Agent Error] --> ERROR_CATCH[Exception Caught]
ERROR_CATCH --> ERROR_LOG[Log Error Details]

ERROR_LOG --> ERROR_RESULT[Create Error AgentResult]
ERROR_RESULT --> ERROR_SUCCESS["success: false"]
ERROR_SUCCESS --> ERROR_MESSAGE["error: str(e)"]

ERROR_MESSAGE --> ERROR_TIME["execution_time: calculated"]
ERROR_TIME --> ERROR_RETURN[Return Error Result]

ERROR_RETURN --> ERROR_CONTINUE[Continue Workflow]
ERROR_CONTINUE --> ERROR_FALLBACK[Fallback Strategies]

ERROR_FALLBACK --> ERROR_SKIP[Skip Failed Agent]
ERROR_SKIP --> ERROR_PARTIAL[Partial Response]
ERROR_PARTIAL --> ERROR_GRACEFUL[Graceful Degradation]
```

## Performance & Monitoring

```mermaid
graph TD
%% ===========================================
%% PERFORMANCE MONITORING
%% ===========================================
PERF_START[Performance Monitoring] --> PERF_WORKFLOW[Workflow Timer]
PERF_WORKFLOW --> PERF_AGENTS[Agent Timers]

PERF_AGENTS --> PERF_ROUTER[Router Agent Time]
PERF_AGENTS --> PERF_CONTEXT[Context Agents Time]
PERF_AGENTS --> PERF_RESPONSE[Response Agent Time]
PERF_AGENTS --> PERF_CITATION[Citation Agent Time]

PERF_ROUTER --> PERF_METRICS[Collect Metrics]
PERF_CONTEXT --> PERF_METRICS
PERF_RESPONSE --> PERF_METRICS
PERF_CITATION --> PERF_METRICS

PERF_METRICS --> PERF_USAGE[Usage Statistics]
PERF_USAGE --> PERF_ENABLED[Enabled Agents Count]
PERF_ENABLED --> PERF_TOTAL[Total Execution Time]

PERF_TOTAL --> PERF_METADATA[Add to Response Metadata]
PERF_METADATA --> PERF_CLIENT[Return to Client]
```

## Integration Points with Existing System

```mermaid
graph TD
%% ===========================================
%% INTEGRATION WITH EXISTING MODULES
%% ===========================================
INTEG_START[Multi-Agent Integration] --> INTEG_EXISTING[Existing Infrastructure]

INTEG_EXISTING --> INTEG_ROUTER[IntelligentRouter]
INTEG_EXISTING --> INTEG_RAG[RAGProcessor]
INTEG_EXISTING --> INTEG_WEB[WebSearchProcessor]
INTEG_EXISTING --> INTEG_ATTACH[FileAttachmentManager]
INTEG_EXISTING --> INTEG_LLM[LLMProviderSelector]
INTEG_EXISTING --> INTEG_CITATION[CitationEngine]

INTEG_ROUTER --> INTEG_ROUTER_AGENT[Router Agent Uses]
INTEG_RAG --> INTEG_RAG_AGENT[RAG Agent Uses]
INTEG_WEB --> INTEG_WEB_AGENT[Web Search Agent Uses]
INTEG_ATTACH --> INTEG_ATTACH_AGENT[Attachment Agent Uses]
INTEG_LLM --> INTEG_RESPONSE_AGENT[Response Agent Uses]
INTEG_CITATION --> INTEG_CITATION_AGENT[Citation Agent Uses]

INTEG_ROUTER_AGENT --> INTEG_SEAMLESS[Seamless Integration]
INTEG_RAG_AGENT --> INTEG_SEAMLESS
INTEG_WEB_AGENT --> INTEG_SEAMLESS
INTEG_ATTACH_AGENT --> INTEG_SEAMLESS
INTEG_RESPONSE_AGENT --> INTEG_SEAMLESS
INTEG_CITATION_AGENT --> INTEG_SEAMLESS

INTEG_SEAMLESS --> INTEG_BENEFITS[Benefits]
INTEG_BENEFITS --> INTEG_REUSE[Code Reuse]
INTEG_BENEFITS --> INTEG_MAINTAIN[Maintainability]
INTEG_BENEFITS --> INTEG_CONSISTENCY[Consistency]
```

## Future Enhancements

```mermaid
graph TD
%% ===========================================
%% FUTURE ENHANCEMENTS
%% ===========================================
FUTURE_START[Future Enhancements] --> FUTURE_STREAMING[Streaming Support]
FUTURE_STREAMING --> FUTURE_AGENT_STREAM[Agent-Level Streaming]
FUTURE_AGENT_STREAM --> FUTURE_PROGRESSIVE[Progressive Updates]

FUTURE_START --> FUTURE_DYNAMIC[Dynamic Agent Loading]
FUTURE_DYNAMIC --> FUTURE_PLUGINS[Plugin System]
FUTURE_PLUGINS --> FUTURE_CUSTOM[Custom Agents]

FUTURE_START --> FUTURE_PARALLEL[Enhanced Parallelism]
FUTURE_PARALLEL --> FUTURE_PIPELINE[Pipeline Optimization]
FUTURE_PIPELINE --> FUTURE_CACHING[Agent Result Caching]

FUTURE_START --> FUTURE_MONITORING[Advanced Monitoring]
FUTURE_MONITORING --> FUTURE_METRICS[Detailed Metrics]
FUTURE_METRICS --> FUTURE_ANALYTICS[Performance Analytics]

FUTURE_START --> FUTURE_RECOVERY[Advanced Recovery]
FUTURE_RECOVERY --> FUTURE_RETRY[Retry Mechanisms]
FUTURE_RETRY --> FUTURE_FALLBACK[Intelligent Fallbacks]
```

## Summary

This multi-agent architecture provides:

1. **Modular Design**: Each agent is self-contained and autonomous
2. **Parallel Execution**: Context agents run simultaneously for efficiency
3. **Flexible Workflow**: Easy to add/remove agents without breaking existing functionality
4. **Existing Infrastructure**: Leverages all current modular components
5. **Error Resilience**: Individual agent failures don't break the entire workflow
6. **Performance Monitoring**: Detailed timing and usage statistics
7. **Extensible**: Easy to add new agent types in the future

The system maintains backward compatibility while providing a more scalable and maintainable architecture for complex AI workflows.

```

```
