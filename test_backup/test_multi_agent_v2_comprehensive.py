#!/usr/bin/env python3
"""
Comprehensive Test for Multi-Agent Endpoint V2
Tests all agents with specific use cases and streaming functionality.
"""

import asyncio
import json
import logging
import sys
import os
import time
from typing import Dict, Any, List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_individual_agents():
    """Test each agent individually with specific use cases"""
    logger.info("🔬 Testing Individual Agents")
    
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        
        endpoint = MultiAgentChatEndpointV2()
        results = {}
        
        # Test 1: Router Agent - Query Analysis
        logger.info("📍 Testing Router Agent...")
        router_request = {
            "messages": [{"role": "user", "content": "Search for AI developments and analyze my uploaded research paper"}],
            "model": "gpt-4.1-nano",
            "user_id": "test_user_123",
            "attachments": [{"type": "pdf", "url": "research.pdf", "filename": "ai_research.pdf"}],
            "enable_web_search": True,
            "enable_citations": True
        }
        
        context = {}
        router_result = await endpoint.agents["router"].run(router_request, context)
        results["router"] = router_result
        logger.info(f"✅ Router enabled agents: {router_result.get('enabled_agents', [])}")
        
        # Test 2: Web Search Agent - Current Events
        logger.info("🌐 Testing Web Search Agent...")
        web_request = {
            "messages": [{"role": "user", "content": "Latest AI breakthroughs in 2025"}],
            "model": "gpt-4.1-nano", 
            "user_id": "test_user_123"
        }
        context["router_agent"] = {"condensed_query": "Latest AI breakthroughs 2025", "original_query": "Latest AI breakthroughs in 2025"}
        
        web_result = await endpoint.agents["web_search"].run(web_request, context)
        results["web_search"] = web_result
        logger.info(f"✅ Web search found {len(web_result.get('results', []))} results")
        
        # Test 3: RAG Agent - Knowledge Base Query
        logger.info("🧠 Testing RAG Agent...")
        rag_request = {
            "messages": [{"role": "user", "content": "What are my previous notes about machine learning?"}],
            "model": "gpt-4.1-nano",
            "user_id": "test_user_123"
        }
        context["router_agent"] = {"condensed_query": "machine learning notes", "search_type": "knowledge_base"}
        
        rag_result = await endpoint.agents["rag"].run(rag_request, context)
        results["rag"] = rag_result
        logger.info(f"✅ RAG retrieved context length: {len(rag_result.get('context', ''))}")
        
        # Test 4: Attachment Agent - File Processing
        logger.info("📎 Testing Attachment Agent...")
        attachment_request = {
            "messages": [{"role": "user", "content": "Analyze this research paper"}],
            "model": "gpt-4.1-nano",
            "user_id": "test_user_123",
            "attachments": [
                {"type": "pdf", "url": "research.pdf", "filename": "ai_research.pdf"},
                {"type": "image", "url": "chart.png", "filename": "results_chart.png"}
            ]
        }
        context["router_agent"] = {"condensed_query": "analyze research paper"}
        
        attachment_result = await endpoint.agents["attachment"].run(attachment_request, context)
        results["attachment"] = attachment_result
        logger.info(f"✅ Attachment processed {attachment_result.get('metadata', {}).get('attachment_count', 0)} files")
        
        # Test 5: Response Agent - Final Generation
        logger.info("🎯 Testing Response Agent...")
        context["rag_agent"] = {"context": "Previous notes about ML algorithms and techniques"}
        context["web_search_agent"] = {"context": "Recent AI developments in neural networks"}
        context["attachment_agent"] = {"context": "Research paper discusses transformer architectures"}
        
        response_request = {
            "messages": [{"role": "user", "content": "Explain the latest AI developments based on my research"}],
            "model": "gpt-4.1-nano",
            "user_id": "test_user_123"
        }
        
        response_result = await endpoint.agents["response"].run(response_request, context)
        results["response"] = response_result
        logger.info(f"✅ Response generated: {len(response_result.get('response', ''))} characters")
        
        # Test 6: Citation Agent - Reference Addition
        logger.info("📚 Testing Citation Agent...")
        context["response_agent"] = {"response": "AI has advanced significantly with transformer models and neural architectures."}
        
        citation_result = await endpoint.agents["citation"].run(response_request, context)
        results["citation"] = citation_result
        logger.info(f"✅ Citations processed: {citation_result.get('metadata', {}).get('source_count', 0)} sources")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Individual agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_full_workflow_non_streaming():
    """Test the complete multi-agent workflow (non-streaming)"""
    logger.info("🔄 Testing Full Non-Streaming Workflow")
    
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        
        endpoint = MultiAgentChatEndpointV2()
        
        # Comprehensive test request
        test_request = {
            "messages": [
                {"role": "user", "content": "Search for recent AI developments, check my notes about machine learning, and analyze the attached research paper to give me a comprehensive overview"},
            ],
            "model": "gpt-4.1-nano",
            "user_id": "test_user_123",
            "stream": False,
            "enable_web_search": True,
            "enable_citations": True,
            "attachments": [
                {"type": "pdf", "url": "ai_research.pdf", "filename": "ai_research.pdf"},
                {"type": "image", "url": "results.png", "filename": "results.png"}
            ]
        }
        
        start_time = time.time()
        result = await endpoint.handle_request(test_request)
        end_time = time.time()
        
        logger.info(f"✅ Non-streaming workflow completed in {end_time - start_time:.2f}s")
        logger.info(f"📊 Response: {result.get('choices', [{}])[0].get('message', {}).get('content', '')[:100]}...")
        logger.info(f"📈 Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Non-streaming workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_streaming_workflow():
    """Test the complete multi-agent workflow with streaming"""
    logger.info("🌊 Testing Full Streaming Workflow")
    
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        
        endpoint = MultiAgentChatEndpointV2()
        
        # Comprehensive streaming test request  
        test_request = {
            "messages": [
                {"role": "user", "content": "Search the web for latest AI developments, find my previous notes about neural networks, process the attached research paper, and provide a comprehensive analysis with proper citations"}
            ],
            "model": "gpt-4.1-nano", 
            "user_id": "test_user_123",
            "stream": True,
            "enable_web_search": True,
            "enable_citations": True,
            "attachments": [
                {"type": "pdf", "url": "research.pdf", "filename": "transformer_research.pdf"},
                {"type": "image", "url": "architecture.png", "filename": "model_architecture.png"}
            ]
        }
        
        start_time = time.time()
        result = await endpoint.handle_request(test_request)
        
        # Process streaming events
        events = []
        event_types = set()
        output_items = []
        
        logger.info("📡 Processing streaming events...")
        
        async for event in result:
            events.append(event)
            event_type = event.get('type', 'unknown')
            event_types.add(event_type)
            
            # Log important events
            if event_type == 'response.created':
                logger.info(f"🚀 Response started: {event.get('response', {}).get('id')}")
            elif event_type == 'response.output_item.added':
                item = event.get('item', {})
                output_items.append(item)
                logger.info(f"📦 Output item added: {item.get('type')} ({item.get('id')})")
            elif event_type == 'response.reasoning_text.delta':
                delta = event.get('delta', '')
                logger.info(f"💭 Reasoning: {delta[:50]}...")
            elif event_type == 'response.web_search_call.searching':
                logger.info("🔍 Web search in progress...")
            elif event_type == 'response.file_search_call.searching':
                logger.info("📁 File search in progress...")
            elif event_type == 'response.output_text.delta':
                delta = event.get('delta', '')
                logger.info(f"✏️ Response: {delta[:30]}...")
            elif event_type == 'response.citations':
                citations = event.get('citations', [])
                logger.info(f"📚 Citations added: {len(citations)}")
            elif event_type == 'response.completed':
                end_time = time.time()
                logger.info(f"✅ Streaming completed in {end_time - start_time:.2f}s")
            
            # Limit for testing
            if len(events) >= 100:
                logger.warning("⚠️ Limiting to 100 events for testing")
                break
        
        logger.info(f"📊 Streaming Results:")
        logger.info(f"   Total Events: {len(events)}")
        logger.info(f"   Event Types: {len(event_types)}")
        logger.info(f"   Output Items: {len(output_items)}")
        logger.info(f"   Event Types Found: {sorted(event_types)}")
        
        # Validate streaming structure
        success = True
        
        if not events:
            logger.error("❌ No events received")
            success = False
        elif events[0].get('type') != 'response.created':
            logger.error(f"❌ First event should be 'response.created', got '{events[0].get('type')}'")
            success = False
        elif events[-1].get('type') not in ['response.completed', 'response.failed']:
            logger.error(f"❌ Last event should be terminal, got '{events[-1].get('type')}'")
            success = False
        
        # Check for key streaming events
        required_events = [
            'response.created',
            'response.in_progress',
            'response.output_item.added',
            'response.output_item.done',
        ]
        
        missing_events = []
        for required in required_events:
            if required not in event_types:
                missing_events.append(required)
        
        if missing_events:
            logger.error(f"❌ Missing required events: {missing_events}")
            success = False
        
        if success:
            logger.info("✅ Streaming workflow validation PASSED")
        else:
            logger.error("❌ Streaming workflow validation FAILED")
        
        return {
            "success": success,
            "events": events,
            "event_types": list(event_types),
            "output_items": output_items,
            "total_time": end_time - start_time if 'end_time' in locals() else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Streaming workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def test_specific_use_cases():
    """Test specific use cases for each agent type"""
    logger.info("🎯 Testing Specific Use Cases")
    
    test_cases = [
        {
            "name": "Knowledge Base Query",
            "request": {
                "messages": [{"role": "user", "content": "What did I write about artificial intelligence in my notes?"}],
                "model": "gpt-4.1-nano",
                "user_id": "test_user_123",
                "stream": True
            },
            "expected_agents": ["router", "rag", "response", "citation"]
        },
        {
            "name": "Current Events Search", 
            "request": {
                "messages": [{"role": "user", "content": "What are the latest developments in quantum computing?"}],
                "model": "gpt-4.1-nano",
                "user_id": "test_user_123",
                "stream": True,
                "enable_web_search": True
            },
            "expected_agents": ["router", "web_search", "response", "citation"]
        },
        {
            "name": "File Analysis",
            "request": {
                "messages": [{"role": "user", "content": "Analyze this research document and summarize key findings"}],
                "model": "gpt-4.1-nano",
                "user_id": "test_user_123",
                "stream": True,
                "attachments": [{"type": "pdf", "url": "research.pdf", "filename": "research.pdf"}]
            },
            "expected_agents": ["router", "attachment", "response", "citation"]
        },
        {
            "name": "Comprehensive Research",
            "request": {
                "messages": [{"role": "user", "content": "Research the topic of transformer architectures, check my existing notes, analyze the attached paper, and provide a complete overview with citations"}],
                "model": "gpt-4.1-nano",
                "user_id": "test_user_123", 
                "stream": True,
                "enable_web_search": True,
                "enable_citations": True,
                "attachments": [{"type": "pdf", "url": "transformer_paper.pdf", "filename": "attention_is_all_you_need.pdf"}]
            },
            "expected_agents": ["router", "rag", "web_search", "attachment", "response", "citation"]
        }
    ]
    
    results = {}
    
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        for test_case in test_cases:
            logger.info(f"🧪 Testing: {test_case['name']}")
            
            start_time = time.time()
            result = await endpoint.handle_request(test_case['request'])
            
            events = []
            triggered_agents = set()
            
            async for event in result:
                events.append(event)
                
                # Track which agents were triggered
                if event.get('type') == 'response.output_item.added':
                    item_type = event.get('item', {}).get('type')
                    if item_type == 'reasoning':
                        triggered_agents.add('router')
                    elif item_type == 'web_search_call':
                        triggered_agents.add('web_search')
                    elif item_type == 'file_search_call':
                        triggered_agents.add('rag')
                    elif item_type == 'function_tool_call':
                        triggered_agents.add('attachment')
                    elif item_type == 'message':
                        triggered_agents.add('response')
                
                if event.get('type') == 'response.citations':
                    triggered_agents.add('citation')
                
                # Limit events for testing
                if len(events) >= 50:
                    break
            
            end_time = time.time()
            
            results[test_case['name']] = {
                "success": len(events) > 0,
                "events": len(events),
                "triggered_agents": list(triggered_agents),
                "expected_agents": test_case['expected_agents'],
                "time": end_time - start_time
            }
            
            logger.info(f"✅ {test_case['name']}: {len(events)} events, agents: {list(triggered_agents)}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Specific use cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def main():
    """Run all comprehensive tests"""
    logger.info("🧪 YouWoAI Multi-Agent Endpoint V2 Comprehensive Test Suite")
    logger.info("=" * 80)
    
    all_results = {}
    
    # Test 1: Individual Agents
    logger.info("\n" + "=" * 80)
    individual_results = await test_individual_agents()
    all_results["individual_agents"] = individual_results
    
    # Test 2: Non-Streaming Workflow
    logger.info("\n" + "=" * 80)
    non_streaming_results = await test_full_workflow_non_streaming()
    all_results["non_streaming_workflow"] = non_streaming_results
    
    # Test 3: Streaming Workflow
    logger.info("\n" + "=" * 80)
    streaming_results = await test_streaming_workflow()
    all_results["streaming_workflow"] = streaming_results
    
    # Test 4: Specific Use Cases
    logger.info("\n" + "=" * 80)
    use_case_results = await test_specific_use_cases()
    all_results["use_cases"] = use_case_results
    
    # Final Report
    logger.info("\n" + "=" * 80)
    logger.info("🏁 COMPREHENSIVE TEST RESULTS")
    logger.info("=" * 80)
    
    # Summary
    individual_success = bool(individual_results)
    non_streaming_success = bool(non_streaming_results)
    streaming_success = streaming_results.get("success", False) if streaming_results else False
    use_case_success = all(r.get("success", False) for r in use_case_results.values()) if use_case_results else False
    
    logger.info(f"📊 Test Results:")
    logger.info(f"   Individual Agents: {'✅ PASS' if individual_success else '❌ FAIL'}")
    logger.info(f"   Non-Streaming: {'✅ PASS' if non_streaming_success else '❌ FAIL'}")
    logger.info(f"   Streaming: {'✅ PASS' if streaming_success else '❌ FAIL'}")
    logger.info(f"   Use Cases: {'✅ PASS' if use_case_success else '❌ FAIL'}")
    
    overall_success = all([individual_success, non_streaming_success, streaming_success, use_case_success])
    
    if overall_success:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("✅ Multi-Agent Endpoint V2 is fully functional with streaming support")
    else:
        logger.error("\n💥 SOME TESTS FAILED!")
        logger.error("❌ Review the implementation and fix issues")
    
    # Save detailed results
    with open("multi_agent_v2_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\n📄 Detailed results saved to: multi_agent_v2_test_results.json")
    
    return overall_success


if __name__ == "__main__":
    asyncio.run(main())