#!/usr/bin/env python
"""
Test script to verify WorkflowOrchestrator streaming capabilities
Shows reasoning steps and tool calls in real-time
"""

import asyncio
import json
import os
from datetime import datetime

# Set up environment
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "dummy-key-for-test")


async def test_workflow_streaming():
    """Test the WorkflowOrchestrator with streaming events"""
    
    print("🧪 Testing WorkflowOrchestrator Streaming")
    print("=" * 60)
    
    try:
        # Import components
        from llama_index.llms.openai import OpenAI
        from src.humansa.v2.orchestrator_workflow import create_workflow_orchestrator
        
        # Create LLM
        llm = OpenAI(model="gpt-4", temperature=0.7)
        
        # Create workflow orchestrator
        orchestrator = create_workflow_orchestrator(
            llm=llm,
            debug=True
        )
        
        # Test query
        test_query = "我想买一些维生素C，有什么推荐吗？"
        print(f"📝 Query: {test_query}")
        print("=" * 60)
        
        # Track event types
        event_counts = {}
        
        # Process with streaming
        print("\n🔄 Streaming Events:")
        print("-" * 60)
        
        async for event in orchestrator.process_query(
            query=test_query,
            user_id="test_user_workflow",
            stream=True
        ):
            event_type = event.get("type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Display different event types
            if event_type == "response.created":
                print(f"\n✅ Response Created: {event['response']['id']}")
                
            elif event_type == "response.reasoning_text.delta":
                # Show reasoning in real-time
                print(f"💭 {event['delta']}", end="", flush=True)
                
            elif event_type == "response.output_item.added":
                item = event["item"]
                if item["type"] == "reasoning":
                    print(f"\n\n🧠 Starting Reasoning (ID: {item['id']})")
                elif item["type"] == "function_tool_call":
                    print(f"\n\n🔧 Calling Tool: {item['name']}")
                elif item["type"] == "message":
                    print(f"\n\n💬 Final Response:")
                    
            elif event_type == "response.output_text.delta":
                # Show final response text
                print(f"{event['delta']}", end="", flush=True)
                
            elif event_type == "response.output_item.done":
                item = event["item"]
                if item["type"] == "function_tool_call":
                    print(f"\n✅ Tool Completed: {item.get('output', '')[:100]}...")
                    
            elif event_type == "response.usage":
                usage = event["usage"]
                print(f"\n\n📊 Usage Stats:")
                print(f"   - Agents Used: {usage['agents_used']}")
                print(f"   - Total Agents: {usage['total_agents']}")
                print(f"   - Duration: {usage['duration']:.2f}s")
                
            elif event_type == "response.completed":
                print(f"\n\n✅ Response Completed!")
        
        # Show event summary
        print("\n" + "=" * 60)
        print("📈 Event Summary:")
        for event_type, count in sorted(event_counts.items()):
            print(f"   - {event_type}: {count}")
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure LlamaIndex is installed with workflow support:")
        print("pip install llama-index-core llama-index-agent-workflow")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_non_streaming():
    """Test non-streaming mode"""
    
    print("\n\n🧪 Testing Non-Streaming Mode")
    print("=" * 60)
    
    try:
        from llama_index.llms.openai import OpenAI
        from src.humansa.v2.orchestrator_workflow import create_workflow_orchestrator
        
        # Create components
        llm = OpenAI(model="gpt-4", temperature=0.7)
        orchestrator = create_workflow_orchestrator(llm=llm)
        
        # Test query
        test_query = "我需要预约心内科医生"
        print(f"📝 Query: {test_query}")
        
        # Process without streaming
        async for response in orchestrator.process_query(
            query=test_query,
            user_id="test_user_workflow",
            stream=False
        ):
            print(f"\n📄 Response Structure: {list(response.keys())}")
            
            if "choices" in response:
                content = response["choices"][0]["message"]["content"]
                print(f"\n💬 Response:\n{content}")
                
            if "usage" in response:
                usage = response["usage"]
                print(f"\n📊 Agents Used: {usage.get('agents_used', [])}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print(f"🚀 Starting WorkflowOrchestrator Test")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests
    asyncio.run(test_workflow_streaming())
    asyncio.run(test_non_streaming())
    
    print("\n✅ Test completed!")