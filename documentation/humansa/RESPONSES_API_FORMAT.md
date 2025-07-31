# OpenAI Responses API Format Documentation

## Overview

The HUMANSA V2 system now implements the proper OpenAI Responses API format, which provides full transparency into the AI's reasoning process and tool usage. This document explains the actual format based on OpenAI's implementation.

## Key Concepts

### 1. Output Array Structure

The core of the Responses API is the `output` array, which contains a complete record of the AI's reasoning chain:

```json
{
  "id": "resp_abc123",
  "object": "response",
  "created": 1234567890,
  "model": "gpt-4-turbo",
  "output": [
    {
      "type": "text",
      "text": "Let me search for information about Dr. Zhang..."
    },
    {
      "type": "tool_use",
      "tool_use": {
        "id": "tool_0",
        "name": "search_doctors",
        "input": {"specialty": "neurology", "name": "张医生"}
      }
    },
    {
      "type": "tool_result",
      "tool_result": {
        "tool_use_id": "tool_0",
        "output": "Found Dr. Zhang Wei, Neurology specialist..."
      }
    },
    {
      "type": "text",
      "text": "Based on my search, Dr. Zhang Wei is a neurology specialist..."
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 250,
    "total_tokens": 350,
    "reasoning_tokens": 150,
    "tool_tokens": 100
  }
}
```

### 2. Output Item Types

#### Text Output
Represents the AI's thoughts, reasoning, and responses:
```json
{
  "type": "text",
  "text": "The actual text content..."
}
```

#### Tool Use
Records when the AI decides to use a tool:
```json
{
  "type": "tool_use",
  "tool_use": {
    "id": "tool_0",
    "name": "appointment_manager",
    "input": {
      "action": "check_availability",
      "doctor": "Dr. Zhang"
    }
  }
}
```

#### Tool Result
Contains the output from tool execution:
```json
{
  "type": "tool_result",
  "tool_result": {
    "tool_use_id": "tool_0",
    "output": "Available slots: Friday 3pm, Monday 10am",
    "is_error": false
  }
}
```

### 3. Streaming Events

When streaming is enabled, responses use event-based format:

#### response.created
Sent when a new response begins:
```json
{
  "event": "response.created",
  "data": {
    "id": "resp_xyz789",
    "object": "response",
    "created": 1234567890,
    "model": "gpt-4-turbo"
  }
}
```

#### response.output_item.delta
Streams partial content for text items:
```json
{
  "event": "response.output_item.delta",
  "data": {
    "output_index": 0,
    "item": {
      "type": "text",
      "text": "Let me check"
    }
  }
}
```

#### response.output_item.done
Completes an output item:
```json
{
  "event": "response.output_item.done",
  "data": {
    "output_index": 0,
    "item": {
      "type": "text",
      "text": "Let me check the doctor's availability."
    }
  }
}
```

#### response.done
Final event with complete response:
```json
{
  "event": "response.done",
  "data": {
    "id": "resp_xyz789",
    "object": "response",
    "created": 1234567890,
    "model": "gpt-4-turbo",
    "output": [...],
    "usage": {...}
  }
}
```

## API Endpoints

### Create Response

**POST** `/v2/humansa/responses/create`

Creates a new response with full reasoning transparency.

Request:
```json
{
  "model": "gpt-4-turbo",
  "input": "帮我查询神经内科的医生",
  "user_id": "user123",
  "previous_response_id": "resp_abc123",  // Optional
  "metadata": {}  // Optional
}
```

Response includes the full output array showing all reasoning steps and tool calls.

### Stream Response

**POST** `/v2/humansa/responses/stream`

Creates a streaming response with event-based format.

Request:
```json
{
  "model": "gpt-4-turbo",
  "input": "我想预约周五下午",
  "previous_response_id": "resp_abc123"  // Optional
}
```

Response: Server-Sent Events stream with proper event format.

### Get Response

**GET** `/v2/humansa/responses/{response_id}`

Retrieves a response with its full conversation history.

### Get Conversation Tree

**GET** `/v2/humansa/responses/conversations/{conversation_id}/tree`

Shows the complete conversation tree including all branches (forks).

## Key Benefits

1. **Full Transparency**: Users can see exactly what the AI is thinking and which tools it uses
2. **Debugging**: Complete reasoning chain helps identify where issues occur
3. **Trust**: Users understand how the AI arrives at its conclusions
4. **Reproducibility**: The complete chain can be analyzed and replicated
5. **Fork Support**: Conversations can branch for exploring different paths

## Implementation Details

### Transparent Orchestrator

The `HumansaOrchestratorAgentTransparent` class captures all reasoning steps using a callback handler:

```python
class ToolCallCapture(BaseCallbackHandler):
    """Captures tool calls and reasoning steps"""
    
    def on_event_end(self, event_type, payload, **kwargs):
        if event_type == CBEventType.FUNCTION_CALL:
            # Capture tool use and result
            self.captured_steps.append({
                "type": "tool_use",
                "tool_name": payload["function_call"]["name"],
                "tool_input": payload["function_call"]["arguments"]
            })
```

### Response Formatter

The `ResponseFormatter` class converts LlamaIndex outputs to proper format:

```python
def format_agent_response(self, agent_response):
    # Extract reasoning steps
    output_items = self._extract_output_items(agent_response)
    
    # Build proper response format
    return {
        "id": response_id,
        "output": output_items,
        "usage": self._calculate_usage(output_items)
    }
```

## Example: Medical Consultation Flow

Here's how a typical medical consultation appears in the new format:

1. **User Query**: "我想看神经内科医生"

2. **AI Reasoning** (text output): "用户想要看神经内科医生，让我搜索可用的医生..."

3. **Tool Use**: Search for neurology doctors
   ```json
   {
     "type": "tool_use",
     "tool_use": {
       "id": "tool_0",
       "name": "unified_search",
       "input": {"query": "神经内科医生", "search_type": "doctor"}
     }
   }
   ```

4. **Tool Result**: List of available doctors
   ```json
   {
     "type": "tool_result",
     "tool_result": {
       "tool_use_id": "tool_0",
       "output": "Found 3 neurology specialists: Dr. Zhang Wei..."
     }
   }
   ```

5. **Final Response** (text output): "我为您找到了3位神经内科医生..."

This format ensures users can follow the entire reasoning process, building trust and understanding.