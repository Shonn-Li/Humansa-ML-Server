"""
Intelligent Router - Query-based source selection (CORRECT IMPLEMENTATION)

This module analyzes user queries and decides which context sources to enable/disable
within the constraints set by the client. It does NOT retrieve anything itself.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    """Result of router decision - which sources to enable/disable"""
    final_flags: Dict[str, bool]  # Final enable_* flags after router decision
    reasoning: str
    confidence: float
    changes_made: List[str]  # What the router changed


class IntelligentRouter:
    """
    CORRECT Router Implementation:
    - Analyzes queries with LLM
    - Decides which sources are needed
    - Modifies enable_* flags within client constraints
    - Does NOT retrieve anything itself
    """

    def __init__(self, provider_selector=None):
        self.provider_selector = provider_selector
        self.router_llm = None
        self._setup_router_llm()

    def _setup_router_llm(self):
        """Get OpenAI-compatible LLM for query analysis"""
        if self.provider_selector:
            self.router_llm = self.provider_selector.get_router_compatible_llm()
            if self.router_llm:
                logger.info("🎯 Router initialized with OpenAI-compatible LLM")
            else:
                logger.warning("⚠️ No router-compatible LLM available")
        else:
            logger.warning("⚠️ No provider selector provided to router")

    def make_routing_decision(self, query: str, client_flags: Dict[str, bool]) -> RouterDecision:
        """
        MAIN ROUTER FUNCTION:
        Analyze query and decide which sources to enable within client constraints
        
        Args:
            query: User's question/message  
            client_flags: Original enable_* flags from client
            
        Returns:
            RouterDecision with final flags and reasoning
        """
        
        # Start with client flags as baseline
        final_flags = client_flags.copy()
        changes_made = []
        
        try:
            # Use LLM to analyze query (if available)
            if self.router_llm:
                decision = self._llm_based_routing(query, client_flags)
            else:
                decision = self._heuristic_routing(query, client_flags)
                
            return decision
            
        except Exception as e:
            logger.error(f"Router decision failed: {e}")
            # Fallback: return original flags unchanged
            return RouterDecision(
                final_flags=client_flags,
                reasoning=f"Router failed, using original flags: {e}",
                confidence=0.0,
                changes_made=[]
            )

    def _llm_based_routing(self, query: str, client_flags: Dict[str, bool]) -> RouterDecision:
        """Use LLM to make intelligent routing decisions"""
        
        if not self.router_llm:
            logger.warning("No LLM available for routing, falling back to heuristics")
            return self._heuristic_routing(query, client_flags)
        
        try:
            # Create the routing prompt
            routing_prompt = self._create_routing_prompt(query, client_flags)
            
            # Get LLM decision
            response = self.router_llm.complete(routing_prompt)
            decision_text = response.text.strip()
            
            # Parse LLM response
            return self._parse_llm_routing_response(decision_text, client_flags, query)
            
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            # Fallback to heuristics if LLM fails
            return self._heuristic_routing(query, client_flags)

    def _create_routing_prompt(self, query: str, client_flags: Dict[str, bool]) -> str:
        """Create the routing prompt for the LLM"""
        
        prompt = f"""You are an intelligent routing system for a chat application. Your job is to analyze a user's query and decide which context sources should be enabled or disabled to provide the best response.

Available context sources:
- RAG (Retrieval Augmented Generation): Personal notes, conversations, user's saved content
- Web Search: Current information from the internet, news, latest developments
- Citations: Whether to include source citations in the response

Current client settings:
- enable_rag: {client_flags.get('enable_rag', False)}
- enable_web_search: {client_flags.get('enable_web_search', False)}
- enable_citations: {client_flags.get('enable_citations', False)}

IMPORTANT CONSTRAINTS:
- You can only DISABLE sources that are currently enabled
- You CANNOT enable sources that the client has disabled
- If a source is disabled by client, it must stay disabled

User Query: "{query}"

Analyze this query and decide which sources should be enabled/disabled. Consider:
1. Simple greetings/conversations → Disable web search and citations
2. Personal/historical questions → Keep RAG enabled
3. Current events/latest info → Keep web search enabled  
4. Technical questions needing sources → Keep citations enabled

Respond in this exact JSON format:
{{
    "enable_rag": true/false,
    "enable_web_search": true/false,
    "enable_citations": true/false,
    "reasoning": "Brief explanation of your decision",
    "confidence": 0.0-1.0
}}"""

        return prompt

    def _parse_llm_routing_response(self, response_text: str, original_flags: Dict[str, bool], query: str) -> RouterDecision:
        """Parse the LLM's routing decision response"""
        
        try:
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                decision_data = json.loads(json_str)
            else:
                # Fallback if no JSON found
                raise ValueError("No JSON found in LLM response")
            
            # Extract decision data
            final_flags = {}
            changes_made = []
            
            # Process each flag, respecting client constraints
            for flag_name in ['enable_rag', 'enable_web_search', 'enable_citations']:
                original_value = original_flags.get(flag_name, False)
                llm_value = decision_data.get(flag_name, original_value)
                
                # Constraint: Cannot enable what client disabled
                if not original_value and llm_value:
                    final_flags[flag_name] = False  # Keep disabled
                else:
                    final_flags[flag_name] = llm_value
                    
                # Track changes
                if original_value != final_flags[flag_name]:
                    action = "Enabled" if final_flags[flag_name] else "Disabled"
                    changes_made.append(f"{action} {flag_name.replace('enable_', '')}")
            
            reasoning = decision_data.get('reasoning', 'LLM routing decision')
            confidence = float(decision_data.get('confidence', 0.8))
            
            return RouterDecision(
                final_flags=final_flags,
                reasoning=f"LLM Decision: {reasoning}",
                confidence=confidence,
                changes_made=changes_made
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LLM routing response: {e}")
            logger.debug(f"Raw LLM response: {response_text}")
            
            # Fallback to heuristic if parsing fails
            return self._heuristic_routing(query, original_flags)

    def _heuristic_routing(self, query: str, client_flags: Dict[str, bool]) -> RouterDecision:
        """
        Heuristic-based routing decisions
        """
        final_flags = client_flags.copy()
        changes_made = []
        reasoning_parts = []
        
        query_lower = query.lower().strip()
        
        # 1. SIMPLE GREETINGS/CONVERSATIONAL - Disable everything  
        simple_patterns = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'thanks', 'thank you', 'ok', 'okay', 'yes', 'no', 'sure',
            'what are you talking about', 'i dont understand', "i don't understand"
        ]
        
        # Check if it's a simple greeting (exact matches to avoid false positives)
        is_simple = (any(query_lower.startswith(pattern) for pattern in simple_patterns) or 
                    any(query_lower == pattern for pattern in simple_patterns) or 
                    len(query_lower.strip()) < 10)
        
        if is_simple:
            # Disable web search for simple conversational messages
            if final_flags.get('enable_web_search', False):
                final_flags['enable_web_search'] = False
                changes_made.append('Disabled web search')
                reasoning_parts.append('simple conversational message detected')
            
            # Disable citations for simple messages
            if final_flags.get('enable_citations', False):
                final_flags['enable_citations'] = False
                changes_made.append('Disabled citations')
                reasoning_parts.append('citations not needed for simple conversation')

        # 2. PERSONAL/NOTE KEYWORDS - Keep/Enable RAG (be more specific to avoid false positives)
        personal_keywords = [' my ', ' i ', ' me ', 'remember', 'note', 'conversation', 'we discussed', 'you said', 'our ', 'last time']
        has_personal = any(keyword in f" {query_lower} " for keyword in personal_keywords)
        
        if has_personal and not is_simple:
            reasoning_parts.append('personal keywords detected')
            # RAG is handled by whether it's enabled by client
            
        # 3. FILE/ATTACHMENT KEYWORDS - Keep attachments enabled
        file_keywords = ['file', 'document', 'pdf', 'attachment', 'image', 'uploaded']
        has_file_ref = any(keyword in query_lower for keyword in file_keywords)
        
        if has_file_ref:
            reasoning_parts.append('file reference detected')
            
        # 4. GENERAL KNOWLEDGE - Keep web search if it's complex
        knowledge_keywords = ['what is', 'who is', 'when did', 'how to', 'latest', 'recent', 'current']
        needs_external = any(keyword in query_lower for keyword in knowledge_keywords)
        
        if needs_external and not any(pattern in query_lower for pattern in simple_patterns):
            reasoning_parts.append('external knowledge needed')
            # Keep web search enabled if client allowed it
        else:
            # For non-knowledge queries, we might want to disable web search
            if not has_personal and not has_file_ref and final_flags.get('enable_web_search', False):
                final_flags['enable_web_search'] = False
                changes_made.append('Disabled web search')
                reasoning_parts.append('no external knowledge needed')

        # Build reasoning
        if reasoning_parts:
            reasoning = f"Router analysis: {', '.join(reasoning_parts)}"
        else:
            reasoning = "No specific patterns detected, keeping original settings"
            
        if changes_made:
            reasoning += f" → Changes: {', '.join(changes_made)}"

        return RouterDecision(
            final_flags=final_flags,
            reasoning=reasoning,
            confidence=0.8,
            changes_made=changes_made
        )

    def get_status(self) -> Dict[str, Any]:
        """Get router status"""
        return {
            "router_llm_available": self.router_llm is not None,
            "router_llm_type": self.router_llm.__class__.__name__ if self.router_llm else None,
            "status": "operational" if self.router_llm else "degraded"
        }
