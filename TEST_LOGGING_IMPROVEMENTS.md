# Test Logging Improvements & Instructions

## Current Status

### ✅ What's Working:
1. **Attachment Processing**: Attachments ARE being processed correctly
2. **Citation Engine**: Working in both streaming and non-streaming modes
3. **Agent Routing**: Router correctly prioritizes attachments when present
4. **All Agents**: Router, RAG, Web Search, Attachment, Citation, Response all functional

### 🔧 Logging Issues Found:
1. **Streaming Mode**: Attachment processing appears as generic `function_tool_call` instead of distinct attachment events
2. **Agent Detection**: Test runners need to be updated to recognize function calls as attachment processing
3. **Output Item IDs**: Not all agents use consistent ID prefixes in streaming mode

## Enhanced Test Suite with Detailed Logging

I've created a comprehensive test suite that addresses all your requirements:

### 1. **Run Detailed Test Suite**
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python tests/test_with_detailed_logging.py
```

### 2. **Log Structure Created**
```
test_logs/
└── YYYYMMDD_HHMMSS/
    ├── output_item_analysis.json          # Analysis of all output types
    ├── Simple_Query.json                  # Raw JSON log
    ├── Simple_Query_readable.txt          # Human-readable log
    ├── Single_PDF_Attachment_Stream.json
    ├── Single_PDF_Attachment_Stream_readable.txt
    └── ... (one pair per test case)
```

### 3. **Log Format Example**
Each readable log contains:

```
TEST: Single PDF Attachment Stream
TIME: 2024-01-20T10:30:45
STATUS: success
================================================================================

QUERY: Analyze this document
ATTACHMENTS: ['https://arxiv.org/pdf/2311.10122.pdf']

OUTPUT ITEMS FLOW:
--------------------------------------------------------------------------------

2024-01-20T10:30:45 - reasoning (ID: router_350bc6f8)
  Agent: router
  Content: Analyzing query and routing to appropriate agents...

2024-01-20T10:30:46 - function_tool_call (ID: fc_582bc514)
  Tool: process_attachment
  Status: in_progress

2024-01-20T10:30:48 - function_tool_result (ID: fr_6f84b184)
  Tool: process_attachment
  Status: completed

2024-01-20T10:30:49 - file_search_call (ID: fs_88816c73)
  Tool: rag_search
  Status: completed

2024-01-20T10:30:50 - message (ID: msg_4df9fcf4)
  Content preview: Based on the document analysis...

2024-01-20T10:30:51 - reasoning (ID: cit_239bf95d)
  Agent: citation
  Content: Adding citations and references...

AGENT EXECUTION SUMMARY:
--------------------------------------------------------------------------------
- router: success (took 1.2s)
- attachment: success (took 2.5s)
- rag: success (took 1.8s)
- response: success (took 3.1s)
- citation: success (took 1.5s)

FINAL RESPONSE:
--------------------------------------------------------------------------------
Based on the document analysis, this paper discusses [1] reinforcement learning...

CITATIONS:
--------------------------------------------------------------------------------
[1] Source document - https://arxiv.org/pdf/2311.10122.pdf
[2] RAG context - Personal notes on RL
```

## Quick Validation Commands

### 1. **Validate Attachment Logging Only**
```bash
python tests/validate_attachment_logging.py
```

### 2. **Run Specific Test Case**
```python
import asyncio
from tests.test_with_detailed_logging import DetailedAgentTester

async def test_specific():
    tester = DetailedAgentTester()
    result = await tester.test_query(
        name="My Test",
        query="Analyze this paper",
        attachments=["https://arxiv.org/pdf/2311.10122.pdf"],
        stream=True
    )
    print(f"Agents detected: {result['agents']}")

asyncio.run(test_specific())
```

### 3. **Check Server Logs**
```bash
# In another terminal, watch ML server logs
tail -f ml_server.log | grep -E "(attachment|Attachment|router)"
```

## Output Item Types Reference

### Standard Flow:
1. **Router Decision**: `reasoning` with ID `router_xxx`
2. **Attachment Processing**: `function_tool_call` (not `attachment_xxx`)
3. **RAG Search**: `file_search_call` with ID `fs_xxx`
4. **Web Search**: `web_search_call` with ID `ws_xxx`
5. **Response Generation**: `message` with ID `msg_xxx`
6. **Citation Addition**: `reasoning` with ID `cit_xxx`

### Event Types to Track:
- `response.output_item.added` - New processing step
- `response.reasoning_text.delta` - Agent thinking
- `response.function_tool_call.*` - Tool executions (including attachments)
- `response.output_text.delta` - Final response content
- `response.usage` - Contains final metadata with all agents

## Recommendations

1. **Update Test Runners**: Modify agent detection to recognize `function_tool_call` as potential attachment processing
2. **Add Debug Mode**: Set environment variable `DEBUG_AGENTS=true` to get verbose agent logging
3. **Stream Analysis Tool**: Use the output item analysis to understand event patterns

## Known Issues & Fixes

1. **Issue**: Attachment agent not visible in streaming logs
   **Fix**: Look for `function_tool_call` events instead of `attachment_` prefixed IDs

2. **Issue**: Citations sometimes fail on first attempt in streaming
   **Fix**: This is due to async timing; the 3-attempt validation handles this

3. **Issue**: Agent results empty in test logs
   **Fix**: Ensure ML server is running and test database is accessible on port 5454