# OpenAI Streaming Handler Usage

## How to Use

1. Import the handler:

```python
from humansa.openai.openai_response_streaming_handler import OpenAIResponseStreamingHandler
```

2. Create an instance and stream a response:

```python
handler = OpenAIResponseStreamingHandler(model="gpt-4o-mini", system_prompt="You are a helpful assistant.")
async for event in handler.stream_openai_response(
    user_message="Tell me a joke."
):
    print(event)
```

3. For tool calling, pass a list of LlamaIndex FunctionTool objects:

```python
from llama_index.core.tools import FunctionTool

def add(a: int, b: int) -> int:
    return a + b

tool = FunctionTool.from_defaults(fn=add)
handler = OpenAIResponseStreamingHandler(model="gpt-4o-mini")
async for event in handler.stream_openai_response(
    user_message="Add 2 and 3",
    tools=[tool]
):
    print(event)
```

4. To use conversation history, pass a list of ChatMessage objects:

```python
from llama_index.core.llms import ChatMessage
history = [ChatMessage(role="user", content="Hello!"), ChatMessage(role="assistant", content="Hi!")]
async for event in handler.stream_openai_response(
    user_message="How are you?",
    conversation_history=history
):
    print(event)
```

## Requirements

- Install dependencies:

```sh
pip install -r requirements-openai.txt
```
