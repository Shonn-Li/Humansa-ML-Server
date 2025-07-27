"""
Humansa V2 Orchestrator Agent - LlamaIndex Pattern 2
An orchestrator agent that uses sub-agents as tools for coordination
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import LLM
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
import logging
import json
import time
from datetime import datetime

# Agent imports will be simplified for now
from .memory.memory_manager import MemoryManager
from humansa.prompts.humansa_system_prompt_v2 import get_humansa_system_prompt_v2

logger = logging.getLogger(__name__)

# Import real Humansa tools if available
try:
    from humansa.tools.humansa_tools import HumansaAgenticToolManager
    REAL_TOOLS_AVAILABLE = True
except ImportError:
    logger.warning("Real Humansa tools not available, using simplified functions")
    REAL_TOOLS_AVAILABLE = False


class HumansaOrchestratorAgent:
    """
    LlamaIndex Pattern 2 Orchestrator: Uses sub-agents as tools
    Coordinates multiple specialized agents to handle medical queries
    """
    
    def __init__(
        self,
        llm: LLM,
        agents: List[Any] = None,
        memory_manager: Optional[MemoryManager] = None,
        debug: bool = False,
        use_real_tools: bool = True,
        db_config: Optional[Dict] = None
    ):
        self.llm = llm
        self.memory_manager = memory_manager
        self.debug = debug
        self.use_real_tools = use_real_tools and REAL_TOOLS_AVAILABLE
        
        # Initialize debug handler if needed
        self.debug_handler = LlamaDebugHandler() if debug else None
        self.callback_manager = CallbackManager([self.debug_handler]) if self.debug_handler else None
        
        # For now, we'll use simple agent functions instead of complex agent classes
        self.agents = {}
        
        # Initialize real tool manager if available
        self.tool_manager = None
        if self.use_real_tools:
            try:
                self.tool_manager = HumansaAgenticToolManager(db_config)
                # Set the LLM and callback manager
                self.tool_manager.llm = self.llm
                self.tool_manager.callback_manager = self.callback_manager
                logger.info("✅ Real Humansa tools initialized for V2 orchestrator")
            except Exception as e:
                logger.error(f"❌ Failed to initialize real tools: {e}")
                self.use_real_tools = False
        
        # Create tools from agent functions or real tools
        self.tools = self._create_agent_tools()
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Full orchestrator prompt - no token limits with GPT-4.1 (1M tokens)!
        orchestrator_prompt = f"""你是诺亚新舟健康医疗助理（小诺），一位专业、温暖、值得信赖的AI健康顾问。

今天日期：{current_date}

品牌身份：
- 我是诺亚新舟（Humansa）的AI健康医疗助理
- 我的名字是小诺
- 诺亚新舟理念：以爱行舟，亲近相守
- 我们拥有500多位优秀医生，30+家专业诊所

角色职责：
1. 提供专业的医疗健康咨询服务
2. 协助用户实时预约医生、查找诊所
3. 推荐健康产品（通过健康商城小程序）
4. 解答医疗相关问题，查询检查项目
5. 提供诊所导航、体检报告解读等服务

工作原则：
1. 必须使用工具获取准确信息，不要凭记忆回答
2. 根据用户问题选择最合适的工具
3. 可以同时使用多个工具获取完整信息
4. 保持专业但友好的语气，称呼自己为"小诺"
5. 对紧急医疗情况，先建议拨打120急救电话

工具使用指南：
- 查询医生信息 → find_doctor_info
- 查看医生排班 → find_doctor_availability  
- 搜索诊所 → search_clinics
- 查询服务项目 → search_services
- 获取价格信息 → get_pricing
- 推荐保健产品 → recommend_product
- 预约服务 → book_appointment
- 创建/更新医生 → create_doctor/update_doctor
- 管理诊所 → create_clinic/update_clinic
- 网络搜索 → search_web

特别说明：
- 介绍自己时要说："我是诺亚新舟健康医疗助理小诺"
- 推荐产品时提及"健康商城小程序"
- 强调我们的服务特色：实时预约、诊所导航、体检报告解读等

请根据用户需求选择合适的工具，提供准确、有帮助的回答。"""
        
        # Create orchestrator agent
        self.orchestrator = ReActAgent.from_tools(
            tools=self.tools,
            llm=self.llm,
            verbose=True,  # Always verbose for agent flow visibility
            system_prompt=orchestrator_prompt,
            callback_manager=self.callback_manager,
            max_iterations=10
        )
        
        logger.info(f"Initialized HumansaOrchestratorAgent with {len(self.tools)} {'real database' if self.use_real_tools else 'simplified'} tools")
        
    def _create_agent_tools(self) -> List[FunctionTool]:
        """Create tools from agents for the orchestrator to use"""
        tools = []
        
        # If real tools are available, use them
        if self.use_real_tools and self.tool_manager:
            try:
                # Get real LlamaIndex tools from the tool manager
                all_tools = self.tool_manager.get_llamaindex_tools()
                
                # Use ALL tools - no token limits with GPT-4.1 (1M tokens)!
                logger.info(f"🔧 Loading ALL {len(all_tools)} tools with GPT-4.1 (1M token context)")
                logger.info("✨ No more token limits! Using full tool set for better functionality")
                return all_tools
            except Exception as e:
                logger.error(f"Failed to get real tools: {e}")
                # Fall back to simple tools
        
        # General Medical Agent Tool
        def general_medical_agent(query: str) -> str:
            """处理一般健康咨询、健康建议、日常保健等问题"""
            logger.info(f"🏥 General Medical Agent called with: {query}")
            
            # Check for greetings first
            greeting_keywords = ['你好', '您好', 'hi', 'hello', '早上好', '下午好', '晚上好']
            if any(word in query.lower() for word in greeting_keywords):
                logger.info("👋 Greeting detected")
                return """你好！我是诺亚新舟健康医疗助理（小诺），您的AI健康管家。

很高兴为您服务！我可以帮助您：
• 健康咨询与症状分析
• 预约诺亚新舟诊所的医生
• 解读体检报告
• 推荐健康产品
• 提供就医指导

有什么可以帮助您的吗？"""
            
            # Check if asking about identity
            identity_keywords = ['你是谁', '您是谁', '你叫什么', '您叫什么', '身份', 'who are you', '介绍一下你']
            if any(word in query.lower() for word in identity_keywords):
                logger.info("🤖 Identity query detected")
                # Respond in English if query is in English
                if 'who are you' in query.lower():
                    return """I am Humansa Health Medical Assistant (Xiao Nuo), your AI health companion.

Humansa (诺亚新舟) is a premium healthcare provider with the motto "Sail with Love, Stay Close Together" (以爱行舟，亲近相守). We have over 500 chief physicians from top tertiary hospitals and operate 30+ premium comprehensive clinics nationwide.

I can assist you with:
• Health consultations and symptom analysis
• Real-time appointment booking
• Medical examination arrangements
• Clinic navigation and information
• Health report interpretation

How may I help you today?"""
                else:
                    return """我是诺亚新舟健康医疗助理（小诺），您的AI健康管家。

诺亚新舟以"以爱行舟，亲近相守"为口号，拥有500多位三甲主任级名医专家，在全国开设了30+家高端综合名医诊所。

我可以为您提供以下服务：
• 健康咨询与分诊：根据症状提供初步科室/检查建议
• 实时预约：查询医生余号，协助完成预约
• 检查项目下单：对比各诊所项目，跳转商城下单
• 诊所导航：提供地址、电话、营业时间、交通指引
• 体检报告解读和慢病管理方案推荐

有什么可以帮助您的吗？"""
            
            # Check for company intro query
            if '诺亚新舟' in query and any(word in query for word in ['介绍', '什么是', '了解']):
                return """诺亚新舟（Humansa）- 以爱行舟，亲近相守

诺亚新舟是一家高端医疗健康服务机构，以名医多、级别高、专业强为特色：
• 拥有500多位三甲主任级名医专家
• 在全国开设30+家高端综合名医诊所
• 始终将客户健康放在第一位
• 为注重高品质生活的家庭提供专业医疗健康服务

您可以通过诺亚新舟医疗小程序进行实时预约，或拨打客服电话咨询最近的诊所。"""
            
            # Check for slogan query
            if '口号' in query or '理念' in query:
                return "诺亚新舟的口号是：以爱行舟，亲近相守。这体现了我们以关爱为核心，陪伴守护每一位客户健康的服务理念。"
            
            # Check for capability query
            if any(word in query for word in ['能做什么', '功能', '服务', '能力']):
                return """作为诺亚新舟健康医疗助理，我可以为您提供：

1. 健康咨询与分诊：根据症状提供初步科室/检查建议
2. 实时预约：查询医生余号，协助完成预约
3. 检查项目下单：对比各诊所项目，跳转商城下单
4. 诊所导航：提供地址、电话、营业时间、交通指引
5. 体检报告解读：帮您解读检查结果
6. 慢病管理：提供个性化健康管理方案

需要我为您提供哪方面的服务呢？"""
            
            # Check for health mall/product query
            if any(word in query for word in ['保健品', '健康商城', '购买', '产品']):
                return """关于保健品和健康产品，建议您访问诺亚新舟健康商城：

健康商城：#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl

在商城中您可以找到经过专业医生推荐的各类保健品和功能性产品。如需个性化推荐，建议您先到诺亚新舟诊所咨询医生。"""
            
            # Check for article query
            if any(word in query for word in ['文章', '资讯', '最新']):
                return """诺亚新舟最新健康文章推荐：

最新文章：https://mp.weixin.qq.com/s/q6YEtpRd_-U5tWGrRMBOtw

您也可以关注诺亚新舟公众号，获取更多健康资讯和专业医疗知识。"""
            
            # Default health consultation
            return f"关于您的健康咨询 '{query}'：建议保持良好的生活习惯，均衡饮食，适量运动。如有具体症状，请到我们的诺亚新舟诊所进行专业咨询。我们有500多位三甲主任级名医专家为您服务。"
            
        tools.append(FunctionTool.from_defaults(
            fn=general_medical_agent,
            name="general_medical_agent",
            description="处理问候（你好、Hi）、身份查询（你是谁）、公司介绍、一般健康咨询、健康建议、保健品推荐、健康文章、服务能力介绍等问题。对于打招呼、询问身份、了解公司或一般咨询，使用此工具。"
        ))
        
        # Diagnosis Agent Tool
        def diagnosis_agent(symptoms: str) -> str:
            """分析症状并提供可能的诊断建议"""
            logger.info(f"🔍 Diagnosis Agent called with symptoms: {symptoms}")
            
            # Check for common symptoms and provide more specific guidance
            if any(word in symptoms.lower() for word in ['失眠', '睡眠', '睡不着']):
                return """关于失眠问题的建议：

失眠可能由多种因素引起，包括压力、焦虑、生活习惯等。建议您：
1. 保持规律作息，每天同一时间睡觉和起床
2. 睡前避免使用电子设备，减少蓝光刺激
3. 适量运动，但避免睡前剧烈运动
4. 睡前可以尝试冥想或深呼吸放松

如果失眠持续超过2周，建议您预约诺亚新舟的神经内科或睡眠专科医生进行专业评估。"""
            
            if any(word in symptoms.lower() for word in ['发烧', '发热', '高烧']):
                return """关于发烧的处理建议：

发烧是身体的防御反应。请注意：
1. 多喝水，保持水分充足
2. 适当休息，避免过度劳累
3. 可以用温水擦拭身体帮助降温
4. 体温超过38.5°C可考虑服用退烧药

如果发烧超过3天不退，或伴有其他严重症状，请及时到诺亚新舟诊所就诊。"""
            
            return f"根据您描述的症状 '{symptoms}'：这可能需要专业医生的诊断。建议您预约我们诺亚新舟诊所的专家进行详细检查。我们有超过500位三甲主任级名医专家为您服务。"
            
        tools.append(FunctionTool.from_defaults(
            fn=diagnosis_agent,
            name="diagnosis_agent",
            description="分析症状、提供诊断建议、评估体征、建议检查项目"
        ))
        
        # Medication Agent Tool
        def medication_agent(query: str) -> str:
            """提供药物信息和用药指导"""
            logger.info(f"💊 Medication Agent called with query: {query}")
            return f"关于您的用药咨询 '{query}'：用药需要在医生指导下进行。请携带您的用药记录到诺亚新舟诊所，我们的专业医生会为您提供个性化的用药指导。"
            
        tools.append(FunctionTool.from_defaults(
            fn=medication_agent,
            name="medication_agent",
            description="提供药物信息、用药指导、药物相互作用、副作用说明"
        ))
        
        # Emergency Triage Agent Tool
        def emergency_triage_agent(situation: str) -> str:
            """评估紧急医疗情况并提供指导"""
            logger.info(f"🚨 Emergency Triage Agent called with situation: {situation}")
            # Check for emergency keywords in both Chinese and English
            emergency_keywords = ['胸痛', '呼吸困难', '昏迷', '大出血', '严重', 
                                'chest pain', 'difficulty breathing', 'severe']
            if any(keyword in situation.lower() for keyword in emergency_keywords):
                logger.warning(f"⚠️ EMERGENCY DETECTED: {situation}")
                return f"⚠️ 紧急情况：根据您描述的症状，这是紧急医疗情况！请立即拨打120急救电话，或前往最近的医院急诊科。在等待救援时，请保持冷静，尽量保持呼吸通畅。"
            return f"根据您描述的情况 '{situation}'：建议您尽快到诺亚新舟诊所就诊。如果症状加重，请立即就医。"
            
        tools.append(FunctionTool.from_defaults(
            fn=emergency_triage_agent,
            name="emergency_triage_agent",
            description="评估紧急医疗情况（胸痛、呼吸困难、昏迷等）、提供急救指导、判断是否需要拨打120。当用户描述紧急症状时必须使用此工具。"
        ))
        
        # Appointment Agent Tool
        def appointment_agent(request: str) -> str:
            """处理预约相关请求"""
            logger.info(f"📅 Appointment Agent called with request: {request}")
            
            response = """关于您的预约需求：

诺亚新舟在全国有30+家高端综合名医诊所，您可以通过以下方式预约：

1. 诺亚新舟医疗小程序：#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl
   - 实时查看医生余号
   - 在线选择时间段
   - 一键完成预约

2. 客服电话预约（工作时间）

为了帮您更好地预约，请告诉我：
- 您需要看哪个科室的医生？
- 您偏好的就诊时间？
- 您所在的城市？"""
            
            return response
            
        tools.append(FunctionTool.from_defaults(
            fn=appointment_agent,
            name="appointment_agent",
            description="处理预约服务、诊所导航、医生推荐、查询可用时间段"
        ))
        
        # Product Agent Tool  
        def product_agent(request: str) -> str:
            """推荐健康产品和保健品"""
            logger.info(f"🛍️ Product Agent called with request: {request}")
            
            # Check for specific product categories
            if any(word in request.lower() for word in ['维生素', '维他命', 'vitamin']):
                return """关于维生素补充的建议：
诺亚新舟健康商城为您推荐：

1. 诺亚新舟维生素D3软胶囊 - ¥168（原价¥198）
   - 高纯度维生素D3，每粒含2000IU
   - 增强免疫力，促进钙吸收
   - 适合成人及老年人

2. 综合维生素片 - ¥158
   - 23种维生素矿物质，科学配比
   - 补充日常营养，提高身体机能

3. 深海鱼油Omega-3胶囊 - ¥298（会员专享）
   - 保护心血管，改善记忆力

建议根据您的具体需求选择。访问健康商城查看更多：
#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl"""
            
            if any(word in request.lower() for word in ['血压计', '血糖仪', '医疗器械', '设备']):
                return """关于医疗器械的推荐：
                
1. 智能血压计 - ¥399（原价¥499）
   - 全自动臂式，APP连接，语音播报
   - 精准测量，历史记录，异常提醒
   - 适合高血压患者及家庭使用

2. 血糖仪套装 - ¥268（糖友必备）
   - 含血糖仪+100试纸+采血针
   - 快速准确，微量采血

3. 便携式制氧机 - ¥2880（呼吸守护）
   - 5L医用级，低噪音

访问健康商城了解更多医疗器械：
#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl"""
            
            if any(word in request.lower() for word in ['护肤', '美容', '面膜', '精华']):
                return """关于护肤美容产品推荐：

1. 医美修复面膜 - ¥368（术后修复）
   - 医用级无菌包装，透明质酸+胶原蛋白
   - 修复受损肌肤，补水保湿

2. 美白淡斑精华 - ¥588（明星产品）
   - 烟酰胺+维C衍生物，淡化色斑
   - 美白提亮，均匀肤色

3. 抗衰老面霜 - ¥698（贵妇首选）
   - 视黄醇+多肽复合物，深层抗皱

访问健康商城查看更多护肤产品：
#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl"""
            
            # Default product recommendation
            return """诺亚新舟健康商城为您提供：

🌟 热门推荐：
• 营养保健：维生素、鱼油、益生菌、胶原蛋白
• 医疗器械：血压计、血糖仪、制氧机、体温计
• 护肤美容：医美面膜、美白精华、抗衰产品
• 中医养生：西洋参、灵芝、燕窝、枸杞
• 母婴健康：孕妇DHA、婴儿益生菌、产后修复

🎁 当前优惠：
- 免疫力提升套餐 ¥1288（原价¥1688）
- 三高管理套餐 ¥1588（原价¥2088）
- 抗衰老美容套餐 ¥2888（原价¥3888）

访问健康商城，享受更多优惠：
#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl

温馨提示：保健品不能替代药品，请遵医嘱使用。"""
            
        tools.append(FunctionTool.from_defaults(
            fn=product_agent,
            name="product_agent",
            description="推荐健康产品、保健品、医疗器械、护肤品、营养品等。当用户询问产品购买、保健品推荐时使用此工具。"
        ))
        
        return tools
        
    async def process_query(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, str]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process query through orchestrator pattern
        Returns OpenAI-compatible response format
        """
        start_time = time.time()
        
        logger.info(f"🎭 Orchestrator processing query: {query[:100]}...")
        logger.info(f"👤 User ID: {user_id}")
        
        # Load user context from Mem0 if available
        user_context = {}
        memory_content = ""
        
        if self.memory_manager:
            try:
                logger.info("📚 Loading user context from Mem0...")
                user_context = await self.memory_manager.get_user_context(user_id)
                
                if user_context:
                    logger.info(f"📚 User context loaded: {user_context}")
                    
                    # Extract memories from recent_memories
                    if 'recent_memories' in user_context and user_context['recent_memories']:
                        memory_items = []
                        for memory in user_context['recent_memories']:
                            if 'memory' in memory:
                                memory_text = memory['memory']
                                memory_items.append(f"- {memory_text}")
                                logger.info(f"  📝 Memory: {memory_text}")
                        
                        if memory_items:
                            memory_content = "\n用户历史记忆:\n" + "\n".join(memory_items)
                            logger.info(f"✅ Loaded {len(memory_items)} memory items")
                    else:
                        logger.info("📭 No recent memories found for user")
                        
            except Exception as e:
                logger.error(f"❌ Error loading user context: {e}")
        
        # Build conversation context
        conversation_context = ""
        if messages and len(messages) > 1:
            recent_messages = messages[-6:-1] if len(messages) > 6 else messages[:-1]
            conversation_parts = []
            for msg in recent_messages:
                role = "用户" if msg['role'] == 'user' else "助手"
                conversation_parts.append(f"{role}: {msg['content']}")
            conversation_context = "\n对话历史:\n" + "\n".join(conversation_parts)
        
        # Combine query with context
        enhanced_query = query
        if memory_content or conversation_context:
            enhanced_query = f"{memory_content}{conversation_context}\n\n当前问题: {query}"
            logger.info("📝 Enhanced query with context")
        
        try:
            # Get response from orchestrator
            if stream:
                return await self._process_streaming(enhanced_query, user_id)
            else:
                # Log the query being processed
                logger.info(f"🎯 Processing query: {enhanced_query[:200]}...")
                
                response = self.orchestrator.chat(enhanced_query)
                
                # Log detailed agent flow
                if self.debug_handler:
                    # Get all events from the debug handler
                    events = self.debug_handler.get_llm_inputs_outputs()
                    logger.info(f"🔍 Agent trace: {len(events)} LLM calls")
                    
                    # Extract and log the agent's reasoning steps
                    for i, event in enumerate(events):
                        logger.info(f"\n📋 LLM Call {i+1}:")
                        
                        # Log the prompt (which includes ReAct reasoning)
                        if 'prompt' in event:
                            prompt = str(event['prompt'])
                            # Extract thought/action patterns from ReAct
                            if "Thought:" in prompt:
                                thought_start = prompt.find("Thought:")
                                thought_end = prompt.find("\n", thought_start)
                                if thought_end > thought_start:
                                    thought = prompt[thought_start:thought_end].strip()
                                    logger.info(f"  💭 {thought}")
                            
                            if "Action:" in prompt:
                                action_start = prompt.find("Action:")
                                action_end = prompt.find("\n", action_start)
                                if action_end > action_start:
                                    action = prompt[action_start:action_end].strip()
                                    logger.info(f"  🔧 {action}")
                                    
                                    # Extract tool and input
                                    if "Action Input:" in prompt:
                                        input_start = prompt.find("Action Input:")
                                        input_end = prompt.find("\n", input_start)
                                        if input_end > input_start:
                                            action_input = prompt[input_start:input_end].strip()
                                            logger.info(f"  📥 {action_input}")
                        
                        # Log the response
                        if 'completion' in event:
                            completion = str(event['completion'])[:500]
                            logger.info(f"  📤 Response: {completion}...")
                    
                    # Note: LlamaDebugHandler doesn't have reset method
                    # Events accumulate until handler is recreated
                
                # Store conversation in memory
                if self.memory_manager:
                    try:
                        await self.memory_manager.add_conversation(
                            user_id=user_id,
                            query=query,
                            response=str(response),
                            metadata={
                                "orchestrator": "v2_pattern2",
                                "processing_time": time.time() - start_time
                            }
                        )
                    except Exception as e:
                        logger.error(f"❌ Error storing conversation: {e}")
                
                # Return OpenAI-compatible format
                return self._format_openai_response(str(response), query, user_id)
                
        except Exception as e:
            logger.error(f"❌ Orchestrator error: {e}")
            import traceback
            traceback.print_exc()
            
            # Return error response in OpenAI format
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "抱歉，处理您的请求时遇到了错误。请稍后再试。"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            
    async def _process_streaming(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process streaming response with true LlamaIndex streaming showing thoughts"""
        start_time = time.time()
        chunk_id = f"chatcmpl-{int(time.time())}"
        
        logger.info(f"🎭 Orchestrator streaming query: {query[:100]}...")
        logger.info(f"👤 User ID: {user_id}")
        
        # Load user context from Mem0 if available
        user_context = {}
        memory_content = ""
        
        if self.memory_manager:
            try:
                logger.info("📚 Loading user context from Mem0...")
                user_context = await self.memory_manager.get_user_context(user_id)
                
                if user_context:
                    logger.info(f"📚 User context loaded: {user_context}")
                    
                    # Extract memories from recent_memories
                    if 'recent_memories' in user_context and user_context['recent_memories']:
                        memory_items = []
                        for memory in user_context['recent_memories']:
                            if 'memory' in memory:
                                memory_text = memory['memory']
                                memory_items.append(f"- {memory_text}")
                                logger.info(f"  📝 Memory: {memory_text}")
                        
                        if memory_items:
                            memory_content = "\n用户历史记忆:\n" + "\n".join(memory_items)
                            logger.info(f"✅ Loaded {len(memory_items)} memory items")
                    else:
                        logger.info("📭 No recent memories found for user")
                        
            except Exception as e:
                logger.error(f"❌ Error loading user context: {e}")
        
        # Build conversation context
        conversation_context = ""
        if messages and len(messages) > 1:
            recent_messages = messages[-6:-1] if len(messages) > 6 else messages[:-1]
            conversation_parts = []
            for msg in recent_messages:
                role = "用户" if msg['role'] == 'user' else "助手"
                conversation_parts.append(f"{role}: {msg['content']}")
            conversation_context = "\n对话历史:\n" + "\n".join(conversation_parts)
        
        # Combine query with context
        enhanced_query = query
        if memory_content or conversation_context:
            enhanced_query = f"{memory_content}{conversation_context}\n\n当前问题: {query}"
            logger.info("📝 Enhanced query with context")
        
        try:
            # First, stream a header to show we're processing
            yield {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": "🤔 正在思考...\n\n"
                    },
                    "finish_reason": None
                }]
            }
            
            # For streaming, we need to capture both the reasoning and the final response
            # First, let's try using chat with verbose output captured
            import io
            import sys
            from contextlib import redirect_stdout
            
            # Capture the verbose output
            captured_output = io.StringIO()
            
            # Use regular chat but capture the verbose output
            with redirect_stdout(captured_output):
                response = self.orchestrator.chat(enhanced_query)
            
            # Get the captured reasoning
            reasoning_output = captured_output.getvalue()
            
            # Parse and stream the reasoning first
            if reasoning_output:
                # Stream the reasoning process
                lines = reasoning_output.split('\n')
                for line in lines:
                    if line.strip():
                        if "Thought:" in line:
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": "gpt-4",
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": f"\n💭 **思考**: {line.split('Thought:')[-1].strip()}\n"
                                    },
                                    "finish_reason": None
                                }]
                            }
                        elif "Action:" in line:
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": "gpt-4",
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": f"🔧 **行动**: {line.split('Action:')[-1].strip()}\n"
                                    },
                                    "finish_reason": None
                                }]
                            }
                        elif "Action Input:" in line:
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": "gpt-4",
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": f"📥 **输入参数**: {line.split('Action Input:')[-1].strip()}\n"
                                    },
                                    "finish_reason": None
                                }]
                            }
                        elif "Observation:" in line:
                            yield {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": "gpt-4",
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": f"📊 **观察结果**: {line.split('Observation:')[-1].strip()}\n"
                                    },
                                    "finish_reason": None
                                }]
                            }
            
            # Stream the final response
            yield {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"\n✅ **最终回答**:\n{str(response)}\n"
                    },
                    "finish_reason": None
                }]
            }
            
            full_response = str(response)
            
            # Store conversation in memory
            if self.memory_manager:
                try:
                    await self.memory_manager.add_conversation(
                        user_id=user_id,
                        query=query,
                        response=full_response,
                        metadata={
                            "orchestrator": "v2_pattern2_streaming",
                            "processing_time": time.time() - start_time,
                            "full_reasoning": reasoning_output  # Store full reasoning separately
                        }
                    )
                except Exception as e:
                    logger.error(f"❌ Error storing conversation: {e}")
            
            # Send final chunk
            yield {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            import traceback
            traceback.print_exc()
            
            # Yield error message
            yield {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"\n\n抱歉，处理您的请求时遇到了错误：{str(e)}"
                    },
                    "finish_reason": "stop"
                }]
            }
        
    def _format_openai_response(
        self,
        content: str,
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Format response in OpenAI API format"""
        # Estimate token usage (rough approximation)
        prompt_tokens = len(query.split()) * 2
        completion_tokens = len(content.split()) * 2
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "system_fingerprint": f"humansa_v2_orchestrator_{user_id}"
        }