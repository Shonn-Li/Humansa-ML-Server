#!/usr/bin/env python3
"""
Debug script to check router decisions with attachments
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chat.router.intelligent_router import IntelligentRouter
from src.chat.provider.llm_provider import LLMProviderSelector

async def test_router_decisions():
    """Test what the router decides for different queries with attachments"""
    
    # Initialize router
    llm_provider_manager = LLMProviderSelector()
    router = IntelligentRouter(llm_provider_manager)
    
    test_cases = [
        {
            "name": "Simple attachment query",
            "query": "Summarize this paper",
            "has_attachments": True
        },
        {
            "name": "Attachment with 'about' keyword",
            "query": "Tell me what this paper is about",
            "has_attachments": True
        },
        {
            "name": "No attachment control",
            "query": "What do my notes say about PARL?",
            "has_attachments": False
        }
    ]
    
    print("="*80)
    print("ROUTER DECISION TESTING")
    print("="*80)
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Query: {test['query']}")
        print(f"Has Attachments: {test['has_attachments']}")
        print("-"*50)
        
        try:
            decision = await router.route_query(
                test['query'], 
                "10001",
                [],
                test['has_attachments']
            )
            
            print(f"Selected Tool: {decision.selected_tool}")
            print(f"Search Type: {decision.search_type}")
            print(f"Confidence: {decision.confidence}")
            print(f"Reasoning: {decision.reasoning}")
            print(f"Classification: {decision.query_classification}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_router_decisions())