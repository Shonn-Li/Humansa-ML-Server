"""Minimal workflow test to debug issue"""
import asyncio
import logging
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MinimalWorkflow(Workflow):
    @step
    async def process(self, ev: StartEvent) -> StopEvent:
        logger.info("Processing event")
        data = ev.get("data", "no data")
        return StopEvent(result={"received": data})

async def test():
    try:
        workflow = MinimalWorkflow()
        # Try different ways to create the event
        logger.info("Creating event...")
        event = StartEvent(data="test")
        logger.info("Running workflow...")
        result = await workflow.run(event)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test())