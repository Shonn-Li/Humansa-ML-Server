"""
Agent-to-Tool Wrapper for HUMANSA V2 Sub-Agent Architecture
Converts sub-agents into LlamaIndex tools for orchestrator use
"""

import logging
from typing import Dict, Any, Optional, List
from llama_index.core.tools import FunctionTool
from llama_index.core.tools.types import ToolMetadata
import asyncio
import json

logger = logging.getLogger(__name__)


class AgentToolWrapper:
    """Wraps a sub-agent as a LlamaIndex tool"""
    
    def __init__(self, agent: Any, name: str, description: str):
        self.agent = agent
        self.name = name
        self.description = description
        
    async def __call__(self, query: str, **kwargs) -> str:
        """Execute the agent and return response"""
        try:
            # Process query through the agent
            context = kwargs.get('context', {})
            stream = kwargs.get('stream', False)
            
            # Collect response chunks
            response_chunks = []
            
            # Process through agent
            async for chunk in self.agent.process_query(query, context, stream=False):
                # Handle different chunk formats
                if chunk.get('type') == 'content':
                    response_chunks.append(chunk.get('chunk', ''))
                elif chunk.get('type') == 'error':
                    error_msg = chunk.get('chunk', 'Unknown error')
                    logger.error(f"Agent {self.name} error: {error_msg}")
                    return f"抱歉，{self.description}服务暂时出现问题：{error_msg}"
                elif 'response' in chunk:
                    # Handle base agent response format
                    response_chunks.append(chunk['response'])
                elif isinstance(chunk, str):
                    # Handle direct string responses
                    response_chunks.append(chunk)
            
            # Join all chunks into final response
            response = ''.join(response_chunks)
            return response
            
        except Exception as e:
            logger.error(f"Error in agent tool {self.name}: {e}")
            return f"抱歉，{self.description}服务出现错误：{str(e)}"


def create_agent_tool(agent: Any, name: str, description: str, 
                     input_description: str = None) -> FunctionTool:
    """
    Create a LlamaIndex FunctionTool from a sub-agent
    
    Args:
        agent: The sub-agent instance
        name: Tool name (e.g., "product_recommendation_agent")
        description: Tool description in Chinese
        input_description: Description of expected input
        
    Returns:
        FunctionTool instance
    """
    
    # Create wrapper
    wrapper = AgentToolWrapper(agent, name, description)
    
    # Default input description
    if input_description is None:
        input_description = "用户的查询或问题"
    
    # Create tool metadata
    metadata = ToolMetadata(
        name=name,
        description=description,
        fn_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": input_description
                }
            },
            "required": ["query"]
        }
    )
    
    # Create a synchronous wrapper for LlamaIndex compatibility
    def sync_wrapper(query: str, **kwargs) -> str:
        """Synchronous wrapper that runs the async agent"""
        import asyncio
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            if loop.is_running():
                # If loop is already running (e.g., in Jupyter), create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, wrapper(query, **kwargs))
                    return future.result()
            else:
                # Otherwise, run normally
                return loop.run_until_complete(wrapper(query, **kwargs))
        except Exception as e:
            logger.error(f"Error in sync wrapper: {e}")
            return f"错误：{str(e)}"
    
    # Create and return function tool with sync wrapper
    return FunctionTool.from_defaults(
        fn=sync_wrapper,
        name=name,
        description=description,
        return_direct=False  # Let orchestrator handle final response
    )


def create_subagent_tools(llm: Any, memory_manager: Any = None, 
                         db_config: Dict[str, Any] = None) -> List[FunctionTool]:
    """
    Create all sub-agent tools for the orchestrator
    
    Returns:
        List of FunctionTool instances
    """
    try:
        from .agents import (
            ProductAgent,
            AppointmentAgent, 
            DiagnosisAgent,
            EmergencyTriageAgent,
            GeneralMedicalAgent,
            MedicationAgent
        )
    except ImportError:
        from src.humansa.v2.agents import (
            ProductAgent,
            AppointmentAgent, 
            DiagnosisAgent,
            EmergencyTriageAgent,
            GeneralMedicalAgent,
            MedicationAgent
        )
    
    tools = []
    
    try:
        # 1. Product Recommendation Agent
        product_agent = ProductAgent(llm=llm)
        tools.append(create_agent_tool(
            agent=product_agent,
            name="product_recommendation_agent",
            description="专门处理产品推荐、保健品查询、医疗器械推荐、价格优惠等健康商城相关问题。可以推荐维生素、血压计、护肤品、中医养生产品等。",
            input_description="关于产品推荐、保健品、医疗器械的查询"
        ))
        logger.info("✅ Created Product Recommendation Agent tool")
        
        # 2. Appointment Booking Agent
        appointment_agent = AppointmentAgent(llm=llm)
        tools.append(create_agent_tool(
            agent=appointment_agent,
            name="appointment_booking_agent", 
            description="专门处理预约挂号、查询医生排班、预约改期、取消预约等就诊预约相关服务。支持按科室、医生、时间查询可用号源。",
            input_description="关于预约挂号、医生排班、改期取消的查询"
        ))
        logger.info("✅ Created Appointment Booking Agent tool")
        
        # 3. Clinical Analysis Agent (Diagnosis + Emergency Triage)
        diagnosis_agent = DiagnosisAgent(llm=llm)
        tools.append(create_agent_tool(
            agent=diagnosis_agent,
            name="clinical_analysis_agent",
            description="专门进行症状分析、疾病诊断建议、紧急情况识别（120急救）、科室推荐等医疗分析服务。可以分析症状严重程度并给出就医建议。",
            input_description="关于症状、疾病、紧急情况的医疗咨询"
        ))
        logger.info("✅ Created Clinical Analysis Agent tool")
        
        # 4. Medication Guidance Agent
        medication_agent = MedicationAgent(llm=llm)
        tools.append(create_agent_tool(
            agent=medication_agent,
            name="medication_guidance_agent",
            description="专门提供用药指导、药物相互作用检查、用药注意事项、药品信息查询等药物相关咨询服务。",
            input_description="关于药物使用、药品信息、用药安全的查询"
        ))
        logger.info("✅ Created Medication Guidance Agent tool")
        
        # 5. General Medical Agent
        general_agent = GeneralMedicalAgent(llm=llm)
        tools.append(create_agent_tool(
            agent=general_agent,
            name="general_medical_agent",
            description="处理一般医疗咨询、健康知识科普、保险政策、诊所位置查询等综合性医疗服务问题。",
            input_description="关于健康知识、保险、诊所等一般性咨询"
        ))
        logger.info("✅ Created General Medical Agent tool")
        
        # Log summary
        logger.info(f"✅ Created {len(tools)} sub-agent tools successfully")
        
    except Exception as e:
        logger.error(f"Error creating sub-agent tools: {e}")
        import traceback
        traceback.print_exc()
        
    return tools


def test_agent_tool():
    """Test function to verify agent tool creation"""
    from llama_index.llms.openai import OpenAI
    
    # Create a mock LLM
    llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)
    
    # Create tools
    tools = create_subagent_tools(llm)
    
    # Print tool info
    for tool in tools:
        print(f"Tool: {tool.metadata.name}")
        print(f"Description: {tool.metadata.description}")
        print("---")
    
    return tools


if __name__ == "__main__":
    # Run test
    test_agent_tool()