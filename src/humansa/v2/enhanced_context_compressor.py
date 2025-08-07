"""
Enhanced Context Compressor for HUMANSA V2 with Response Chain Support
Intelligently compresses conversation history while preserving critical information
and maintaining response chain relationships
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import asyncio
import json
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationSegment:
    """Represents a segment of conversation for compression"""
    start_idx: int
    end_idx: int
    messages: List[Dict[str, str]]
    importance_score: float
    topics: Set[str]
    has_critical_info: bool
    response_ids: List[str]


class EnhancedContextCompressor:
    """
    Enhanced compressor that understands response chains and conversation structure
    """
    
    def __init__(self, llm: Optional[Any] = None, response_manager: Optional[Any] = None):
        self.llm = llm
        self.response_manager = response_manager
        
        # Enhanced compression prompts
        self.compression_prompts = {
            "medical_chain_summary": """请总结以下医疗对话链的关键信息，保持时间顺序和决策流程。

重点保留：
1. 患者信息变化（症状发展、新信息披露）
2. 医疗决策点（诊断、治疗建议）
3. 预约和行动项
4. 关键医疗信息（过敏、用药、病史）
5. 对话分支点和选择

对话链：
{conversation_chain}

请按时间顺序总结，标注重要决策点（200字以内）：""",

            "fork_aware_summary": """这是一个有分支的对话。请分别总结每个分支的内容。

主干对话：
{main_branch}

分支点：{fork_point}

分支A：
{branch_a}

分支B：
{branch_b}

请总结主干和各分支的关键差异：""",

            "topic_transition_summary": """请总结以下对话中的话题转换和信息流。

对话内容：
{conversation}

识别的话题：{topics}

请按话题总结关键信息，标注转换点：""",

            "critical_extraction": """从对话中提取必须永久保留的关键医疗信息。

对话：
{conversation}

请提取：
1. 患者标识信息
2. 过敏和禁忌
3. 慢性病和用药
4. 已确认的诊断
5. 已预约的信息

返回JSON格式："""
        }
        
        # Topic keywords for intelligent segmentation
        self.topic_keywords = {
            "症状描述": ["疼", "痛", "不舒服", "症状", "感觉"],
            "医疗史": ["病史", "以前", "曾经", "过敏", "用药"],
            "预约": ["预约", "挂号", "时间", "医生", "号"],
            "产品": ["产品", "保健品", "推荐", "购买"],
            "诊断建议": ["建议", "需要", "检查", "治疗"],
            "紧急情况": ["紧急", "急", "立即", "马上"]
        }
    
    async def compress_response_chain(
        self,
        response_chain: List[Any],
        preserve_last_n: int = 5,
        target_tokens: int = 4000
    ) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """
        Compress a response chain while maintaining relationships
        Returns: (summary, preserved_messages, metadata)
        """
        if len(response_chain) <= preserve_last_n:
            return "", self._extract_messages_from_chain(response_chain), {}
        
        # Segment the conversation
        segments = self._segment_response_chain(response_chain)
        
        # Score segments by importance
        scored_segments = self._score_segments(segments)
        
        # Compress segments based on importance and token budget
        compressed_summary = await self._compress_segments(
            scored_segments,
            target_tokens,
            preserve_last_n
        )
        
        # Extract preserved messages
        preserved_messages = self._extract_messages_from_chain(
            response_chain[-preserve_last_n:]
        )
        
        # Extract metadata
        metadata = {
            "total_responses": len(response_chain),
            "compressed_segments": len(scored_segments) - 1,  # Excluding preserved
            "compression_ratio": self._calculate_compression_ratio(
                response_chain[:-preserve_last_n],
                compressed_summary
            ),
            "topics_covered": self._extract_all_topics(segments),
            "has_forks": self._detect_forks(response_chain)
        }
        
        return compressed_summary, preserved_messages, metadata
    
    def _segment_response_chain(self, response_chain: List[Any]) -> List[ConversationSegment]:
        """Segment response chain into logical groups"""
        segments = []
        current_segment_messages = []
        current_topics = set()
        current_response_ids = []
        start_idx = 0
        
        for i, response in enumerate(response_chain):
            # Extract message content
            messages = [
                {"role": "user", "content": response.input},
                {"role": "assistant", "content": self._extract_response_text(response)}
            ]
            current_segment_messages.extend(messages)
            current_response_ids.append(response.id)
            
            # Detect topics
            topics = self._detect_topics(response.input + " " + self._extract_response_text(response))
            current_topics.update(topics)
            
            # Check if we should create a new segment
            should_segment = (
                len(current_segment_messages) >= 10 or  # Size limit
                i == len(response_chain) - 1 or  # Last response
                self._is_major_topic_change(current_topics, topics) or  # Topic change
                self._is_fork_point(response, response_chain, i)  # Fork point
            )
            
            if should_segment:
                has_critical = self._has_critical_info(current_segment_messages)
                importance = self._calculate_importance(
                    current_segment_messages,
                    current_topics,
                    has_critical
                )
                
                segments.append(ConversationSegment(
                    start_idx=start_idx,
                    end_idx=i,
                    messages=current_segment_messages.copy(),
                    importance_score=importance,
                    topics=current_topics.copy(),
                    has_critical_info=has_critical,
                    response_ids=current_response_ids.copy()
                ))
                
                # Reset for next segment
                current_segment_messages = []
                current_topics = set()
                current_response_ids = []
                start_idx = i + 1
        
        return segments
    
    def _score_segments(self, segments: List[ConversationSegment]) -> List[ConversationSegment]:
        """Score segments by importance for compression priority"""
        # Adjust scores based on position and content
        for i, segment in enumerate(segments):
            # Recency bonus (more recent = higher score)
            recency_bonus = (i / len(segments)) * 0.3
            segment.importance_score += recency_bonus
            
            # Critical info bonus
            if segment.has_critical_info:
                segment.importance_score += 0.5
            
            # Topic diversity bonus
            topic_bonus = min(len(segment.topics) * 0.1, 0.3)
            segment.importance_score += topic_bonus
        
        return sorted(segments, key=lambda s: s.importance_score, reverse=True)
    
    async def _compress_segments(
        self,
        segments: List[ConversationSegment],
        target_tokens: int,
        preserve_last_n: int
    ) -> str:
        """Compress segments intelligently based on importance"""
        compressed_parts = []
        current_tokens = 0
        
        # Always preserve the most important segments
        for segment in segments:
            # Skip if this is in the preserved range
            if segment.end_idx >= len(segments) - preserve_last_n:
                continue
            
            # Determine compression level based on importance
            if segment.importance_score > 0.8:
                # High importance: detailed summary
                summary = await self._generate_detailed_summary(segment)
            elif segment.importance_score > 0.5:
                # Medium importance: standard summary
                summary = await self._generate_standard_summary(segment)
            else:
                # Low importance: brief summary
                summary = await self._generate_brief_summary(segment)
            
            summary_tokens = self._estimate_tokens(summary)
            
            if current_tokens + summary_tokens <= target_tokens:
                compressed_parts.append(summary)
                current_tokens += summary_tokens
            else:
                # Token budget exceeded, only add if critical
                if segment.has_critical_info:
                    # Extract only critical info
                    critical_summary = await self._extract_critical_only(segment)
                    compressed_parts.append(critical_summary)
                break
        
        # Combine summaries with proper formatting
        return self._format_compressed_summary(compressed_parts)
    
    async def _generate_detailed_summary(self, segment: ConversationSegment) -> str:
        """Generate detailed summary for high-importance segments"""
        conversation_text = self._format_messages_for_compression(segment.messages)
        
        prompt = f"""详细总结以下重要对话段落，保留所有关键决策和医疗信息：

话题：{', '.join(segment.topics)}
对话：
{conversation_text}

详细总结（100字以内）："""
        
        if self.llm:
            try:
                response = await self._llm_complete(prompt)
                return f"[重要] {response.strip()}"
            except Exception as e:
                logger.error(f"Failed to generate detailed summary: {e}")
        
        return f"[重要] 讨论了{', '.join(segment.topics)}相关内容"
    
    async def _generate_standard_summary(self, segment: ConversationSegment) -> str:
        """Generate standard summary for medium-importance segments"""
        conversation_text = self._format_messages_for_compression(segment.messages)
        topics_str = ', '.join(segment.topics)
        
        if self.llm:
            try:
                prompt = self.compression_prompts["topic_transition_summary"].format(
                    conversation=conversation_text,
                    topics=topics_str
                )
                response = await self._llm_complete(prompt)
                return response.strip()
            except Exception as e:
                logger.error(f"Failed to generate standard summary: {e}")
        
        return f"讨论了{topics_str}"
    
    async def _generate_brief_summary(self, segment: ConversationSegment) -> str:
        """Generate brief summary for low-importance segments"""
        topics = ', '.join(segment.topics) if segment.topics else "一般对话"
        return f"简要讨论：{topics}"
    
    async def _extract_critical_only(self, segment: ConversationSegment) -> str:
        """Extract only critical information from segment"""
        conversation_text = self._format_messages_for_compression(segment.messages)
        
        if self.llm:
            try:
                prompt = self.compression_prompts["critical_extraction"].format(
                    conversation=conversation_text
                )
                response = await self._llm_complete(prompt)
                return f"[关键信息] {response.strip()}"
            except Exception as e:
                logger.error(f"Failed to extract critical info: {e}")
        
        # Fallback extraction
        critical_info = []
        for msg in segment.messages:
            content = msg.get("content", "").lower()
            if any(keyword in content for keyword in ["过敏", "禁忌", "慢性", "预约"]):
                critical_info.append(msg["content"][:50])
        
        return f"[关键信息] {'; '.join(critical_info)}" if critical_info else ""
    
    def _detect_topics(self, text: str) -> Set[str]:
        """Detect topics in text"""
        text_lower = text.lower()
        detected_topics = set()
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_topics.add(topic)
        
        return detected_topics
    
    def _is_major_topic_change(self, current_topics: Set[str], new_topics: Set[str]) -> bool:
        """Check if there's a major topic change"""
        if not current_topics:
            return False
        
        # Major change if no overlap and both have topics
        if current_topics and new_topics and not current_topics.intersection(new_topics):
            return True
        
        # Major change if switching between medical and non-medical
        medical_topics = {"症状描述", "医疗史", "诊断建议", "紧急情况"}
        current_medical = bool(current_topics.intersection(medical_topics))
        new_medical = bool(new_topics.intersection(medical_topics))
        
        return current_medical != new_medical
    
    def _is_fork_point(self, response: Any, chain: List[Any], index: int) -> bool:
        """Check if this response is a fork point"""
        if not self.response_manager or index >= len(chain) - 1:
            return False
        
        # Check if multiple responses have the same previous_response_id
        current_id = response.id
        fork_count = sum(
            1 for r in chain[index + 1:]
            if hasattr(r, 'previous_response_id') and r.previous_response_id == current_id
        )
        
        return fork_count > 1
    
    def _has_critical_info(self, messages: List[Dict[str, str]]) -> bool:
        """Check if messages contain critical medical information"""
        critical_keywords = [
            "过敏", "禁忌", "慢性病", "糖尿病", "高血压", "心脏病",
            "预约成功", "预约号", "用药", "诊断"
        ]
        
        for msg in messages:
            content = msg.get("content", "").lower()
            if any(keyword in content for keyword in critical_keywords):
                return True
        
        return False
    
    def _calculate_importance(
        self,
        messages: List[Dict[str, str]],
        topics: Set[str],
        has_critical: bool
    ) -> float:
        """Calculate importance score for a segment"""
        score = 0.0
        
        # Base score from message count
        score += min(len(messages) / 20, 0.3)
        
        # Topic importance
        important_topics = {"症状描述", "诊断建议", "预约", "紧急情况"}
        if topics.intersection(important_topics):
            score += 0.3
        
        # Critical info bonus
        if has_critical:
            score += 0.4
        
        # Question-answer pairs bonus
        qa_pairs = sum(
            1 for i in range(0, len(messages) - 1, 2)
            if messages[i].get("role") == "user" and "？" in messages[i].get("content", "")
        )
        score += min(qa_pairs * 0.1, 0.3)
        
        return min(score, 1.0)
    
    def _extract_messages_from_chain(self, response_chain: List[Any]) -> List[Dict[str, str]]:
        """Extract messages from response chain"""
        messages = []
        for response in response_chain:
            messages.append({
                "role": "user",
                "content": response.input,
                "response_id": response.id
            })
            messages.append({
                "role": "assistant",
                "content": self._extract_response_text(response),
                "response_id": response.id
            })
        return messages
    
    def _extract_response_text(self, response: Any) -> str:
        """Extract text from response object"""
        if hasattr(response, 'output'):
            output_text = []
            for item in response.output:
                if isinstance(item, dict) and item.get("type") == "text":
                    output_text.append(item.get("text", ""))
            return " ".join(output_text)
        return str(response)
    
    def _detect_forks(self, response_chain: List[Any]) -> bool:
        """Detect if the response chain has forks"""
        if not self.response_manager:
            return False
        
        response_ids = [r.id for r in response_chain]
        for resp_id in response_ids:
            if resp_id in self.response_manager.response_tree:
                if len(self.response_manager.response_tree[resp_id]) > 1:
                    return True
        return False
    
    def _extract_all_topics(self, segments: List[ConversationSegment]) -> List[str]:
        """Extract all unique topics from segments"""
        all_topics = set()
        for segment in segments:
            all_topics.update(segment.topics)
        return sorted(list(all_topics))
    
    def _format_compressed_summary(self, parts: List[str]) -> str:
        """Format compressed summary parts into cohesive summary"""
        if not parts:
            return "对话摘要：一般性咨询对话。"
        
        # Remove empty parts
        parts = [p for p in parts if p.strip()]
        
        # Add temporal markers if multiple parts
        if len(parts) > 1:
            formatted_parts = []
            for i, part in enumerate(parts):
                if i == 0:
                    formatted_parts.append(f"开始阶段：{part}")
                elif i == len(parts) - 1:
                    formatted_parts.append(f"最近讨论：{part}")
                else:
                    formatted_parts.append(f"中间阶段：{part}")
            return "\n".join(formatted_parts)
        else:
            return parts[0]
    
    def _format_messages_for_compression(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for compression"""
        parts = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            parts.append(f"{role}: {msg['content']}")
        return "\n".join(parts)
    
    async def _llm_complete(self, prompt: str) -> str:
        """Complete prompt using LLM"""
        if hasattr(self.llm, 'acomplete'):
            response = await self.llm.acomplete(prompt)
            return response.text
        elif hasattr(self.llm, 'complete'):
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.llm.complete, prompt)
            return response.text
        else:
            raise ValueError("LLM does not have complete method")
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return (chinese_chars // 2) + (other_chars // 4)
    
    def _calculate_compression_ratio(self, original_chain: List[Any], compressed: str) -> float:
        """Calculate compression ratio"""
        original_text = ""
        for response in original_chain:
            original_text += response.input + " " + self._extract_response_text(response)
        
        original_tokens = self._estimate_tokens(original_text)
        compressed_tokens = self._estimate_tokens(compressed)
        
        if original_tokens == 0:
            return 0.0
        
        return 1.0 - (compressed_tokens / original_tokens)
    
    async def generate_fork_aware_summary(
        self,
        main_branch: List[Any],
        fork_point_response: Any,
        branches: List[List[Any]]
    ) -> str:
        """Generate summary that acknowledges conversation forks"""
        if not self.llm or len(branches) < 2:
            return await self._generate_standard_summary(main_branch)
        
        # Format main branch
        main_text = self._format_messages_for_compression(
            self._extract_messages_from_chain(main_branch)
        )
        
        # Format branches
        branch_texts = []
        for branch in branches[:2]:  # Limit to 2 branches for summary
            branch_text = self._format_messages_for_compression(
                self._extract_messages_from_chain(branch)
            )
            branch_texts.append(branch_text)
        
        prompt = self.compression_prompts["fork_aware_summary"].format(
            main_branch=main_text,
            fork_point=f"用户：{fork_point_response.input}",
            branch_a=branch_texts[0] if len(branch_texts) > 0 else "无",
            branch_b=branch_texts[1] if len(branch_texts) > 1 else "无"
        )
        
        try:
            response = await self._llm_complete(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate fork-aware summary: {e}")
            return "对话包含多个分支选择。"