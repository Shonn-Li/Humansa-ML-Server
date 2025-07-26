"""Debug orchestrator recursion issue"""
import asyncio
import logging
from llama_index.llms.openai import OpenAI
from llama_index.core.workflow import StartEvent
from src.humansa.v2.workflows.orchestrator import HumansaOrchestrator
from src.humansa.v2.memory.memory_manager import MemoryManager
from src.humansa.v2.agents import GeneralMedicalAgent
import os

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_orchestrator():
    """Test the orchestrator directly"""
    try:
        # Initialize components
        llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        memory_manager = MemoryManager()
        agent = GeneralMedicalAgent(llm=llm)
        
        # Create orchestrator
        logger.info("Creating orchestrator...")
        orchestrator = HumansaOrchestrator(
            agents=[agent],
            router_llm=llm,
            memory_manager=memory_manager
        )
        
        # Create start event
        logger.info("Creating start event...")
        start_event = StartEvent(
            query="Hello",
            user_id="test123"
        )
        
        # Run orchestrator
        logger.info("Running orchestrator...")
        result = await orchestrator.run(start_event)
        logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_orchestrator())