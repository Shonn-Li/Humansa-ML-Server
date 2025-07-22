#!/usr/bin/env python3
"""
Enhanced Multi-Agent Service Validation Test

This script provides detailed validation of which services were called,
what queries were sent, and what results were returned for each agent.
"""

import asyncio
import json
import aiohttp
import sys
import os
from typing import Dict, Any, List
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test configuration
ML_SERVER_URL = "http://localhost:5001"
MULTI_AGENT_ENDPOINT = f"{ML_SERVER_URL}/v1/multi-agent/response"
TEST_USER_ID = 3


def print_section(title: str, char: str = "=", width: int = 70):
    """Print a formatted section header"""
    print(f"\n{char * width}")
    print(f"{title.center(width)}")
    print(f"{char * width}")


def print_subsection(title: str, char: str = "-", width: int = 50):
    """Print a formatted subsection header"""
    print(f"\n{char * width}")
    print(f"{title}")
    print(f"{char * width}")


def analyze_agent_execution(agent_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze agent execution details"""
    analysis = {
        "executed_agents": [],
        "successful_agents": [],
        "failed_agents": [],
        "execution_summary": {}
    }

    for agent_name, agent_data in agent_results.items():
        if isinstance(agent_data, dict):
            analysis["executed_agents"].append(agent_name)

            success = agent_data.get("success", False)
            execution_time = agent_data.get("execution_time", 0)

            if success:
                analysis["successful_agents"].append(agent_name)
            else:
                analysis["failed_agents"].append(agent_name)

            analysis["execution_summary"][agent_name] = {
                "success": success,
                "execution_time": execution_time,
                "error": agent_data.get("error"),
                "data_keys": list(agent_data.get("data", {}).keys()) if agent_data.get("data") else []
            }

    return analysis


def print_router_analysis(agent_results: Dict[str, Any]):
    """Print detailed router analysis"""
    router_data = agent_results.get("router_agent", {})
    if not router_data:
        print("   ❌ No router data found")
        return

    print("   🎯 ROUTER AGENT ANALYSIS:")
    print(f"   • Success: {'✅' if router_data.get('success') else '❌'}")
    print(f"   • Execution time: {router_data.get('execution_time', 0):.2f}s")

    router_agent_data = router_data.get("data", {})
    if router_agent_data:
        print(
            f"   • Original query: {router_agent_data.get('original_query', 'N/A')}")
        print(
            f"   • Condensed query: {router_agent_data.get('condensed_query', 'N/A')}")
        print(
            f"   • Enabled agents: {router_agent_data.get('enabled_agents', [])}")

        # Router decision details
        router_decision = router_agent_data.get("router_decision", {})
        if router_decision:
            print(
                f"   • Selected tool: {router_decision.get('selected_tool', 'N/A')}")
            print(
                f"   • Search type: {router_decision.get('search_type', 'N/A')}")
            print(
                f"   • Confidence: {router_decision.get('confidence', 'N/A')}")
            print(f"   • Reasoning: {router_decision.get('reasoning', 'N/A')}")


def print_rag_analysis(agent_results: Dict[str, Any]):
    """Print detailed RAG analysis"""
    rag_data = agent_results.get("rag_agent", {})
    if not rag_data:
        print("   ⚪ RAG Agent not executed")
        return

    print("   🔍 RAG AGENT ANALYSIS:")
    print(f"   • Success: {'✅' if rag_data.get('success') else '❌'}")
    print(f"   • Execution time: {rag_data.get('execution_time', 0):.2f}s")

    if not rag_data.get('success'):
        print(f"   • Error: {rag_data.get('error', 'Unknown error')}")
        return

    rag_agent_data = rag_data.get("data", {})
    if rag_agent_data:
        rag_context = rag_agent_data.get("rag_context", {})
        print(
            f"   • Total chunks found: {rag_agent_data.get('total_chunks', 0)}")
        print(f"   • Used note IDs: {rag_agent_data.get('used_note_ids', [])}")
        print(
            f"   • Used conversation IDs: {rag_agent_data.get('used_conversation_ids', [])}")
        print(f"   • Query used: {rag_agent_data.get('query_used', 'N/A')}")

        if rag_context and isinstance(rag_context, dict):
            chunks = rag_context.get("chunks", [])
            if chunks:
                print(f"   • Sample chunks found:")
                for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                    content = chunk.get("content", "")[
                        :100] + "..." if len(chunk.get("content", "")) > 100 else chunk.get("content", "")
                    print(f"     {i+1}. {content}")


def print_web_search_analysis(agent_results: Dict[str, Any]):
    """Print detailed web search analysis"""
    web_data = agent_results.get("web_search_agent", {})
    if not web_data:
        print("   ⚪ Web Search Agent not executed")
        return

    print("   🌐 WEB SEARCH AGENT ANALYSIS:")
    print(f"   • Success: {'✅' if web_data.get('success') else '❌'}")
    print(f"   • Execution time: {web_data.get('execution_time', 0):.2f}s")

    if not web_data.get('success'):
        print(f"   • Error: {web_data.get('error', 'Unknown error')}")
        return

    web_agent_data = web_data.get("data", {})
    if web_agent_data:
        web_context = web_agent_data.get("web_context", {})
        print(f"   • Total results: {web_agent_data.get('total_results', 0)}")
        print(f"   • Query used: {web_agent_data.get('query_used', 'N/A')}")

        if web_context and isinstance(web_context, dict):
            results = web_context.get("results", [])
            if results:
                print(f"   • Sample search results:")
                # Show first 2 results
                for i, result in enumerate(results[:2]):
                    title = result.get("title", "")[
                        :60] + "..." if len(result.get("title", "")) > 60 else result.get("title", "")
                    print(f"     {i+1}. {title}")
                    print(f"        URL: {result.get('url', 'N/A')}")


def print_attachment_analysis(agent_results: Dict[str, Any]):
    """Print detailed attachment analysis"""
    attachment_data = agent_results.get("attachment_agent", {})
    if not attachment_data:
        print("   ⚪ Attachment Agent not executed")
        return

    print("   📎 ATTACHMENT AGENT ANALYSIS:")
    print(f"   • Success: {'✅' if attachment_data.get('success') else '❌'}")
    print(
        f"   • Execution time: {attachment_data.get('execution_time', 0):.2f}s")

    if not attachment_data.get('success'):
        print(f"   • Error: {attachment_data.get('error', 'Unknown error')}")
        return

    attachment_agent_data = attachment_data.get("data", {})
    if attachment_agent_data:
        attachment_context = attachment_agent_data.get(
            "attachment_context", {})
        print(
            f"   • Total attachments processed: {attachment_agent_data.get('total_attachments', 0)}")
        print(
            f"   • Processed files: {attachment_agent_data.get('processed_files', [])}")


def print_response_analysis(agent_results: Dict[str, Any]):
    """Print detailed response analysis"""
    response_data = agent_results.get("response_agent", {})
    if not response_data:
        print("   ❌ Response Agent not executed")
        return

    print("   🤖 RESPONSE AGENT ANALYSIS:")
    print(f"   • Success: {'✅' if response_data.get('success') else '❌'}")
    print(
        f"   • Execution time: {response_data.get('execution_time', 0):.2f}s")

    if not response_data.get('success'):
        print(f"   • Error: {response_data.get('error', 'Unknown error')}")
        return

    response_agent_data = response_data.get("data", {})
    if response_agent_data:
        response_text = response_agent_data.get("response", "")
        print(
            f"   • Model used: {response_agent_data.get('model_used', 'N/A')}")
        print(
            f"   • Context used: {'Yes' if response_agent_data.get('context_used') else 'No'}")
        print(
            f"   • Total messages: {response_agent_data.get('total_messages', 0)}")
        print(f"   • Response length: {len(response_text)} characters")

        context_summary = response_agent_data.get("context_summary", {})
        if context_summary:
            print(f"   • Context breakdown:")
            print(f"     - RAG chunks: {context_summary.get('rag_chunks', 0)}")
            print(
                f"     - Web results: {context_summary.get('web_results', 0)}")
            print(
                f"     - Attachments: {context_summary.get('attachments', 0)}")


def print_citation_analysis(agent_results: Dict[str, Any]):
    """Print detailed citation analysis"""
    citation_data = agent_results.get("citation_agent", {})
    if not citation_data:
        print("   ⚪ Citation Agent not executed")
        return

    print("   📚 CITATION AGENT ANALYSIS:")
    print(f"   • Success: {'✅' if citation_data.get('success') else '❌'}")
    print(
        f"   • Execution time: {citation_data.get('execution_time', 0):.2f}s")

    if not citation_data.get('success'):
        print(f"   • Error: {citation_data.get('error', 'Unknown error')}")
        return

    citation_agent_data = citation_data.get("data", {})
    if citation_agent_data:
        citations = citation_agent_data.get("citations", [])
        cited_response = citation_agent_data.get("cited_response", "")
        print(f"   • Citations found: {len(citations)}")
        print(f"   • Cited response length: {len(cited_response)} characters")

        if citations:
            print(f"   • Sample citations:")
            # Show first 2 citations
            for i, citation in enumerate(citations[:2]):
                print(f"     {i+1}. Source: {citation.get('source', 'N/A')}")
                print(f"        Type: {citation.get('type', 'N/A')}")


async def run_enhanced_test(test_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single enhanced test with detailed analysis"""

    print_subsection(f"🧪 {test_name}")

    # Print request details
    print("📤 REQUEST DETAILS:")
    print(f"   • User ID: {request_data.get('user_id')}")
    print(f"   • Model: {request_data.get('model')}")
    print(f"   • Stream: {request_data.get('stream', False)}")
    print(
        f"   • Enable Citations: {request_data.get('enable_citations', False)}")
    print(
        f"   • Completion Type: {request_data.get('completion_type', 'N/A')}")
    print(f"   • Note IDs: {request_data.get('note_ids', [])}")
    print(f"   • Conversation IDs: {request_data.get('conversation_ids', [])}")
    print(f"   • Attachments: {len(request_data.get('attachments', []))}")

    # Print query
    messages = request_data.get("messages", [])
    if messages:
        user_message = next(
            (msg for msg in messages if msg.get("role") == "user"), None)
        if user_message:
            query = user_message.get("content", "")
            print(f"   • Query: {query}")

    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                MULTI_AGENT_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:

                request_time = time.time() - start_time

                if response.status == 200:
                    result = await response.json()

                    print(f"\n📥 RESPONSE SUMMARY:")
                    print(f"   • Status: {result.get('status', 'Unknown')}")
                    print(f"   • Request time: {request_time:.2f}s")

                    if result.get("status") == "success":
                        data = result.get("data", {})
                        usage = data.get("usage", {})
                        metadata = data.get("metadata", {})

                        print(
                            f"   • Workflow time: {usage.get('workflow_time', 0):.2f}s")
                        print(
                            f"   • Enabled agents: {usage.get('enabled_agents', [])}")
                        print(
                            f"   • Total agents: {usage.get('total_agents', 0)}")

                        # Final response
                        response_text = data.get("response", "")
                        print(
                            f"   • Final response length: {len(response_text)} characters")
                        if response_text:
                            preview = response_text[:150] + "..." if len(
                                response_text) > 150 else response_text
                            print(f"   • Response preview: {preview}")

                        # Agent-by-agent analysis
                        agent_results = metadata.get("agent_results", {})
                        if agent_results:
                            print_subsection("🔍 DETAILED AGENT ANALYSIS")

                            # Analyze overall execution
                            analysis = analyze_agent_execution(agent_results)
                            print(f"📊 EXECUTION OVERVIEW:")
                            print(
                                f"   • Executed agents: {len(analysis['executed_agents'])}")
                            print(
                                f"   • Successful: {len(analysis['successful_agents'])}")
                            print(
                                f"   • Failed: {len(analysis['failed_agents'])}")
                            if analysis['failed_agents']:
                                print(
                                    f"   • Failed agents: {analysis['failed_agents']}")

                            # Individual agent analysis
                            print_router_analysis(agent_results)
                            print_rag_analysis(agent_results)
                            print_web_search_analysis(agent_results)
                            print_attachment_analysis(agent_results)
                            print_response_analysis(agent_results)
                            print_citation_analysis(agent_results)

                        # Context summary
                        context_summary = metadata.get("context_summary", {})
                        if context_summary:
                            print_subsection("📋 CONTEXT SUMMARY")
                            print(
                                f"   • RAG chunks: {context_summary.get('rag_chunks', 0)}")
                            print(
                                f"   • Web results: {context_summary.get('web_results', 0)}")
                            print(
                                f"   • Attachments: {context_summary.get('attachments', 0)}")

                        # Citations
                        citations = metadata.get("citations", [])
                        if citations:
                            print_subsection("📚 CITATIONS")
                            print(f"   • Total citations: {len(citations)}")
                            for i, citation in enumerate(citations):
                                print(f"   {i+1}. {citation}")

                        return {"status": "success", "data": data, "request_time": request_time}

                    else:
                        error = result.get("error", "Unknown error")
                        print(f"   • Error: {error}")
                        return {"status": "error", "error": error, "request_time": request_time}

                else:
                    error_text = await response.text()
                    print(f"   • HTTP Error {response.status}: {error_text}")
                    return {"status": "http_error", "error": f"HTTP {response.status}: {error_text}", "request_time": request_time}

    except Exception as e:
        request_time = time.time() - start_time
        print(f"   • Exception: {str(e)}")
        return {"status": "exception", "error": str(e), "request_time": request_time}


async def run_enhanced_multi_agent_tests():
    """Run enhanced multi-agent tests with detailed service validation"""

    print_section("🚀 ENHANCED MULTI-AGENT SERVICE VALIDATION", "=", 80)

    # Test cases
    test_cases = [
        {
            "name": "Simple Introduction Query",
            "request": {
                "messages": [
                    {"role": "user", "content": "Hello! Can you introduce yourself and tell me what you can help me with?"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False,
                "enable_citations": False,
                "completion_type": "system"
            }
        },
        {
            "name": "Knowledge Base Query with Empty Context",
            "request": {
                "messages": [
                    {"role": "user", "content": "What can you tell me about my research notes on artificial intelligence?"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False,
                "note_ids": [],
                "conversation_ids": [],
                "enable_citations": True,
                "completion_type": "system"
            }
        },
        {
            "name": "Current Events Query (Should Trigger Web Search)",
            "request": {
                "messages": [
                    {"role": "user", "content": "What are the latest developments in AI technology this week?"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False,
                "enable_citations": True,
                "completion_type": "system"
            }
        },
        {
            "name": "Knowledge Base Query with Specific IDs",
            "request": {
                "messages": [
                    {"role": "user", "content": "Summarize the key points from my notes about machine learning algorithms"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False,
                "note_ids": [1, 2, 3],
                "conversation_ids": [10],
                "enable_citations": True,
                "completion_type": "system"
            }
        },
        {
            "name": "Streaming Response Test",
            "request": {
                "messages": [
                    {"role": "user",
                        "content": "Explain the benefits of using AI in education"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": True,
                "enable_citations": False,
                "completion_type": "system"
            }
        }
    ]

    results = {}

    for i, test_case in enumerate(test_cases, 1):
        print_section(
            f"TEST {i}/{len(test_cases)}: {test_case['name']}", "=", 80)

        result = await run_enhanced_test(test_case["name"], test_case["request"])
        results[test_case['name']] = result

        # Brief pause between tests
        await asyncio.sleep(1)

    # Final summary
    print_section("📊 FINAL TEST SUMMARY", "=", 80)

    total_tests = len(results)
    successful_tests = sum(1 for result in results.values()
                           if result.get("status") == "success")

    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")

    print(f"\n📋 DETAILED RESULTS:")
    for test_name, result in results.items():
        status_icon = "✅" if result.get("status") == "success" else "❌"
        request_time = result.get("request_time", 0)
        print(
            f"{status_icon} {test_name}: {result.get('status')} ({request_time:.2f}s)")
        if result.get("status") != "success":
            print(f"   Error: {result.get('error', 'Unknown')}")

    return results


async def test_server_connection():
    """Test if the server is running"""
    try:
        async with aiohttp.ClientSession() as session:
            test_payload = {
                "messages": [{"role": "user", "content": "test"}],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False
            }
            async with session.post(
                MULTI_AGENT_ENDPOINT,
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status in [200, 400, 500]:
                    return True
                return False
    except Exception:
        return False

if __name__ == "__main__":
    async def main():
        # Check server connection first
        print("🔍 Checking server connection...")
        if not await test_server_connection():
            print("❌ Cannot connect to ML server. Please start the server first.")
            print(
                "   Command: cd YouWoAI-ML-Server && source youwo-ml-venv/bin/activate && python src/main.py")
            sys.exit(1)

        print("✅ Server is available")

        # Run enhanced tests
        await run_enhanced_multi_agent_tests()

    # Run the async main function
    asyncio.run(main())
