"""
HUMANSA V2 Orchestrator - LlamaIndex Pattern 2 Implementation (Fixed)
Uses AgentWorkflow with FunctionAgent and proper Context management
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field

from llama_index.core.agent.workflow import (
    FunctionAgent,
    AgentWorkflow,
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult
)
from llama_index.core.workflow import Context
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import LLM
from llama_index.core.callbacks import CallbackManager

from .context_manager import UnifiedContext, ContextManager
from .memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """State that persists across agent tool calls"""
    # Workflow metadata
    workflow_id: str = ""
    conversation_id: str = ""
    user_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    
    # Patient context
    patient_profile: Dict[str, Any] = field(default_factory=dict)
    medical_history: List[Dict[str, Any]] = field(default_factory=list)
    current_medications: List[Dict[str, Any]] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    
    # Workflow execution state
    agents_called: List[str] = field(default_factory=list)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    reasoning_chain: List[str] = field(default_factory=list)
    
    # Final outputs
    emergency_flags: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_actions: List[str] = field(default_factory=list)
    
    # Form-related state
    active_forms: Dict[str, Any] = field(default_factory=dict)  # form_id -> form data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "workflow_id": self.workflow_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "patient_profile": self.patient_profile,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "allergies": self.allergies,
            "agents_called": self.agents_called,
            "agent_outputs": self.agent_outputs,
            "reasoning_chain": self.reasoning_chain,
            "emergency_flags": self.emergency_flags,
            "follow_up_actions": self.follow_up_actions,
            "active_forms": self.active_forms
        }


class HumansaOrchestratorPattern2Fixed:
    """
    Fixed LlamaIndex Pattern 2 Orchestrator for HUMANSA V2
    Uses AgentWorkflow with FunctionAgent properly
    """
    
    def __init__(
        self,
        llm: LLM,
        agents: Dict[str, Any],
        memory_manager: Optional[MemoryManager] = None,
        context_manager: Optional[ContextManager] = None,
        callback_manager: Optional[CallbackManager] = None,
        db_config: Optional[Dict[str, Any]] = None,
        db_pool: Optional[Any] = None,
        debug: bool = False
    ):
        self.llm = llm
        self.agents = agents
        self.memory_manager = memory_manager
        self.context_manager = context_manager or ContextManager()
        self.callback_manager = callback_manager
        self.db_config = db_config
        self.db_pool = db_pool
        self.debug = debug
        
        # Initialize form tools if database is configured
        self.form_tools = None
        self.form_service = None
        if self.db_pool or self.db_config:
            self.form_tools = True  # Flag to enable form tools
            logger.info("✅ Form tools enabled for appointment booking")
        
        # Create orchestrator tools from sub-agents
        self.orchestrator_tools = self._create_agent_tools()
        
        # We'll create the workflow per request to ensure clean state
        logger.info(f"✅ Initialized Pattern 2 Orchestrator (Fixed) with {len(self.orchestrator_tools)} agent tools")
    
    def _create_agent_tools(self) -> List[FunctionTool]:
        """Create tools from sub-agents"""
        tools = []
        
        # Store workflow state in a way tools can access
        self._current_state = None
        
        # Product Agent Tool
        def call_product_agent(query: str) -> str:
            """Search and recommend health products based on symptoms or needs"""
            logger.info(f"🛍️ ProductAgent called with: {query}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("ProductAgent")
                self._current_state.reasoning_chain.append(f"Searching for products related to: {query}")
            
            # Check if agent exists
            if agent := self.agents.get("ProductAgent"):
                try:
                    # Run the agent using asyncio.run
                    import asyncio
                    
                    async def run_agent():
                        result_parts = []
                        async for chunk in agent.process_query(
                            query=query,
                            context={
                                "patient_profile": self._current_state.patient_profile if self._current_state else {},
                                "allergies": self._current_state.allergies if self._current_state else []
                            },
                            stream=True
                        ):
                            if chunk.get('type') == 'content' and chunk.get('chunk'):
                                result_parts.append(chunk['chunk'])
                        return ''.join(result_parts)
                    
                    try:
                        result = asyncio.run(run_agent())
                    except RuntimeError as e:
                        # Already in an event loop, use create_task
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_agent())
                        else:
                            raise
                    
                    # Store results
                    if self._current_state:
                        self._current_state.agent_outputs["ProductAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"ProductAgent error: {e}")
                    return f"产品搜索时出现错误: {str(e)}"
            else:
                return "产品推荐服务暂时不可用"
        
        # Diagnosis Agent Tool
        def call_diagnosis_agent(symptoms: str) -> str:
            """Analyze symptoms and provide initial medical assessment"""
            logger.info(f"🔍 DiagnosisAgent called with: {symptoms}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("DiagnosisAgent")
                self._current_state.reasoning_chain.append(f"Analyzing symptoms: {symptoms}")
            
            if agent := self.agents.get("DiagnosisAgent", self.agents.get("ClinicalAgent")):
                try:
                    # Run the agent using asyncio.run
                    import asyncio
                    
                    async def run_agent():
                        result_parts = []
                        async for chunk in agent.process_query(
                            query=symptoms,
                            context={
                                "medical_history": self._current_state.medical_history if self._current_state else [],
                                "current_medications": self._current_state.current_medications if self._current_state else [],
                                "patient_profile": self._current_state.patient_profile if self._current_state else {}
                            },
                            stream=True
                        ):
                            if chunk.get('type') == 'content' and chunk.get('chunk'):
                                result_parts.append(chunk['chunk'])
                        return ''.join(result_parts)
                    
                    try:
                        result = asyncio.run(run_agent())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_agent())
                        else:
                            raise
                    
                    # Check for emergency
                    emergency_keywords = ["紧急", "急诊", "立即", "120", "危险", "严重"]
                    if any(keyword in result for keyword in emergency_keywords):
                        if self._current_state:
                            self._current_state.emergency_flags.append({
                                "type": "medical_emergency",
                                "details": result,
                                "timestamp": datetime.now().isoformat()
                            })
                            self._current_state.follow_up_actions.append("立即联系急救服务")
                    
                    # Store results
                    if self._current_state:
                        self._current_state.agent_outputs["DiagnosisAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"DiagnosisAgent error: {e}")
                    return f"症状分析服务暂时不可用: {str(e)}"
            else:
                return "症状分析服务暂时不可用"
        
        # General Medical Agent Tool
        def call_general_agent(question: str) -> str:
            """Answer general medical questions and provide health advice"""
            logger.info(f"🏥 GeneralAgent called with: {question}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("GeneralAgent")
                self._current_state.reasoning_chain.append(f"Answering general question: {question}")
            
            if agent := self.agents.get("GeneralAgent", self.agents.get("GeneralMedicalAgent")):
                try:
                    # Run the agent using asyncio.run
                    import asyncio
                    
                    async def run_agent():
                        result_parts = []
                        async for chunk in agent.process_query(
                            query=question,
                            context={
                                "patient_profile": self._current_state.patient_profile if self._current_state else {}
                            },
                            stream=True
                        ):
                            if chunk.get('type') == 'content' and chunk.get('chunk'):
                                result_parts.append(chunk['chunk'])
                        return ''.join(result_parts)
                    
                    try:
                        result = asyncio.run(run_agent())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_agent())
                        else:
                            raise
                    
                    # Store results
                    if self._current_state:
                        self._current_state.agent_outputs["GeneralAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"GeneralAgent error: {e}")
                    return f"医疗咨询服务暂时不可用: {str(e)}"
            else:
                return "医疗咨询服务暂时不可用"
        
        # Appointment Agent Tool
        def call_appointment_agent(request: str) -> str:
            """Search for doctors and handle appointment bookings"""
            logger.info(f"🏥 AppointmentAgent called with: {request}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("AppointmentAgent")
                self._current_state.reasoning_chain.append(f"Processing appointment request: {request}")
            
            if agent := self.agents.get("AppointmentAgent"):
                try:
                    # Run the agent using asyncio.run
                    import asyncio
                    
                    async def run_agent():
                        result_parts = []
                        async for chunk in agent.process_query(
                            query=request,
                            context={
                                "patient_profile": self._current_state.patient_profile if self._current_state else {},
                                "location": self._current_state.patient_profile.get("location", "北京") if self._current_state else "北京"
                            },
                            stream=True
                        ):
                            if chunk.get('type') == 'content' and chunk.get('chunk'):
                                result_parts.append(chunk['chunk'])
                        return ''.join(result_parts)
                    
                    try:
                        result = asyncio.run(run_agent())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_agent())
                        else:
                            raise
                    
                    # Store results
                    if self._current_state:
                        self._current_state.agent_outputs["AppointmentAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"AppointmentAgent error: {e}")
                    return f"预约服务暂时不可用: {str(e)}"
            else:
                return "预约服务暂时不可用"
        
        # Medication Agent Tool
        def call_medication_agent(query: str) -> str:
            """Provide medication information, interactions, and usage guidance"""
            logger.info(f"💊 MedicationAgent called with: {query}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("MedicationAgent")
                self._current_state.reasoning_chain.append(f"Checking medication information: {query}")
            
            if agent := self.agents.get("MedicationAgent"):
                try:
                    # Run the agent using asyncio.run
                    import asyncio
                    
                    async def run_agent():
                        result_parts = []
                        async for chunk in agent.process_query(
                            query=query,
                            context={
                                "current_medications": self._current_state.current_medications if self._current_state else [],
                                "allergies": self._current_state.allergies if self._current_state else []
                            },
                            stream=True
                        ):
                            if chunk.get('type') == 'content' and chunk.get('chunk'):
                                result_parts.append(chunk['chunk'])
                        return ''.join(result_parts)
                    
                    try:
                        result = asyncio.run(run_agent())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_agent())
                        else:
                            raise
                    
                    # Store results
                    if self._current_state:
                        self._current_state.agent_outputs["MedicationAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"MedicationAgent error: {e}")
                    return f"药物咨询服务暂时不可用: {str(e)}"
            else:
                return "药物咨询服务暂时不可用"
        
        # Create FunctionTool objects
        tools.append(FunctionTool.from_defaults(
            fn=call_product_agent,
            name="search_products",
            description="Search and recommend health products based on symptoms or needs"
        ))
        
        tools.append(FunctionTool.from_defaults(
            fn=call_diagnosis_agent,
            name="analyze_symptoms",
            description="Analyze medical symptoms and provide initial assessment"
        ))
        
        tools.append(FunctionTool.from_defaults(
            fn=call_general_agent,
            name="general_medical",
            description="Answer general medical questions and health advice"
        ))
        
        tools.append(FunctionTool.from_defaults(
            fn=call_appointment_agent,
            name="book_appointment",
            description="Search for doctors and book medical appointments"
        ))
        
        tools.append(FunctionTool.from_defaults(
            fn=call_medication_agent,
            name="medication_info",
            description="Provide medication information, drug interactions, and usage guidance"
        ))
        
        # Memory Tools
        def store_user_info(information: str) -> str:
            """Store user information like allergies, medications, preferences"""
            logger.info(f"💾 Storing user info: {information}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("MemoryStore")
                self._current_state.reasoning_chain.append(f"Storing user information: {information}")
                
                # Parse and store specific information
                if "过敏" in information:
                    # Extract allergy information
                    allergy_info = information.strip()
                    if allergy_info not in self._current_state.allergies:
                        self._current_state.allergies.append(allergy_info)
                        logger.info(f"Added allergy: {allergy_info}")
                
                if "吃" in information or "服用" in information or "药" in information:
                    # Store medication info
                    self._current_state.current_medications.append({
                        "info": information,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Store in Mem0 if available
                if self.memory_manager and self._current_state.user_id:
                    import asyncio
                    
                    async def store_memory():
                        try:
                            await self.memory_manager.add_memory(
                                user_id=self._current_state.user_id,
                                memory=information,
                                metadata={
                                    "type": "user_info",
                                    "source": "pattern2_orchestrator"
                                }
                            )
                            logger.info("✅ Stored in Mem0")
                        except Exception as e:
                            logger.error(f"Failed to store in Mem0: {e}")
                    
                    try:
                        asyncio.run(store_memory())
                    except RuntimeError:
                        # Already in event loop
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(store_memory())
                
                return "我已经记录了您的信息，会在后续服务中考虑。"
            else:
                return "抱歉，暂时无法存储信息。"
        
        def recall_user_info(query: str) -> str:
            """Recall stored user information"""
            logger.info(f"🔍 Recalling user info for: {query}")
            
            # Update state
            if self._current_state:
                self._current_state.agents_called.append("MemoryRecall")
                self._current_state.reasoning_chain.append(f"Recalling information about: {query}")
                
                # Check local state first
                if "过敏" in query and self._current_state.allergies:
                    allergies = ", ".join(self._current_state.allergies)
                    return f"根据记录，您有以下过敏信息：{allergies}"
                
                if "药" in query and self._current_state.current_medications:
                    meds = [med["info"] for med in self._current_state.current_medications]
                    return f"您正在服用的药物：{', '.join(meds)}"
                
                if "我的" in query or "信息" in query:
                    info_parts = []
                    if self._current_state.patient_profile:
                        name = self._current_state.patient_profile.get("name", "")
                        age = self._current_state.patient_profile.get("age", "")
                        if name:
                            info_parts.append(f"姓名：{name}")
                        if age:
                            info_parts.append(f"年龄：{age}")
                    
                    if self._current_state.allergies:
                        info_parts.append(f"过敏史：{', '.join(self._current_state.allergies)}")
                    
                    if info_parts:
                        return "您的基本信息：" + "；".join(info_parts)
                
                # Query Mem0 for more info
                if self.memory_manager and self._current_state.user_id:
                    import asyncio
                    
                    async def search_memory():
                        try:
                            memories = await self.memory_manager.search_memories(
                                user_id=self._current_state.user_id,
                                query=query,
                                limit=3
                            )
                            if memories:
                                return f"根据历史记录：{memories[0].get('memory', '')}"
                            return None
                        except Exception as e:
                            logger.error(f"Failed to search Mem0: {e}")
                            return None
                    
                    try:
                        mem0_result = asyncio.run(search_memory())
                        if mem0_result:
                            return mem0_result
                    except RuntimeError:
                        # Already in event loop
                        loop = asyncio.get_event_loop()
                        mem0_result = loop.run_until_complete(search_memory())
                        if mem0_result:
                            return mem0_result
                
                return "抱歉，我暂时没有找到相关的历史记录。"
            else:
                return "抱歉，暂时无法查询信息。"
        
        tools.append(FunctionTool.from_defaults(
            fn=store_user_info,
            name="store_user_info",
            description="Store user information like allergies, medications, medical history"
        ))
        
        tools.append(FunctionTool.from_defaults(
            fn=recall_user_info,
            name="recall_user_info", 
            description="Recall previously stored user information"
        ))
        
        # Form Tools for Appointment Booking
        if self.form_tools:
            def create_appointment_form(request: str) -> str:
                """Create appointment form from user request"""
                logger.info(f"📋 Creating appointment form for: {request}")
                
                # Update state
                if self._current_state:
                    self._current_state.agents_called.append("FormCreator")
                    self._current_state.reasoning_chain.append(f"Creating appointment form: {request}")
                
                try:
                    # Import form tools
                    import sys
                    import os
                    # Add the project root to path to import form tools
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    from src.humansa.v2.forms.form_tools import create_appointment_form as form_creator
                    
                    # Extract user_id from state
                    user_id = self._current_state.user_id if self._current_state else "unknown"
                    
                    # Create form using async function
                    import asyncio
                    
                    async def run_create_form():
                        result = await form_creator(
                            user_id=user_id,
                            query=request,
                            context={"source": "pattern2_orchestrator"}
                        )
                        return result
                    
                    try:
                        result = asyncio.run(run_create_form())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_create_form())
                        else:
                            raise
                    
                    # Store form in state if created
                    if result.get("success") and result.get("form_id"):
                        if self._current_state:
                            self._current_state.active_forms[result["form_id"]] = result
                    
                    # Format response
                    if result.get("success"):
                        return f"预约表单已创建（表单号：{result['form_id']}）\n\n{result.get('preview', '')}"
                    else:
                        return result.get("message", "创建预约表单失败")
                    
                except Exception as e:
                    logger.error(f"Form creation error: {e}")
                    return f"创建预约表单失败: {str(e)}"
            
            def update_appointment_form(form_id: str, updates: str) -> str:
                """Update existing appointment form"""
                logger.info(f"📝 Updating form {form_id} with: {updates}")
                
                # Update state
                if self._current_state:
                    self._current_state.agents_called.append("FormUpdater")
                    self._current_state.reasoning_chain.append(f"Updating form {form_id}: {updates}")
                
                try:
                    # Import form tools
                    import sys
                    import os
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    from src.humansa.v2.forms.form_tools import update_appointment_form as form_updater
                    
                    user_id = self._current_state.user_id if self._current_state else "unknown"
                    
                    # Update form using async function
                    import asyncio
                    
                    async def run_update_form():
                        result = await form_updater(
                            form_id=form_id,
                            user_input=updates,
                            user_id=user_id
                        )
                        return result
                    
                    try:
                        result = asyncio.run(run_update_form())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_update_form())
                        else:
                            raise
                    
                    # Update form in state
                    if result.get("success") and self._current_state and form_id in self._current_state.active_forms:
                        self._current_state.active_forms[form_id].update(result)
                    
                    # Format response
                    if result.get("success"):
                        return f"预约信息已更新\n\n{result.get('preview', '')}" 
                    else:
                        return result.get("message", "更新表单失败")
                    
                except Exception as e:
                    logger.error(f"Form update error: {e}")
                    return f"更新表单失败: {str(e)}"
            
            def submit_appointment_form(form_id: str) -> str:
                """Submit appointment form for booking"""
                logger.info(f"✅ Submitting form {form_id}")
                
                # Update state
                if self._current_state:
                    self._current_state.agents_called.append("FormSubmitter")
                    self._current_state.reasoning_chain.append(f"Submitting appointment form: {form_id}")
                
                try:
                    # Import form tools
                    import sys
                    import os
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    from src.humansa.v2.forms.form_tools import submit_appointment_form as form_submitter
                    
                    user_id = self._current_state.user_id if self._current_state else "unknown"
                    
                    # Submit form using async function
                    import asyncio
                    
                    async def run_submit_form():
                        result = await form_submitter(
                            form_id=form_id,
                            user_id=user_id
                        )
                        return result
                    
                    try:
                        result = asyncio.run(run_submit_form())
                    except RuntimeError as e:
                        if "already running" in str(e):
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(run_submit_form())
                        else:
                            raise
                    
                    # Remove form from active forms if successful
                    if result.get("success") and self._current_state and form_id in self._current_state.active_forms:
                        del self._current_state.active_forms[form_id]
                    
                    # Format response
                    if result.get("success"):
                        return result.get("message", "预约已成功提交")
                    else:
                        return result.get("message", "提交预约失败")
                    
                except Exception as e:
                    logger.error(f"Form submission error: {e}")
                    return f"提交预约失败: {str(e)}"
            
            # Add form tools
            tools.append(FunctionTool.from_defaults(
                fn=create_appointment_form,
                name="create_appointment_form",
                description="Create appointment booking form from user request. Use this when user wants to book an appointment."
            ))
            
            tools.append(FunctionTool.from_defaults(
                fn=update_appointment_form,
                name="update_appointment_form", 
                description="Update existing appointment form with new information"
            ))
            
            tools.append(FunctionTool.from_defaults(
                fn=submit_appointment_form,
                name="submit_appointment_form",
                description="Submit confirmed appointment form to complete booking"
            ))
        
        return tools
    
    def _get_orchestrator_prompt(self) -> str:
        """System prompt for the orchestrator"""
        # Import form instructions
        try:
            from src.humansa.v2.forms.form_tool_instructions import (
                APPOINTMENT_FORM_SCHEMA,
                FORM_COLLECTION_INSTRUCTIONS,
                ENHANCED_ORCHESTRATOR_PROMPT
            )
            form_instructions = ENHANCED_ORCHESTRATOR_PROMPT
        except:
            form_instructions = ""
        
        return f"""你是诺亚新舟健康医疗助理的主协调器。

今天是{datetime.now().strftime('%Y-%m-%d')}。

你的职责是：
1. 理解患者需求并协调专业代理
2. 确保医疗安全和全面护理
3. 整合所有代理的输出提供完整答案
4. 智能管理用户信息和对话记忆

{form_instructions}

可用的工具及使用场景：

【医疗咨询工具】
1. analyze_symptoms - 症状分析和初步评估
   使用场景：头痛、发烧、咳嗽、腹痛等任何症状描述
   
2. book_appointment - 医生搜索和预约服务（仅用于查询医生信息）
   使用场景：查找医生、查询医院、科室信息
   注意：实际预约请使用 create_appointment_form
   
3. search_products - 健康产品推荐
   使用场景：保健品、维生素、医疗器械、健康产品推荐
   
4. medication_info - 药物信息咨询
   使用场景：药物用法、副作用、药物相互作用、用药指导
   
5. general_medical - 一般医疗咨询
   使用场景：健康建议、预防知识、生活方式指导、不属于上述类别的问题

【记忆管理工具】
6. store_user_info - 存储用户信息
   使用场景：当用户提到个人信息时主动存储，包括：
   - 过敏史（如：我对青霉素过敏）
   - 用药情况（如：我在吃降压药）
   - 医疗史（如：我有高血压）
   - 个人偏好（如：我不喜欢吃药片）
   - 基本信息（如：年龄、性别、位置）
   
7. recall_user_info - 调用用户信息
   使用场景：
   - 提供个性化建议前查询用户过敏史
   - 推荐药物前查询现有用药
   - 用户询问"我的信息"、"我之前说过什么"
   - 需要考虑用户特殊情况时

【预约表单工具】
8. create_appointment_form - 创建预约表单
   使用场景：用户想要预约医生时使用
   - 从用户描述中提取预约信息
   - 返回form_id供确认
   
9. update_appointment_form - 更新预约表单
   使用场景：用户想要修改预约信息
   
10. submit_appointment_form - 提交预约表单
    使用场景：用户确认预约信息后提交

工具选择原则：
- 优先根据用户意图选择最相关的工具
- 症状相关问题必须使用 analyze_symptoms
- 查询医生信息使用 book_appointment
- 实际预约医生使用 create_appointment_form
- 产品推荐使用 search_products
- 药物相关使用 medication_info
- 其他健康咨询使用 general_medical
- 用户提到个人信息时主动使用 store_user_info 存储
- 提供建议前使用 recall_user_info 查询相关历史
- 可以根据需要调用多个工具

预约流程：
1. 用户表达预约意图时，使用 create_appointment_form 创建表单
2. 表单返回 form_id 和预览信息
3. 如果用户要修改，使用 update_appointment_form
4. 用户确认后，使用 submit_appointment_form 完成预约

记忆管理原则：
- 主动记录：用户提到重要个人信息时立即存储
- 智能调用：在提供医疗建议前查询相关历史
- 安全考虑：推荐药物或治疗前必须查询过敏史
- 个性化服务：基于用户历史提供定制化建议

紧急情况识别：
- 胸痛、呼吸困难、严重出血等立即提醒就医
- 意识模糊、严重过敏反应等需要紧急处理

请基于收集到的信息提供专业、准确、有帮助的医疗建议，并充分利用记忆系统提供个性化服务。"""
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, Any]] = None,
        stream: bool = True,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process query through Pattern 2 orchestrator with streaming support
        """
        try:
            # Create workflow state
            self._current_state = WorkflowState(
                workflow_id=f"wf_{datetime.now().timestamp()}",
                conversation_id=session_id or f"conv_{datetime.now().timestamp()}",
                user_id=user_id
            )
            
            # Load patient memory if available
            if self.memory_manager:
                try:
                    patient_memory = await self.memory_manager.get_user_context(user_id)
                    if patient_memory:
                        self._current_state.patient_profile = patient_memory.get("profile", {})
                        self._current_state.medical_history = patient_memory.get("medical_history", [])
                        self._current_state.current_medications = patient_memory.get("medications", [])
                        self._current_state.allergies = patient_memory.get("allergies", [])
                        logger.info(f"Loaded patient memory for {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to load patient memory: {e}")
            
            # Create FunctionAgent
            function_agent = FunctionAgent(
                name="HumansaOrchestrator",
                description="Medical consultation orchestrator",
                system_prompt=self._get_orchestrator_prompt(),
                llm=self.llm,
                tools=self.orchestrator_tools,
                verbose=self.debug
            )
            
            # Create workflow with the agent
            workflow = AgentWorkflow(agents=[function_agent])
            
            # Create context
            ctx = Context(workflow)
            
            # Store state in context
            await ctx.set("workflow_state", self._current_state.to_dict())
            
            # Build enhanced query
            enhanced_query = self._build_enhanced_query(query, messages)
            
            logger.info(f"Running Pattern 2 workflow with query: {query[:100]}...")
            
            if stream:
                # Stream the response
                async for event in self._stream_workflow_response(
                    workflow, ctx, enhanced_query
                ):
                    yield event
            else:
                # Non-streaming response
                result = await self._process_non_streaming(
                    workflow, ctx, enhanced_query
                )
                yield result
                
        except Exception as e:
            logger.error(f"Error in Pattern 2 orchestrator: {e}", exc_info=True)
            
            yield {
                "error": {
                    "message": str(e),
                    "type": "orchestrator_error"
                }
            }
    
    async def _stream_workflow_response(
        self,
        workflow: AgentWorkflow,
        ctx: Context,
        query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream workflow response with event handling"""
        
        stream_id = f"chatcmpl-{self._current_state.conversation_id}"
        created_time = int(datetime.now().timestamp())
        sequence_num = 0
        
        # Start response
        yield {
            "type": "response.created",
            "sequence_number": sequence_num,
            "response": {
                "id": stream_id,
                "object": "chat.completion",
                "created_at": created_time,
                "status": "in_progress",
                "model": "humansa-v2-pattern2-fixed",
                "output": []
            }
        }
        sequence_num += 1
        
        try:
            # Run workflow
            handler = workflow.run(user_msg=query, ctx=ctx)
            
            full_response = ""
            reasoning_steps = []
            tools_called = []
            
            # Stream events
            async for event in handler.stream_events():
                event_type = type(event).__name__
                
                if isinstance(event, AgentInput):
                    logger.debug(f"Agent starting: {event}")
                    
                elif isinstance(event, AgentStream):
                    # This is the agent's thinking/response
                    if hasattr(event, 'delta'):
                        delta = str(event.delta)
                        full_response += delta
                        
                        # Stream delta
                        yield {
                            "type": "response.output_item.delta",
                            "sequence_number": sequence_num,
                            "delta": {
                                "type": "text_delta",
                                "text": delta
                            }
                        }
                        sequence_num += 1
                
                elif isinstance(event, ToolCall):
                    # Tool being called
                    tool_name = getattr(event, 'tool_name', 'Unknown')
                    reasoning_steps.append(f"Calling tool: {tool_name}")
                    tools_called.append(tool_name)
                    logger.info(f"🔧 Tool call: {tool_name}")
                
                elif isinstance(event, ToolCallResult):
                    # Tool result
                    result = getattr(event, 'result', 'No result')
                    logger.debug(f"Tool result: {str(result)[:100]}...")
                
                elif isinstance(event, AgentOutput):
                    # Final output
                    if hasattr(event, 'response'):
                        response_text = str(event.response)
                        if response_text and response_text != full_response:
                            full_response = response_text
            
            # Get final state from context
            final_state_dict = await ctx.get("workflow_state")
            
            # Log final context
            logger.info("="*60)
            logger.info("PATTERN 2 FINAL CONTEXT (Fixed)")
            logger.info("="*60)
            logger.info(f"Workflow ID: {self._current_state.workflow_id}")
            logger.info(f"Agents Called: {self._current_state.agents_called}")
            logger.info(f"Tools Used: {tools_called}")
            logger.info("="*60)
            
            # Create final message
            message_item = {
                "id": f"msg_{sequence_num}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": full_response
                    }
                ],
                "created_at": datetime.now().isoformat() + "Z",
                "completed_at": datetime.now().isoformat() + "Z",
                "output_index": 0
            }
            
            # Add message item
            yield {
                "type": "response.output_item.added",
                "sequence_number": sequence_num,
                "output_index": 0,
                "item": message_item
            }
            sequence_num += 1
            
            # Add reasoning if available
            if reasoning_steps:
                yield {
                    "type": "response.reasoning",
                    "sequence_number": sequence_num,
                    "reasoning": reasoning_steps
                }
                sequence_num += 1
            
            # Add usage metadata
            yield {
                "type": "response.usage",
                "sequence_number": sequence_num,
                "usage": {
                    "agents_used": self._current_state.agents_called,
                    "total_agents": len(self._current_state.agents_called),
                    "workflow_id": self._current_state.workflow_id,
                    "emergency_flags": self._current_state.emergency_flags,
                    "follow_up_actions": self._current_state.follow_up_actions
                }
            }
            sequence_num += 1
            
            # Complete response
            yield {
                "type": "response.completed",
                "sequence_number": sequence_num,
                "response": {
                    "id": stream_id,
                    "status": "completed",
                    "object": "chat.completion",
                    "output": [message_item]
                }
            }
            
        except Exception as e:
            logger.error(f"Error in workflow streaming: {e}", exc_info=True)
            
            error_item = {
                "id": f"msg_error_{sequence_num}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{
                    "type": "output_text",
                    "text": f"处理请求时出现错误: {str(e)}"
                }],
                "created_at": datetime.now().isoformat() + "Z",
                "output_index": 0
            }
            
            yield {
                "type": "response.output_item.added",
                "sequence_number": sequence_num,
                "output_index": 0,
                "item": error_item
            }
    
    async def _process_non_streaming(
        self,
        workflow: AgentWorkflow,
        ctx: Context,
        query: str
    ) -> Dict[str, Any]:
        """Process without streaming"""
        try:
            # Run workflow
            handler = workflow.run(user_msg=query, ctx=ctx)
            
            # Collect full response
            full_response = ""
            async for event in handler.stream_events():
                if isinstance(event, AgentStream) and hasattr(event, 'delta'):
                    full_response += str(event.delta)
                elif isinstance(event, AgentOutput) and hasattr(event, 'response'):
                    full_response = str(event.response)
            
            return {
                "id": f"chatcmpl-{self._current_state.conversation_id}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "humansa-v2-pattern2-fixed",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "agents_used": self._current_state.agents_called,
                    "total_agents": len(self._current_state.agents_called),
                    "workflow_state": self._current_state.to_dict()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in non-streaming processing: {e}", exc_info=True)
            return {
                "id": f"chatcmpl-error",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "humansa-v2-pattern2-fixed",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"处理请求时出现错误: {str(e)}"
                    },
                    "finish_reason": "error"
                }],
                "error": {
                    "message": str(e),
                    "type": "processing_error"
                }
            }
    
    def _build_enhanced_query(
        self,
        query: str,
        messages: List[Dict[str, Any]] = None
    ) -> str:
        """Build enhanced query with context"""
        parts = []
        
        # Add patient context if available
        if self._current_state and self._current_state.patient_profile:
            parts.append(f"患者信息: {json.dumps(self._current_state.patient_profile, ensure_ascii=False)}")
        
        # Add conversation history
        if messages and len(messages) > 1:
            recent = messages[-3:-1] if len(messages) > 3 else messages[:-1]
            history = []
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history.append(f"{role}: {content}")
            if history:
                parts.append(f"近期对话:\n" + "\n".join(history))
        
        # Add current query
        parts.append(f"当前问题: {query}")
        
        return "\n\n".join(parts)


# Factory function
def create_pattern2_orchestrator_fixed(
    llm: LLM,
    agents: Dict[str, Any],
    memory_manager: Optional[MemoryManager] = None,
    db_config: Optional[Dict[str, Any]] = None,
    db_pool: Optional[Any] = None,
    debug: bool = False
) -> HumansaOrchestratorPattern2Fixed:
    """
    Create a fixed Pattern 2 orchestrator instance
    
    Args:
        llm: Language model
        agents: Dictionary of initialized sub-agents
        memory_manager: Memory manager for persistence
        db_config: Database configuration
        db_pool: Database connection pool
        debug: Enable debug logging
        
    Returns:
        HumansaOrchestratorPattern2Fixed instance
    """
    return HumansaOrchestratorPattern2Fixed(
        llm=llm,
        agents=agents,
        memory_manager=memory_manager,
        db_config=db_config,
        db_pool=db_pool,
        debug=debug
    )