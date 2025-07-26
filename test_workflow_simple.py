"""Test simplified workflow to debug recursion"""
import asyncio
import logging
from typing import Dict, Any
from llama_index.core.workflow import (
    Workflow, StartEvent, StopEvent, step, Context, Event
)
from dataclasses import dataclass

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class Step1Event(Event):
    data: str

@dataclass
class Step2Event(Event):
    data: str

class TestWorkflow(Workflow):
    @step
    async def step1(self, ctx: Context, ev: StartEvent) -> Step1Event:
        logger.info("Step 1 executing")
        # Test context usage
        ctx.set("test_key", "test_value")
        return Step1Event(data="from_step1")
    
    @step
    async def step2(self, ctx: Context, ev: Step1Event) -> Step2Event:
        logger.info("Step 2 executing")
        # Try to read from context
        value = ctx.get("test_key", "default")
        logger.info(f"Context value: {value}")
        return Step2Event(data=f"from_step2_{ev.data}")
    
    @step
    async def final_step(self, ctx: Context, ev: Step2Event) -> StopEvent:
        logger.info("Final step executing")
        return StopEvent(result={"final": ev.data})

async def test_workflow():
    """Test basic workflow"""
    try:
        workflow = TestWorkflow()
        start = StartEvent()
        result = await workflow.run(start)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_workflow())