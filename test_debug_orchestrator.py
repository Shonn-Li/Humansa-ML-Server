"""Test debug orchestrator"""
import asyncio
import logging
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llama_index.llms.openai import OpenAI
from llama_index.core.workflow import StartEvent
from humansa.v2.workflows.debug_orchestrator import DebugHumansaOrchestrator
from humansa.v2.memory.memory_manager import MemoryManager
from humansa.v2.agents import GeneralMedicalAgent

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_debug_orchestrator():
    """Test the debug orchestrator"""
    try:
        # Initialize components
        llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        memory_manager = MemoryManager()
        agent = GeneralMedicalAgent(llm=llm)
        
        # Create orchestrator
        logger.info("Creating debug orchestrator...")
        orchestrator = DebugHumansaOrchestrator(
            agents=[agent],
            router_llm=llm,
            memory_manager=memory_manager
        )
        
        # Create start event
        logger.info("Creating start event...")
        start_event = StartEvent(
            query="Hello, test query",
            user_id="test123"
        )
        
        # Run orchestrator
        logger.info("Running orchestrator...")
        result = await orchestrator.run(start_event)
        logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_debug_orchestrator())