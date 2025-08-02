# Migration from ReActAgent to AgentWorkflow

## Summary

The current HUMANSA V2 implementation uses `ReActAgent` which cannot stream reasoning steps. We need to migrate to `FunctionAgent` + `AgentWorkflow` to expose the complete Think-Act-Observe reasoning chain in API responses.

## Current Architecture Problems

1. **ReActAgent Limitations**
   - `astream_chat()` only streams final response text
   - `verbose=True` prints to stdout, not to API response
   - No access to intermediate reasoning steps
   - GitHub issues confirm: "Stream not supported for function calling agent"

2. **Test Results Issue**
   - User complaint: "It didn't show its thinking and its individual agent thinking and response"
   - Current logs only show final responses and usage statistics
   - No visibility into orchestrator reasoning or sub-agent thinking

## Solution: AgentWorkflow Pattern

### Key Benefits
- `stream_events()` provides access to:
  - `AgentStream` - Real-time agent reasoning
  - `ToolCall` - Which sub-agents are called
  - `ToolCallResult` - Results from sub-agents
  - Full Think-Act-Observe visibility

### Implementation Status

✅ **Completed:**
1. Created `orchestrator_workflow.py` with proper streaming
2. Implemented OpenAI-compatible event streaming
3. Demonstrated the difference with comparison scripts

🚧 **In Progress:**
1. Converting sub-agents to FunctionAgent pattern
2. Updating API endpoint integration

📋 **TODO:**
1. Update `/v2/humansa/chat` endpoint to use WorkflowOrchestrator
2. Convert existing sub-agents to FunctionAgent
3. Update test suite to verify reasoning visibility
4. Update documentation

## Migration Steps

### Step 1: Update API Endpoint
```python
# In api.py, replace:
orchestrator = SubAgentOrchestrator(...)

# With:
orchestrator = WorkflowOrchestrator(...)
```

### Step 2: Update Streaming Response
The new orchestrator already outputs events compatible with our streaming standard:
- `response.reasoning_text.delta` - Agent thinking
- `response.output_item.added` - New reasoning/tool/message items
- `response.output_text.delta` - Final response text

### Step 3: Convert Sub-Agents
Each sub-agent needs to be converted from custom implementation to FunctionAgent:
```python
# Instead of custom BaseAgent
class ProductAgent(BaseAgent):
    async def process_query(...):
        # Custom logic

# Use FunctionAgent
product_agent = FunctionAgent(
    name="ProductAgent",
    tools=[...],
    system_prompt="...",
    llm=llm
)
```

### Step 4: Test Reasoning Visibility
Run test suite and verify output includes:
- Orchestrator reasoning steps
- Sub-agent selection logic
- Tool calls and results
- Complete reasoning chain

## Expected Test Output

```
Test Case: "我想买一些维生素C"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ORCHESTRATOR REASONING:
💭 用户询问维生素C产品推荐，这是产品相关查询，需要调用ProductAgent来处理。

🔧 CALLING SUB-AGENT: call_product_agent
💭 ProductAgent: 正在搜索维生素C产品...找到5个匹配产品，筛选推荐...

💬 FINAL RESPONSE:
根据您的需求，我推荐以下维生素C产品：1) 诺亚维C片 ¥89 2) 天然VC胶囊 ¥129

📊 Agents Used: ['Orchestrator', 'ProductAgent']
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Technical Notes

1. **Import Path**: LlamaIndex workflow components are in `llama_index.core.agent.workflow`
2. **Context Management**: Use `Context` object to maintain state across agents
3. **Event Streaming**: Events follow our existing `STREAMING_API_STANDARD.md`
4. **Backward Compatibility**: API response format remains OpenAI-compatible

## Next Steps

1. Complete sub-agent conversion
2. Update API endpoint
3. Run comprehensive tests
4. Document the new architecture