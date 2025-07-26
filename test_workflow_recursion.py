"""Test to isolate recursion issue"""
import asyncio
import logging
from typing import Dict, Any, List
from llama_index.core.workflow import (
    Workflow, StartEvent, StopEvent, step, Event
)
from dataclasses import dataclass

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test 1: Simple event
@dataclass
class SimpleEvent(Event):
    message: str

class Test1Workflow(Workflow):
    @step
    async def process(self, ev: StartEvent) -> SimpleEvent:
        logger.info("Test1: Returning simple event")
        return SimpleEvent(message="test")
    
    @step
    async def finish(self, ev: SimpleEvent) -> StopEvent:
        logger.info(f"Test1: Got message: {ev.message}")
        return StopEvent(result={"message": ev.message})

# Test 2: Event with Dict
@dataclass
class DictEvent(Event):
    data: Dict[str, Any]

class Test2Workflow(Workflow):
    @step
    async def process(self, ev: StartEvent) -> DictEvent:
        logger.info("Test2: Returning event with dict")
        return DictEvent(data={"key": "value", "nested": {"a": 1}})
    
    @step
    async def finish(self, ev: DictEvent) -> StopEvent:
        logger.info(f"Test2: Got data: {ev.data}")
        return StopEvent(result=ev.data)

# Test 3: Event with List
@dataclass
class ListEvent(Event):
    items: List[str]

class Test3Workflow(Workflow):
    @step
    async def process(self, ev: StartEvent) -> ListEvent:
        logger.info("Test3: Returning event with list")
        return ListEvent(items=["a", "b", "c"])
    
    @step
    async def finish(self, ev: ListEvent) -> StopEvent:
        logger.info(f"Test3: Got items: {ev.items}")
        return StopEvent(result={"items": ev.items})

# Test 4: Complex event (similar to orchestrator)
@dataclass
class ComplexEvent(Event):
    query: str
    context: Dict[str, Any]
    capabilities: List[str]

class Test4Workflow(Workflow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data = {"stored": "value"}
    
    @step
    async def process(self, ev: StartEvent) -> ComplexEvent:
        logger.info("Test4: Returning complex event")
        # Simulate user context
        context = {
            "user_id": "test",
            "profile": {"name": "Test User"},
            "history": [{"query": "old", "response": "data"}]
        }
        return ComplexEvent(
            query="test query",
            context=context,
            capabilities=["medical", "general"]
        )
    
    @step
    async def finish(self, ev: ComplexEvent) -> StopEvent:
        logger.info(f"Test4: Got query: {ev.query}")
        return StopEvent(result={"query": ev.query})

async def run_tests():
    """Run all tests"""
    tests = [
        ("Test 1 - Simple Event", Test1Workflow),
        ("Test 2 - Dict Event", Test2Workflow),
        ("Test 3 - List Event", Test3Workflow),
        ("Test 4 - Complex Event", Test4Workflow)
    ]
    
    for name, workflow_class in tests:
        print(f"\n{'='*50}")
        print(f"Running {name}")
        print("="*50)
        
        try:
            workflow = workflow_class()
            result = await workflow.run(start_event=StartEvent())
            print(f"✓ Success: {result}")
        except Exception as e:
            print(f"✗ Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_tests())