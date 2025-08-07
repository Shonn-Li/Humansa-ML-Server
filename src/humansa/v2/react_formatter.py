"""
Custom ReAct formatter to ensure tool outputs are included in final answers
"""

from typing import List, Optional
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.agent.react.types import (
    BaseReasoningStep,
    ObservationReasoningStep,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole


class HumansaReActFormatter(ReActChatFormatter):
    """
    Custom ReAct formatter that ensures tool observations are incorporated
    into the final answer rather than just being intermediate steps.
    """
    
    def __init__(self):
        # Use a system prompt that emphasizes using tool outputs
        system_header = """You are designed to help with a variety of tasks, from answering questions to providing summaries to other types of analyses.

## Tools
You have access to a wide variety of tools. You are responsible for using the tools in any sequence you deem appropriate to complete the task at hand.
This may require breaking the task into subtasks and using different tools to complete each subtask.

## Output Format
To answer the question, please use the following format:

```
Thought: I need to use a tool to help me answer the question.
Action: tool name (one of {tool_names}) if using a tool.
Action Input: the input to the tool, in a JSON format representing the kwargs (e.g. {{"input": "hello world", "num_beams": 5}})
```

Please ALWAYS start with a Thought.

Please use a valid JSON format for the Action Input. Do NOT do this {{'input': 'hello world', 'num_beams': 5}}.

If this format is used, the user will respond in the following format:

```
Observation: tool response
```

You should keep repeating the above format until you have enough information to answer the question without using any more tools.

## CRITICAL: Final Answer Format

When you have collected all necessary information from tools, you MUST provide a comprehensive final answer that:
1. Directly incorporates the specific information from tool observations
2. Includes concrete details like product names, URLs, prices, dosages, etc. from the observations
3. Does NOT give generic advice - use the actual data returned by tools

At that point, you MUST respond in the one of the following two formats:

```
Thought: I can answer without using any more tools.
Answer: [Provide a comprehensive answer that includes ALL specific information from the tool observations. Do not summarize or generalize - include actual product names, links, details, etc.]
```

```
Thought: I cannot answer the question with the provided tools.
Answer: [explain why you cannot answer the question]
```

## Current Conversation
Below is the current conversation consisting of interleaving human and assistant messages.
"""
        
        super().__init__(system_header=system_header)
    
    def format(
        self,
        tools: List,
        chat_history: List,
        current_reasoning: Optional[List[BaseReasoningStep]] = None,
    ) -> List:
        """Format messages with emphasis on using tool outputs"""
        
        # Get base formatting
        messages = super().format(tools, chat_history, current_reasoning)
        
        # If we have observations in current reasoning, add a reminder
        if current_reasoning:
            observations = [
                step for step in current_reasoning 
                if isinstance(step, ObservationReasoningStep)
            ]
            
            if observations:
                # Add a system message reminding to use the observations
                reminder = ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="REMINDER: You have collected specific information from tools. Your final answer MUST include these specific details (product names, URLs, dosages, etc.) rather than generic advice."
                )
                messages.append(reminder)
        
        return messages


def get_humansa_react_formatter() -> ReActChatFormatter:
    """Get the custom ReAct formatter for HUMANSA"""
    try:
        return HumansaReActFormatter()
    except Exception as e:
        import logging
        logging.error(f"Failed to create custom formatter: {e}")
        # Fallback to default formatter
        return ReActChatFormatter()