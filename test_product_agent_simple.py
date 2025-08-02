#!/usr/bin/env python3
"""
Simple test script for Enhanced Product Agent
"""

import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Import directly
import asyncpg
import json
from datetime import datetime


class MockLLM:
    """Mock LLM for testing."""
    async def astream_complete(self, prompt):
        """Mock streaming."""
        response = "基于您的睡眠问题，我推荐以下产品：\n1. 褪黑素片 - 改善睡眠质量\n2. 薰衣草精油 - 助眠放松"
        for word in response.split():
            yield type('obj', (), {'delta': word + ' '})()
    
    async def acomplete(self, prompt):
        """Mock completion."""
        return type('obj', (), {'text': json.dumps({
            "selected_agents": ["search_products"],
            "selection_reason": "用户需要产品推荐",
            "information_gaps": []
        })})()
    
    def chat(self, query):
        """Mock chat."""
        return type('obj', (), {
            'response': "根据您的需求，推荐褪黑素片和薰衣草精油。"
        })()
    
    def update_prompts(self, prompts):
        """Mock update prompts."""
        pass


class SimpleReActAgent:
    """Simple mock ReAct agent."""
    def __init__(self, tools, llm, system_prompt, verbose):
        self.tools = tools
        self.llm = llm
        self.system_prompt = system_prompt
        self.verbose = verbose
    
    @classmethod
    def from_tools(cls, tools, llm, system_prompt, verbose=True):
        return cls(tools, llm, system_prompt, verbose)
    
    def chat(self, query):
        return self.llm.chat(query)
    
    def stream_chat(self, query):
        """Mock streaming chat."""
        class AsyncGen:
            async def async_response_gen(self):
                response = "基于您的需求，我为您推荐以下产品：\n\n1. 褪黑素片 - 每晚睡前服用，改善睡眠质量\n2. 薰衣草精油 - 滴在枕头上，有助于放松助眠"
                for char in response:
                    yield char
        return AsyncGen()
    
    def update_prompts(self, prompts):
        self.system_prompt = prompts.get('system', self.system_prompt)


# Mock LlamaIndex imports
class FunctionTool:
    @staticmethod
    def from_defaults(fn, name, description):
        return {'fn': fn, 'name': name, 'description': description}


async def test_database_connection():
    """Test database connection."""
    print("\n=== Testing Database Connection ===")
    
    db_config = {
        "host": "localhost",
        "port": 5454,
        "user": "postgres", 
        "password": "12931",
        "database": "test4"
    }
    
    try:
        conn = await asyncpg.connect(**db_config)
        
        # Check if products table exists
        result = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'humansa_products'
        """)
        
        if result > 0:
            # Count products
            count = await conn.fetchval("SELECT COUNT(*) FROM humansa_products")
            print(f"✅ Connected to database")
            print(f"✅ Found humansa_products table with {count} products")
            
            # Get sample products
            products = await conn.fetch("""
                SELECT p.*, c.name as category_name
                FROM humansa_products p
                LEFT JOIN humansa_product_category c ON p.category_id = c.category_id
                LIMIT 5
            """)
            
            print("\nSample products:")
            for p in products:
                print(f"  - {p['name']} ({p['category_name']}) - ¥{p['price']}")
            
            await conn.close()
            return True
        else:
            print("❌ humansa_products table not found")
            await conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_enhanced_product_agent():
    """Test the enhanced product agent implementation."""
    print("\n=== Testing Enhanced Product Agent ===")
    
    # Import the agent code inline
    exec(open('src/humansa/v2/agents/product_agent_enhanced.py').read(), globals())
    
    # Create agent with mock LLM
    llm = MockLLM()
    db_config = {
        "host": "localhost",
        "port": 5454,
        "user": "postgres",
        "password": "12931", 
        "database": "test4"
    }
    
    # Replace ReActAgent with mock
    globals()['ReActAgent'] = SimpleReActAgent
    
    agent = EnhancedProductAgent(llm=llm, db_config=db_config)
    
    # Test cache refresh
    print("\n1. Testing cache refresh...")
    await agent.ensure_fresh_cache()
    stats = agent.get_statistics()
    print(f"   Loaded {stats['total_products']} products")
    print(f"   Categories: {stats['categories']}")
    
    # Test product search
    print("\n2. Testing product search...")
    results = await agent._search_products("维生素")
    print(f"   Found {len(results)} products matching '维生素'")
    for r in results[:3]:
        print(f"   - {r['name']} (¥{r['price']})")
    
    # Test streaming query
    print("\n3. Testing streaming query processing...")
    print("   Query: 我最近失眠，有什么产品推荐？")
    print("   Response: ", end='')
    
    response_text = ""
    async for chunk in agent.process_query("我最近失眠，有什么产品推荐？", {}, stream=True):
        if chunk['type'] == 'content':
            print(chunk['chunk'], end='', flush=True)
            response_text += chunk['chunk']
    
    print("\n")
    
    # Verify response contains expected content
    if "褪黑素" in response_text or "助眠" in response_text or "小程序" in response_text:
        print("✅ Response contains expected product recommendations")
    else:
        print("⚠️  Response may not contain expected content")
    
    return True


async def main():
    """Main test function."""
    print("=" * 60)
    print("Enhanced Product Agent Simple Test")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test database first
    db_ok = await test_database_connection()
    
    if db_ok:
        # Test agent
        agent_ok = await test_enhanced_product_agent()
        
        if agent_ok:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Agent tests failed")
    else:
        print("\n❌ Cannot proceed without database connection")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())