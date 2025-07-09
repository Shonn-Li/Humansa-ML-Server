"""
Intelligent Prompt Selector for Humansa AI Agent
Uses LLM to analyze user query and decide which prompt template to use (like IntelligentRouter)
"""

import json
import logging
import asyncio
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class PromptDecision:
    selected_prompt: str
    prompt_type: str
    confidence: float
    reasoning: str
    query_classification: str


class IntelligentPromptSelector:
    """
    LLM-based intelligent prompt selector that analyzes user queries
    and selects the appropriate prompt template (similar to IntelligentRouter).
    """

    def __init__(self):
        """Initialize the intelligent prompt selector."""
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Available prompt templates
        self.prompts = [
            "general_only",
            "appointment_booking",
            "product_recommendation",
            "clinic_search",
            "health_education",
            "emergency_handling"
        ]

        self.prompt_descriptions = {
            "general_only": "For general health questions, non-specific queries, or casual conversation",
            "appointment_booking": "For medical appointments, doctor booking, scheduling, or clinic visits",
            "product_recommendation": "For recommending medical products, devices, or health-related purchases",
            "clinic_search": "For finding clinics, hospitals, or medical facilities",
            "health_education": "For health knowledge, medical education, or symptom information",
            "emergency_handling": "For emergency situations, urgent medical conditions, or crisis scenarios"
        }

        logger.info("🧠 IntelligentPromptSelector initialized")

    async def select_prompt_template(self, query: str, conversation_history: Optional[List[Dict]] = None) -> PromptDecision:
        """Select the appropriate prompt template using LLM-based selection."""
        try:
            llm_decision = await self._llm_select(query, conversation_history)
            if llm_decision:
                logger.info(
                    f"🎯 LLM prompt selection successful: {llm_decision.selected_prompt}")
                return llm_decision
        except Exception as e:
            logger.warning(f"⚠️ LLM prompt selection failed: {e}")

        # Fallback to heuristic selection
        logger.info("📋 Falling back to heuristic prompt selection")
        return self._heuristic_select(query)

    async def _llm_select(self, query: str, conversation_history: Optional[List[Dict]] = None) -> Optional[PromptDecision]:
        """Use LLM to intelligently select the prompt template."""

        # Build prompt descriptions for the system prompt
        prompts_desc = "\n".join([f"{i}: {prompt} - {desc}"
                                 for i, (prompt, desc) in enumerate(self.prompt_descriptions.items())])

        system_prompt = f"""你是一个智能提示选择器，根据用户查询选择最合适的AI助手提示模板。

可用提示模板：
{prompts_desc}

选择指南：
- 模板 0 (general_only): 用于一般健康咨询、非特定查询或日常对话
- 模板 1 (appointment_booking): 用于医生预约、挂号、看诊安排或诊所访问
- 模板 2 (product_recommendation): 用于推荐医疗产品、设备或健康相关购买
- 模板 3 (clinic_search): 用于查找诊所、医院或医疗机构
- 模板 4 (health_education): 用于健康知识、医学教育或症状信息
- 模板 5 (emergency_handling): 用于紧急情况、急症医疗或危机场景

返回JSON对象，包含：
- prompt_index: 数字 (0-5)
- confidence: 浮点数 (0.0-1.0)
- reasoning: 字符串解释你的选择理由
- query_classification: 字符串描述查询类型

示例响应：
{{"prompt_index": 1, "confidence": 0.9, "reasoning": "用户想要预约医生", "query_classification": "appointment_request"}}"""

        user_prompt = f"用户查询: {query}"

        # Add conversation context if available
        if conversation_history:
            recent_context = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')[:100]}..."
                for msg in conversation_history[-3:] if msg.get('content')
            ])
            user_prompt += f"\n\n最近对话上下文:\n{recent_context}"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )

            content = response.choices[0].message.content.strip()
            logger.debug(f"🧠 LLM prompt selector response: {content}")

            # Parse JSON response
            try:
                result = json.loads(content)
                prompt_index = result.get("prompt_index")

                if prompt_index is not None and 0 <= prompt_index < len(self.prompts):
                    selected_prompt = self.prompts[prompt_index]
                    decision = self._map_prompt_to_decision(
                        selected_prompt,
                        result.get("confidence", 0.8),
                        result.get("reasoning", "LLM智能选择"),
                        result.get("query_classification", "一般查询")
                    )
                    logger.info(
                        f"✅ LLM选择提示模板 {prompt_index}: {selected_prompt}")
                    return decision
                else:
                    logger.warning(f"⚠️ LLM返回无效提示索引: {prompt_index}")

            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ 无法解析LLM响应为JSON: {e}")

        except Exception as e:
            logger.error(f"❌ LLM提示选择出错: {e}")

        return None

    def _heuristic_select(self, query: str) -> PromptDecision:
        """Fallback heuristic prompt selection based on keyword matching."""
        query_lower = query.lower()

        # Emergency keywords - highest priority
        emergency_keywords = ["急救", "紧急", "胸痛", "呼吸困难",
                              "昏迷", "emergency", "urgent", "911", "120"]
        if any(keyword in query_lower for keyword in emergency_keywords):
            return self._map_prompt_to_decision("emergency_handling", 0.9, "启发式: 紧急关键词", "emergency_query")

        # Appointment booking keywords
        appointment_keywords = ["预约", "挂号", "看诊", "就诊",
                                "book appointment", "schedule", "医生", "预定"]
        if any(keyword in query_lower for keyword in appointment_keywords):
            return self._map_prompt_to_decision("appointment_booking", 0.8, "启发式: 预约关键词", "appointment_query")

        # Product recommendation keywords
        product_keywords = ["推荐", "购买", "商品", "产品",
                            "药品", "设备", "recommend", "buy", "商城"]
        if any(keyword in query_lower for keyword in product_keywords):
            return self._map_prompt_to_decision("product_recommendation", 0.7, "启发式: 产品推荐关键词", "product_query")

        # Clinic search keywords
        clinic_keywords = ["诊所", "医院", "医疗机构",
                           "clinic", "hospital", "找医院", "医疗中心"]
        if any(keyword in query_lower for keyword in clinic_keywords):
            return self._map_prompt_to_decision("clinic_search", 0.7, "启发式: 诊所搜索关键词", "clinic_query")

        # Health education keywords
        education_keywords = ["什么是", "如何", "怎么",
                              "科普", "知识", "症状", "疾病", "health", "病因"]
        if any(keyword in query_lower for keyword in education_keywords):
            return self._map_prompt_to_decision("health_education", 0.7, "启发式: 健康教育关键词", "education_query")

        # Default to general only
        return self._map_prompt_to_decision("general_only", 0.6, "启发式: 默认一般查询", "general_query")

    def _map_prompt_to_decision(self, prompt_name: str, confidence: float, reasoning: str, classification: str) -> PromptDecision:
        """Map prompt name to PromptDecision with correct prompt_type."""

        # Map prompt names to types
        prompt_type_mapping = {
            "general_only": "general",
            "appointment_booking": "booking",
            "product_recommendation": "product",
            "clinic_search": "search",
            "health_education": "education",
            "emergency_handling": "emergency"
        }

        prompt_type = prompt_type_mapping.get(prompt_name, "general")

        return PromptDecision(
            selected_prompt=prompt_name,
            prompt_type=prompt_type,
            confidence=confidence,
            reasoning=reasoning,
            query_classification=classification
        )

    def get_available_prompts(self) -> List[str]:
        """Return list of available prompt templates."""
        return self.prompts.copy()

    def get_prompt_description(self, prompt_name: str) -> Optional[str]:
        """Get description for a specific prompt template."""
        return self.prompt_descriptions.get(prompt_name)


# Global instance
intelligent_prompt_selector = IntelligentPromptSelector()
