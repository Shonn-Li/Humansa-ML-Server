# LlamaIndex Workflows Event Recursion Bug Workaround

## Issue Description

When using llama-index-workflows v1.2.0, there is a critical bug that causes infinite recursion when creating Event classes that inherit from the base Event class and use the `@dataclass` decorator.

### Error Message
```
RecursionError: maximum recursion depth exceeded while calling a Python object
```

## Root Cause

The bug occurs in the Event class implementation where the `__setattr__` method creates an infinite recursion loop when used with dataclass fields. This happens because:

1. The `@dataclass` decorator generates `__init__` and other methods that set attributes
2. The Event class overrides `__setattr__` to handle special behavior
3. When dataclass tries to set attributes, it triggers Event's `__setattr__`
4. This creates an infinite loop of attribute setting

## Affected Code Pattern

```python
from llama_index.core.workflow import Event
from dataclasses import dataclass

# This will cause recursion error
@dataclass
class MyEvent(Event):
    field1: str
    field2: Dict[str, Any]
```

## Workaround Implementation

### Option 1: Avoid @dataclass Decorator

Create Event classes without using `@dataclass`:

```python
class QueryAnalysisEvent(Event):
    """Initial query analysis results."""
    def __init__(self, **kwargs):
        super().__init__()
        self.query = kwargs.get('query', '')
        self.user_id = kwargs.get('user_id', '')
        self.intent = kwargs.get('intent', '')
        self.complexity = kwargs.get('complexity', '')
        self.required_capabilities = kwargs.get('required_capabilities', [])
        self.context = kwargs.get('context', {})
```

### Option 2: Simplify Workflow Architecture

Instead of complex multi-step workflows with event passing, use a single-step workflow that stores state in instance variables:

```python
class HumansaOrchestrator(Workflow):
    def __init__(self, agents, router_llm, memory_manager, **kwargs):
        super().__init__(**kwargs)
        self.agents = agents
        self.router_llm = router_llm
        self.memory_manager = memory_manager
        
        # Store workflow state in instance variables
        self._query = ""
        self._user_id = ""
        self._user_context = {}
        self._agent_responses = []
        
    @step
    async def process_query(self, ev: StartEvent) -> StopEvent:
        """Single-step processing to avoid multi-step event issues."""
        self._query = ev.get("query")
        self._user_id = ev.get("user_id")
        
        # Process everything in one step
        analysis = await self._analyze_query()
        selected_agents = await self._select_agents(analysis)
        agent_responses = await self._execute_agents(selected_agents)
        final_response = await self._synthesize_response(agent_responses)
        
        return StopEvent(result={"response": final_response})
```

## Implementation in This Project

We implemented the workaround in `/src/humansa/v2/workflows/orchestrator_workaround.py`:

1. Created Event classes without `@dataclass` decorator
2. Simplified the workflow to use a single-step architecture
3. Stored workflow state in instance variables instead of passing through events
4. This maintains full functionality while avoiding the recursion bug

## Testing

The workaround has been tested and verified to work correctly:
- No recursion errors
- Full multi-agent functionality maintained
- Memory integration works as expected
- Streaming responses supported

## Future Considerations

1. Monitor llama-index-workflows for bug fixes in future versions
2. When the bug is fixed, consider migrating back to the original multi-step event architecture
3. File an issue with the llama-index project if not already reported

## References

- Original error discovered: 2025-07-25
- Workaround implemented: 2025-07-25
- Affected version: llama-index-workflows v1.2.0
- Python version: 3.13