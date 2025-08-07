# Humansa V2 Enhanced Logging - Summary

## What Was Done

I've successfully created an enhanced logging system for the Humansa V2 tests that provides complete visibility into the multi-agent processing flow.

### Files Created/Modified:

1. **`run_humansa_test_environment_v2_enhanced.sh`** - Enhanced test script that:
   - Sets `HUMANSA_ENHANCED_LOGGING=true` environment variable
   - Creates an inline test script with streaming and debug enabled
   - Shows colored output for different event types
   - Displays full untruncated responses

2. **`src/humansa/v2/orchestrator_agent_enhanced.py`** - Enhanced orchestrator with:
   - Custom callback handlers for comprehensive event logging
   - Tracks thinking steps, agent calls, tool usage, and Mem0 events
   - Streams debug events alongside regular content

3. **`src/humansa/v2/api_enhanced.py`** - Enhanced API that:
   - Supports `debug: true` parameter in requests
   - Automatically uses enhanced orchestrator when debug is enabled
   - Streams debug events in SSE format
   - Provides summary statistics at the end

4. **`HUMANSA_V2_ENHANCED_LOGGING_GUIDE.md`** - Documentation explaining:
   - How to use the enhanced logging
   - Event types and their meanings
   - Troubleshooting guide

5. **`CLAUDE.md`** - Updated with:
   - Command to run enhanced V2 tests
   - Information about enhanced logging capabilities

## How to Use

### Option 1: Run the Enhanced Test Script (Recommended)
```bash
./run_humansa_test_environment_v2_enhanced.sh
```

This will:
- Start the server with enhanced logging enabled
- Run all 30 test cases with detailed output
- Show thinking process, agent calls, tool usage, and Mem0 events
- Display full responses without truncation
- Save detailed results to a JSON file

### Option 2: Enable Debug Mode in Individual Requests
Add `"debug": true` to any V2 chat request:
```json
{
  "user_id": "test_user",
  "messages": [{"role": "user", "content": "你是谁？"}],
  "stream": true,
  "debug": true
}
```

### Option 3: Enable Globally (Not Recommended for Production)
```bash
export HUMANSA_ENHANCED_LOGGING=true
python -m src.main
```

## What You'll See

The enhanced logging shows:
- 💭 **Thinking Steps**: Agent's reasoning process
- 🤖 **Agent Calls**: Which agents are invoked and when
- 🔧 **Tool Calls**: Tools used with parameters
- 📊 **Tool Results**: Outputs from tool executions
- 🧠 **Mem0 Events**: Memory system interactions
- 📝 **Full Response**: Complete untruncated output

Example output:
```
💭 Thinking: Analyzing user query for identity information...
🤖 Agent Called: general_medical_agent
🔧 Tool Called: memory_search_agent
   Parameters: {"query": "user preferences", "user_id": "test_user_1"}
🧠 Mem0 Data: {"memories": [], "count": 0}...
📝 Full Response: 我是诺亚新舟健康医疗助理（小诺）...
```

## Key Benefits

1. **Complete Visibility**: See the entire thought process and decision chain
2. **Debug Tool Usage**: Understand which tools are called and why
3. **Memory Integration**: Verify Mem0 is working and see what data it provides
4. **Performance Analysis**: Track timing and execution order
5. **Full Responses**: No truncation, see complete outputs

## Implementation Details

The enhanced logging works by:
1. Using LlamaIndex callback handlers to capture all agent events
2. Streaming these events as SSE debug chunks alongside content
3. Providing colored console output for better readability
4. Tracking and summarizing all events for analysis

The system is designed to have minimal impact when not in use - the enhanced orchestrator is only activated when debug mode is explicitly requested.