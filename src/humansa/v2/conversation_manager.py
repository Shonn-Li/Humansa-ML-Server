"""
Conversation Manager for HUMANSA V2
Manages conversation IDs, context windows, and conversation state
"""

import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Tracks the state of a conversation"""
    conversation_id: str
    user_id: str
    created_at: datetime
    last_updated: datetime
    turn_count: int = 0
    total_tokens: int = 0
    summary: Optional[str] = None
    key_facts: List[Dict[str, Any]] = field(default_factory=list)
    critical_info: Dict[str, Any] = field(default_factory=dict)  # Allergies, conditions, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens,
            "summary": self.summary,
            "key_facts": self.key_facts,
            "critical_info": self.critical_info
        }


class ConversationManager:
    """
    Manages conversations with intelligent context windowing and state tracking
    """
    
    def __init__(self, max_context_tokens: int = 8000, max_recent_messages: int = 6):
        self.max_context_tokens = max_context_tokens
        self.max_recent_messages = max_recent_messages
        self.conversations: Dict[str, ConversationState] = {}
        self.message_store: Dict[str, List[Dict[str, str]]] = {}
        
        # Initialize tokenizer for accurate token counting
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        except:
            logger.warning("Tiktoken not available, using approximate token counting")
            self.encoder = None
            
    def create_conversation(self, user_id: str, conversation_id: Optional[str] = None) -> str:
        """Create a new conversation with unique ID"""
        if not conversation_id:
            conversation_id = f"conv_{user_id}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
            
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.conversations[conversation_id] = state
        self.message_store[conversation_id] = []
        
        logger.info(f"Created new conversation: {conversation_id} for user: {user_id}")
        return conversation_id
        
    def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """Add a message to the conversation"""
        if conversation_id not in self.conversations:
            logger.error(f"Conversation {conversation_id} not found")
            return False
            
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tokens": self._count_tokens(content)
        }
        
        self.message_store[conversation_id].append(message)
        
        # Update conversation state
        state = self.conversations[conversation_id]
        state.last_updated = datetime.now()
        state.turn_count += 1 if role == "user" else 0
        state.total_tokens += message["tokens"]
        
        # Extract critical information if present
        self._extract_critical_info(conversation_id, content)
        
        logger.info(f"Added {role} message to conversation {conversation_id} ({message['tokens']} tokens)")
        return True
        
    def get_context_window(self, conversation_id: str, include_summary: bool = True) -> Tuple[List[Dict[str, str]], int]:
        """
        Get optimized context window for the conversation
        Returns (messages, total_tokens)
        """
        if conversation_id not in self.conversations:
            logger.error(f"Conversation {conversation_id} not found")
            return [], 0
            
        state = self.conversations[conversation_id]
        messages = self.message_store[conversation_id]
        
        if not messages:
            return [], 0
            
        context_messages = []
        total_tokens = 0
        
        # 1. Always include critical information as system message
        if state.critical_info:
            critical_msg = self._format_critical_info(state.critical_info)
            critical_tokens = self._count_tokens(critical_msg)
            context_messages.append({
                "role": "system",
                "content": f"关键信息提醒:\n{critical_msg}"
            })
            total_tokens += critical_tokens
            
        # 2. Include conversation summary if available and requested
        if include_summary and state.summary:
            summary_tokens = self._count_tokens(state.summary)
            if total_tokens + summary_tokens < self.max_context_tokens:
                context_messages.append({
                    "role": "system",
                    "content": f"对话摘要:\n{state.summary}"
                })
                total_tokens += summary_tokens
                
        # 3. Include recent messages (sliding window)
        recent_messages = messages[-self.max_recent_messages:]
        for msg in recent_messages:
            msg_tokens = msg.get("tokens", self._count_tokens(msg["content"]))
            if total_tokens + msg_tokens < self.max_context_tokens:
                context_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
                total_tokens += msg_tokens
            else:
                # Context budget exceeded, stop adding messages
                logger.warning(f"Context window limit reached for conversation {conversation_id}")
                break
                
        return context_messages, total_tokens
        
    def update_summary(self, conversation_id: str, summary: str):
        """Update conversation summary"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].summary = summary
            logger.info(f"Updated summary for conversation {conversation_id}")
            
    def add_key_fact(self, conversation_id: str, fact: Dict[str, Any]):
        """Add a key fact extracted from the conversation"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].key_facts.append({
                **fact,
                "timestamp": datetime.now().isoformat()
            })
            
    def get_conversation_state(self, conversation_id: str) -> Optional[ConversationState]:
        """Get current conversation state"""
        return self.conversations.get(conversation_id)
        
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Approximate: 1 token ≈ 4 characters for English, 2 characters for Chinese
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return (chinese_chars // 2) + (other_chars // 4)
            
    def _extract_critical_info(self, conversation_id: str, content: str):
        """Extract critical medical information from content"""
        state = self.conversations[conversation_id]
        content_lower = content.lower()
        
        # Check for allergies
        allergy_keywords = ["过敏", "allergic", "allergy", "不能吃", "不能用"]
        if any(keyword in content_lower for keyword in allergy_keywords):
            # Simple extraction - in production, use NLP
            if "过敏" in content:
                state.critical_info.setdefault("allergies", []).append({
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
                
        # Check for medical conditions
        condition_keywords = ["糖尿病", "高血压", "心脏病", "diabetes", "hypertension"]
        if any(keyword in content_lower for keyword in condition_keywords):
            state.critical_info.setdefault("conditions", []).append({
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            
        # Check for medications
        medication_keywords = ["吃药", "服用", "medication", "medicine", "药物"]
        if any(keyword in content_lower for keyword in medication_keywords):
            state.critical_info.setdefault("medications", []).append({
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            
    def _format_critical_info(self, critical_info: Dict[str, Any]) -> str:
        """Format critical information for context"""
        parts = []
        
        if "allergies" in critical_info:
            allergies = [item["content"] for item in critical_info["allergies"][-3:]]  # Last 3
            parts.append(f"过敏史: {'; '.join(allergies)}")
            
        if "conditions" in critical_info:
            conditions = [item["content"] for item in critical_info["conditions"][-3:]]
            parts.append(f"既往病史: {'; '.join(conditions)}")
            
        if "medications" in critical_info:
            medications = [item["content"] for item in critical_info["medications"][-3:]]
            parts.append(f"用药情况: {'; '.join(medications)}")
            
        return "\n".join(parts)
        
    def cleanup_old_conversations(self, max_age_hours: int = 24):
        """Remove old conversations to prevent memory bloat"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []
        
        for conv_id, state in self.conversations.items():
            if state.last_updated < cutoff:
                to_remove.append(conv_id)
                
        for conv_id in to_remove:
            del self.conversations[conv_id]
            if conv_id in self.message_store:
                del self.message_store[conv_id]
                
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old conversations")
            
    def get_conversation_history(self, conversation_id: str, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """Get raw conversation history"""
        if conversation_id not in self.message_store:
            return []
            
        messages = self.message_store[conversation_id]
        if last_n:
            return messages[-last_n:]
        return messages
        
    def merge_conversations(self, primary_id: str, secondary_id: str) -> bool:
        """Merge two conversations (useful for continuing sessions)"""
        if primary_id not in self.conversations or secondary_id not in self.conversations:
            return False
            
        # Merge messages
        if secondary_id in self.message_store:
            self.message_store[primary_id].extend(self.message_store[secondary_id])
            
        # Merge state
        primary_state = self.conversations[primary_id]
        secondary_state = self.conversations[secondary_id]
        
        primary_state.turn_count += secondary_state.turn_count
        primary_state.total_tokens += secondary_state.total_tokens
        primary_state.key_facts.extend(secondary_state.key_facts)
        
        # Merge critical info
        for key, values in secondary_state.critical_info.items():
            if key in primary_state.critical_info:
                primary_state.critical_info[key].extend(values)
            else:
                primary_state.critical_info[key] = values
                
        # Clean up secondary
        del self.conversations[secondary_id]
        if secondary_id in self.message_store:
            del self.message_store[secondary_id]
            
        logger.info(f"Merged conversation {secondary_id} into {primary_id}")
        return True