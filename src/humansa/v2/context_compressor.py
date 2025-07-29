"""
Context Compressor for HUMANSA V2
Intelligently compresses conversation history while preserving critical information
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import json

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    Compresses conversation context using LLM summarization while preserving critical medical information
    """
    
    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm
        self.compression_prompts = {
            "medical_summary": """请总结以下医疗对话的关键信息。重点保留：
1. 患者基本信息（姓名、年龄、联系方式）
2. 主诉症状和持续时间
3. 既往病史和过敏史
4. 当前用药情况
5. 已做出的诊断或建议
6. 预约信息或待办事项

对话内容：
{conversation}

请用简洁的要点形式总结（不超过200字）：""",
            
            "general_summary": """请简要总结以下对话的主要内容和结论：
{conversation}

总结（不超过150字）：""",
            
            "appointment_summary": """请总结预约相关信息：
{conversation}

包括：医生姓名、时间、地点、患者信息、预约状态：""",
            
            "key_facts": """从以下对话中提取关键事实：
{conversation}

请列出最重要的3-5个事实："""
        }
        
    async def compress_conversation(
        self,
        messages: List[Dict[str, str]],
        compression_type: str = "medical_summary",
        preserve_last_n: int = 3
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Compress conversation history
        Returns (summary, preserved_recent_messages)
        """
        if len(messages) <= preserve_last_n:
            # Too short to compress
            return "", messages
            
        # Split messages
        to_compress = messages[:-preserve_last_n]
        to_preserve = messages[-preserve_last_n:]
        
        # Format conversation for compression
        conversation_text = self._format_messages_for_compression(to_compress)
        
        # Generate summary using LLM
        summary = await self._generate_summary(conversation_text, compression_type)
        
        logger.info(f"Compressed {len(to_compress)} messages into summary of {len(summary)} characters")
        
        return summary, to_preserve
        
    async def progressive_compression(
        self,
        messages: List[Dict[str, str]],
        token_budget: int = 4000
    ) -> List[Dict[str, str]]:
        """
        Progressively compress messages to fit within token budget
        """
        compressed_messages = []
        current_tokens = 0
        
        # Group messages by topic/time segments
        segments = self._segment_messages(messages)
        
        for i, segment in enumerate(segments):
            segment_tokens = self._estimate_tokens(segment)
            
            if current_tokens + segment_tokens > token_budget:
                # Compress this segment
                if i < len(segments) - 1:  # Don't compress the most recent segment
                    summary, _ = await self.compress_conversation(
                        segment,
                        compression_type="general_summary",
                        preserve_last_n=0
                    )
                    compressed_messages.append({
                        "role": "system",
                        "content": f"[对话段落{i+1}摘要] {summary}"
                    })
                    current_tokens += self._estimate_tokens([{"content": summary}])
                else:
                    # For the most recent segment, include as many messages as possible
                    for msg in segment:
                        msg_tokens = self._estimate_tokens([msg])
                        if current_tokens + msg_tokens <= token_budget:
                            compressed_messages.append(msg)
                            current_tokens += msg_tokens
                        else:
                            break
            else:
                # Include segment as-is
                compressed_messages.extend(segment)
                current_tokens += segment_tokens
                
        return compressed_messages
        
    async def extract_key_information(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract structured key information from conversation
        """
        conversation_text = self._format_messages_for_compression(messages)
        
        extraction_prompt = f"""从以下对话中提取结构化信息：
{conversation_text}

请以JSON格式返回以下信息（如果没有相关信息，该字段为null）：
{{
    "patient_name": "患者姓名",
    "age": "年龄",
    "phone": "电话",
    "chief_complaint": "主诉",
    "symptoms": ["症状1", "症状2"],
    "allergies": ["过敏1", "过敏2"],
    "medications": ["药物1", "药物2"],
    "medical_history": ["既往病史1", "既往病史2"],
    "appointment_info": {{
        "doctor": "医生姓名",
        "date": "日期",
        "time": "时间",
        "status": "状态"
    }},
    "recommendations": ["建议1", "建议2"]
}}"""
        
        if self.llm:
            try:
                response = await self._llm_complete(extraction_prompt)
                # Parse JSON response
                extracted = json.loads(response)
                return extracted
            except Exception as e:
                logger.error(f"Failed to extract key information: {e}")
                return {}
        else:
            # Fallback to rule-based extraction
            return self._rule_based_extraction(messages)
            
    def _format_messages_for_compression(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into conversation text"""
        conversation_parts = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            conversation_parts.append(f"{role}: {msg['content']}")
        return "\n".join(conversation_parts)
        
    async def _generate_summary(self, conversation_text: str, compression_type: str) -> str:
        """Generate summary using LLM"""
        if compression_type not in self.compression_prompts:
            compression_type = "general_summary"
            
        prompt = self.compression_prompts[compression_type].format(conversation=conversation_text)
        
        if self.llm:
            try:
                summary = await self._llm_complete(prompt)
                return summary.strip()
            except Exception as e:
                logger.error(f"LLM summarization failed: {e}")
                return self._fallback_summary(conversation_text)
        else:
            return self._fallback_summary(conversation_text)
            
    async def _llm_complete(self, prompt: str) -> str:
        """Complete prompt using LLM"""
        if hasattr(self.llm, 'acomplete'):
            # Async completion
            response = await self.llm.acomplete(prompt)
            return response.text
        elif hasattr(self.llm, 'complete'):
            # Sync completion wrapped in async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.llm.complete, prompt)
            return response.text
        else:
            raise ValueError("LLM does not have complete method")
            
    def _fallback_summary(self, conversation_text: str) -> str:
        """Simple rule-based summary when LLM is not available"""
        lines = conversation_text.split('\n')
        if len(lines) > 5:
            return f"对话包含{len(lines)}轮交流，讨论了医疗相关问题。"
        else:
            return "简短的医疗咨询对话。"
            
    def _segment_messages(self, messages: List[Dict[str, str]], segment_size: int = 10) -> List[List[Dict[str, str]]]:
        """Segment messages into logical groups"""
        segments = []
        current_segment = []
        
        for i, msg in enumerate(messages):
            current_segment.append(msg)
            
            # Create new segment every N messages or at topic changes
            if len(current_segment) >= segment_size or self._is_topic_change(messages, i):
                segments.append(current_segment)
                current_segment = []
                
        if current_segment:
            segments.append(current_segment)
            
        return segments
        
    def _is_topic_change(self, messages: List[Dict[str, str]], index: int) -> bool:
        """Detect if there's a topic change at this index"""
        if index >= len(messages) - 1:
            return False
            
        current_content = messages[index]["content"].lower()
        next_content = messages[index + 1]["content"].lower()
        
        # Simple heuristic - check for topic keywords
        topic_keywords = [
            ("预约", "产品"),
            ("医生", "购买"),
            ("症状", "价格"),
            ("挂号", "保健品")
        ]
        
        for kw1, kw2 in topic_keywords:
            if kw1 in current_content and kw2 in next_content:
                return True
            if kw2 in current_content and kw1 in next_content:
                return True
                
        return False
        
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        # Rough estimate: 2 chars per token for Chinese
        return total_chars // 2
        
    def _rule_based_extraction(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fallback rule-based information extraction"""
        extracted = {
            "patient_name": None,
            "phone": None,
            "symptoms": [],
            "allergies": [],
            "appointment_info": {}
        }
        
        for msg in messages:
            content = msg["content"]
            
            # Extract phone numbers
            import re
            phone_match = re.search(r'1[3-9]\d{9}', content)
            if phone_match:
                extracted["phone"] = phone_match.group()
                
            # Extract symptoms
            if "疼" in content or "痛" in content or "不舒服" in content:
                extracted["symptoms"].append(content[:50])
                
            # Extract allergies
            if "过敏" in content:
                extracted["allergies"].append(content[:50])
                
        return extracted
        
    def calculate_compression_ratio(self, original: List[Dict[str, str]], compressed: str) -> float:
        """Calculate compression ratio"""
        original_chars = sum(len(msg.get("content", "")) for msg in original)
        compressed_chars = len(compressed)
        
        if original_chars == 0:
            return 0.0
            
        return 1.0 - (compressed_chars / original_chars)