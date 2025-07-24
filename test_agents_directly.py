#!/usr/bin/env python3
"""
Test the search agents directly to verify they're working
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_context_search():
    """Test context search agent directly"""
    print("Testing Context Search Agent...")
    print("-" * 80)
    
    try:
        from chat.agent.context_search_agent import ContextSearchAgent
        
        # Create agent instance
        agent = ContextSearchAgent()
        
        # Test request
        request = {
            "messages": [{"role": "user", "content": "Tell me about AI"}],
            "user_id": 10001,  # Test user
            "model": "openai/gpt-4o-mini"
        }
        
        # Run the agent
        result = await agent.run(request, {})
        
        print("Context Search Result:")
        print(f"Type: {type(result)}")
        print(f"Keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            if "sources" in result:
                print(f"Sources found: {len(result['sources'])}")
                if result['sources']:
                    print(f"First source: {result['sources'][0]}")
            elif "results" in result:
                print(f"Results found: {len(result['results'])}")
                if result['results']:
                    print(f"First result: {result['results'][0]}")
            else:
                print("No sources or results in response")
                print(f"Full result: {result}")
        
    except Exception as e:
        print(f"Context search failed: {e}")
        import traceback
        traceback.print_exc()

async def test_web_search():
    """Test web search agent directly"""
    print("\n\nTesting Web Search Agent...")
    print("-" * 80)
    
    try:
        from chat.agent.websearch_agent import WebSearchAgent
        
        # Create agent instance
        agent = WebSearchAgent()
        
        # Test request
        request = {
            "messages": [{"role": "user", "content": "Latest news about AI"}],
            "user_id": 10001,
            "model": "openai/gpt-4o-mini"
        }
        
        # Run the agent
        result = await agent.run(request, {})
        
        print("Web Search Result:")
        print(f"Type: {type(result)}")
        print(f"Keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            if "results" in result:
                print(f"Results found: {len(result['results'])}")
                if result['results']:
                    print(f"First result: {result['results'][0]}")
            else:
                print("No results in response")
                print(f"Full result: {result}")
        
    except Exception as e:
        print(f"Web search failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests"""
    await test_context_search()
    await test_web_search()

if __name__ == "__main__":
    asyncio.run(main())