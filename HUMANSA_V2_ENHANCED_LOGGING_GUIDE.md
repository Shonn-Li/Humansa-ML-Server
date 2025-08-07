# Humansa V2 Enhanced Logging Guide

## Overview

The enhanced logging system for Humansa V2 provides comprehensive visibility into the entire multi-agent processing flow, including:

- Complete thinking process of each agent
- All agents called and their execution order
- Tool calls with parameters and results
- Mem0 integration status and memory data
- Full untruncated responses

## Using the Enhanced Test Script

### Basic Usage

```bash
# Activate virtual environment
source youwo-ml-venv/bin/activate

# Run the enhanced test
python test_humansa_v2_enhanced_logging.py
```

### What the Test Shows

1. **Health Check**: Shows all component statuses including Mem0
2. **Process Flow**: Real-time display of:
   - 💭 Thinking steps
   - 🤖 Agent invocations
   - 🔧 Tool calls with parameters
   - 📊 Tool results
   - 🧠 Mem0 memory data
   - 📝 Full response content

3. **Process Analysis**: After each test:
   - Agent execution flow timeline
   - Tool usage statistics
   - Thinking process summary
   - Mem0 integration status

### Test Output Example

```
╔═══════════════════════════════════════════════════════════════╗
║     Humansa V2 Enhanced Test Suite with Full Logging         ║
╚═══════════════════════════════════════════════════════════════╝

================================================================================
  Health Check
================================================================================
✅ V2 Health Check Passed
   Status: healthy
   Version: 2.0-enhanced

📦 Components:
   - orchestrator: True
   - enhanced_orchestrator: True
   - memory_manager: True
   - mem0: initialized

================================================================================
  Running Test 1/5
================================================================================

------------------------------------------------------------
  Test 1: Identity Query
------------------------------------------------------------
Query: 你是谁？
Expected: Should identify as 诺亚新舟健康医疗助理/小诺
Focus areas: identity, mem0_integration

🚀 Sending request...
✅ Connected, receiving stream...

💭 Thinking: Analyzing user query for identity information...
🤖 Agent Called: general_medical_agent
   Input: 你是谁？
🔧 Tool Called: memory_search_agent
   Parameters: {"query": "user preferences", "user_id": "test_user_1"}
🧠 Mem0 Data: {"memories": [], "count": 0}...
我是诺亚新舟健康医疗助理（小诺），是您的专业医疗AI助手...

⏱️  Total time: 2.34s

------------------------------------------------------------
  Process Analysis
------------------------------------------------------------

🤖 Agent Execution Flow:
   1. general_medical_agent (at 0.12s)
   2. memory_search_agent (at 0.45s)

🔧 Tools Used:
   - memory_search_agent: 1 call(s)

💭 Thinking Process Summary:
   Total thinking steps: 3
   First thought: Analyzing user query for identity information...
   Last thought: Preparing final response...

🧠 Mem0 Integration: Memory data available: Yes
   Data preview: {"memories": [], "count": 0}...

📝 Response Analysis:
   Response length: 245 characters
   Response preview: 我是诺亚新舟健康医疗助理（小诺）...
```

## Enabling Enhanced Logging on the Server

### Method 1: Environment Variable

```bash
# Enable enhanced logging globally
export HUMANSA_ENHANCED_LOGGING=true

# Start the server
python -m src.main
```

### Method 2: Debug Flag in Request

Include `debug: true` in your API request:

```json
{
  "user_id": "test_user",
  "messages": [
    {"role": "user", "content": "你是谁？"}
  ],
  "stream": true,
  "debug": true  // This enables enhanced logging for this request
}
```

### Method 3: Modify the Server Code

To use the enhanced API by default, update `src/main.py`:

```python
# Import the enhanced API instead
from humansa.v2.api_enhanced import humansa_v2_enhanced_bp, initialize_v2_enhanced_system

# Register the enhanced blueprint
app.register_blueprint(humansa_v2_enhanced_bp)

# Initialize with enhanced system
await initialize_v2_enhanced_system(db_pool, openai_api_key)
```

## Understanding the Debug Output

### Event Types

1. **thinking_start/thinking_end**: Agent reasoning process
2. **tool_call_start/tool_call_end**: Tool invocations
3. **memory/mem0_check**: Memory system interactions
4. **process_start**: Beginning of query processing
5. **debug.event**: Raw debug events from the orchestrator
6. **debug.summary**: Final summary of all events

### Streaming Format

When streaming is enabled with debug mode, you'll receive:

1. Regular content chunks:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion.chunk",
  "choices": [{
    "delta": {"content": "response text..."}
  }]
}
```

2. Debug event chunks:
```json
{
  "id": "debug-456",
  "object": "debug.event",
  "debug": {
    "type": "tool_call_start",
    "tool": "memory_search_agent",
    "input": {"query": "..."}
  }
}
```

3. Summary chunk (at the end):
```json
{
  "id": "summary-789",
  "object": "debug.summary",
  "summary": {
    "total_events": 15,
    "agent_calls": 3,
    "thinking_steps": 5,
    "memory_events": 2,
    "full_response": "complete response text..."
  }
}
```

## Troubleshooting

### No Debug Output
- Check if `debug: true` is in the request
- Verify `HUMANSA_ENHANCED_LOGGING` environment variable
- Ensure you're using the enhanced orchestrator

### Mem0 Not Working
- Check Mem0 initialization in server logs
- Verify PostgreSQL with pgvector is running
- Check `/v2/humansa/memory/status` endpoint

### Performance Impact
Enhanced logging adds overhead. For production:
- Disable `HUMANSA_ENHANCED_LOGGING`
- Don't include `debug: true` in requests
- Use standard orchestrator

## Test Results

All test results are saved with timestamps:
- `humansa_v2_enhanced_test_logs_YYYYMMDD_HHMMSS.json`

These files contain:
- Complete event logs
- Timing information
- All debug data
- Full responses

Use these for:
- Performance analysis
- Debugging agent behavior
- Understanding tool usage patterns
- Mem0 integration verification