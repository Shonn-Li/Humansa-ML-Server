#!/usr/bin/env python3
"""
Comprehensive Multi-Agent Test Suite using Real Test Environment
Tests all agents with actual database, files, and API calls
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx
import sys
from pathlib import Path

# Test configuration
TEST_USER_ID = 10001  # test_Shonn Li from our test environment
ML_SERVER_URL = "http://localhost:5002"
MULTI_AGENT_ENDPOINT = f"{ML_SERVER_URL}/v1/multi-agent/response"

# Test attachments (ML-related files)
TEST_ATTACHMENTS = {
    "pdfs": [
        "https://arxiv.org/pdf/2505.18499.pdf",  # G1 paper
        "https://arxiv.org/pdf/2311.18703.pdf",  # PARL paper
        "https://arxiv.org/pdf/2505.06319.pdf"   # Game theory paper
    ],
    "images": [
        "https://arxiv.org/html/2407.09124v1/x1.png",
        "https://arxiv.org/html/2402.12479v1/x1.png",
        "https://learn2learn.net/assets/img/examples/cheetah_fwdbwd_rewards.png",
        "https://www.scribbr.co.uk/wp-content/uploads/2023/08/the-general-framework-of-reinforcement-learning.webp"
    ]
}

class AgentTestResult:
    """Store test results for each test case"""
    def __init__(self, test_name: str, query: str):
        self.test_name = test_name
        self.query = query
        self.attachments = []
        self.expected_agents = []
        self.actual_agents = []
        self.agent_outputs = {}
        self.final_response = ""
        self.citations = []
        self.status = "PENDING"
        self.notes = []
        self.start_time = None
        self.end_time = None
        self.error = None

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "query": self.query,
            "attachments": self.attachments,
            "expected_agents": self.expected_agents,
            "actual_agents": self.actual_agents,
            "agent_outputs": self.agent_outputs,
            "final_response": self.final_response[:500] + "..." if len(self.final_response) > 500 else self.final_response,
            "citations": self.citations,
            "status": self.status,
            "duration": f"{self.end_time - self.start_time:.2f}s" if self.start_time and self.end_time else None,
            "notes": self.notes,
            "error": str(self.error) if self.error else None
        }

class MultiAgentTester:
    def __init__(self):
        self.results = []
        self.client = httpx.AsyncClient(timeout=60.0)

    async def call_multi_agent_api(self, query: str, attachments: List[str] = None, stream: bool = False) -> Dict:
        """Call the multi-agent API endpoint"""
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": TEST_USER_ID,
            "model": "gpt-4.1-nano",
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 4000,
            "enable_citations": True,
            "attachments": attachments or []
        }

        try:
            if stream:
                # Handle streaming response
                response_data = {
                    "agents_triggered": [],
                    "agent_outputs": {},
                    "final_response": "",
                    "citations": [],
                    "events": []
                }
                
                async with self.client.stream('POST', MULTI_AGENT_ENDPOINT, json=request_data) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            event_data = line[6:]
                            if event_data == "[DONE]":
                                break
                            try:
                                event = json.loads(event_data)
                                response_data["events"].append(event)
                                
                                # Parse event types
                                event_type = event.get("type", "")
                                
                                # Detect agents from reasoning text
                                if event_type == "response.reasoning_text.done":
                                    text = event.get("text", "")
                                    if "routed to agents:" in text:
                                        agents_part = text.split("routed to agents:")[1].strip()
                                        agents = [a.strip() for a in agents_part.split(",")]
                                        for agent in agents:
                                            if agent not in response_data["agents_triggered"]:
                                                response_data["agents_triggered"].append(agent)
                                    # Always add router if we have reasoning
                                    if "router" not in response_data["agents_triggered"]:
                                        response_data["agents_triggered"].append("router")
                                
                                # Detect agents from event types
                                if "web_search_call" in event_type:
                                    if "web_search" not in response_data["agents_triggered"]:
                                        response_data["agents_triggered"].append("web_search")
                                
                                if "file_search_call" in event_type:
                                    if "rag" not in response_data["agents_triggered"]:
                                        response_data["agents_triggered"].append("rag")
                                
                                # Always add response agent if we have output text
                                if event_type == "response.output_text.delta" and "response" not in response_data["agents_triggered"]:
                                    response_data["agents_triggered"].append("response")
                                
                                # Add citation agent if citations present
                                if event_type == "response.citations" and event.get("citations"):
                                    if "citation" not in response_data["agents_triggered"]:
                                        response_data["agents_triggered"].append("citation")
                                        
                                elif event.get("type") == "response.output_item.added":
                                    item = event.get("item", {})
                                    if item.get("type") == "reasoning":
                                        response_data["agent_outputs"]["reasoning"] = item.get("content", "")
                                    elif item.get("type") == "web_search_call":
                                        response_data["agent_outputs"]["web_search"] = item.get("queries", [])
                                    elif item.get("type") == "file_search_call":
                                        response_data["agent_outputs"]["file_search"] = item.get("query", "")
                                        
                                elif event.get("type") == "response.output_text.delta":
                                    response_data["final_response"] += event.get("delta", "")
                                    
                                elif event.get("type") == "response.citations":
                                    response_data["citations"] = event.get("citations", [])
                                    
                            except json.JSONDecodeError:
                                print(f"Failed to parse event: {event_data}")
                                
                return response_data
            else:
                # Handle non-streaming response
                response = await self.client.post(MULTI_AGENT_ENDPOINT, json=request_data)
                response.raise_for_status()
                data = response.json()
                
                # For non-streaming, we need to infer agents from the response
                response_data = {
                    "agents_triggered": [],
                    "agent_outputs": {},
                    "final_response": "",
                    "citations": [],
                }
                
                # Extract final response
                if "choices" in data and data["choices"]:
                    response_data["final_response"] = data["choices"][0].get("message", {}).get("content", "")
                
                # Infer agents based on metadata
                metadata = data.get("metadata", {})
                agents = metadata.get("agents_triggered", [])
                response_data["agents_triggered"] = agents
                
                # If no agents in metadata, infer from response content
                if not agents and response_data["final_response"]:
                    # Always assume router and response for any successful response
                    response_data["agents_triggered"] = ["router", "response"]
                
                return response_data
                
        except Exception as e:
            return {"error": str(e), "agents_triggered": [], "final_response": ""}

    async def run_test_case(self, test_name: str, query: str, expected_agents: List[str], 
                           attachments: List[str] = None, stream: bool = True) -> AgentTestResult:
        """Run a single test case"""
        result = AgentTestResult(test_name, query)
        result.expected_agents = expected_agents
        result.attachments = attachments or []
        result.start_time = time.time()
        
        print(f"\n{'='*80}")
        print(f"Running Test: {test_name}")
        print(f"Query: {query}")
        if attachments:
            print(f"Attachments: {attachments}")
        print(f"Expected Agents: {expected_agents}")
        
        try:
            # Call the API
            response = await self.call_multi_agent_api(query, attachments, stream)
            
            if "error" in response:
                result.error = response["error"]
                result.status = "FAILED"
                result.notes.append(f"API Error: {response['error']}")
            else:
                # Extract results
                result.actual_agents = response.get("agents_triggered", [])
                result.agent_outputs = response.get("agent_outputs", {})
                result.final_response = response.get("final_response", "")
                result.citations = response.get("citations", [])
                
                # Validate results
                if set(expected_agents).issubset(set(result.actual_agents)):
                    result.status = "PASSED"
                else:
                    result.status = "FAILED"
                    missing_agents = set(expected_agents) - set(result.actual_agents)
                    result.notes.append(f"Missing expected agents: {missing_agents}")
                    
                # Additional validation
                if not result.final_response:
                    result.status = "FAILED"
                    result.notes.append("No final response generated")
                    
        except Exception as e:
            result.error = e
            result.status = "FAILED"
            result.notes.append(f"Exception: {str(e)}")
            
        result.end_time = time.time()
        
        # Print results
        print(f"\nActual Agents Triggered: {result.actual_agents}")
        print(f"Status: {result.status}")
        if result.notes:
            print(f"Notes: {result.notes}")
        print(f"Response Length: {len(result.final_response)} chars")
        print(f"Citations: {len(result.citations)}")
        
        self.results.append(result)
        return result

    async def run_all_tests(self):
        """Run all test cases"""
        print(f"\nStarting Multi-Agent Test Suite")
        print(f"ML Server: {ML_SERVER_URL}")
        print(f"Test User ID: {TEST_USER_ID}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # RAG Agent Tests
        print("\n\n### RAG AGENT TESTS ###")
        
        await self.run_test_case(
            "RAG_Research_Paper_Query",
            "What is the main contribution of the PARL paper?",
            ["router", "rag", "response", "citation"]
        )
        
        await self.run_test_case(
            "RAG_Cross_Note_Synthesis",
            "Compare the reinforcement learning approaches in PARL and G1",
            ["router", "rag", "response", "citation"]
        )
        
        await self.run_test_case(
            "RAG_Business_Content",
            "How did Zepto achieve 10-minute delivery?",
            ["router", "rag", "response", "citation"]
        )
        
        await self.run_test_case(
            "RAG_Chinese_Content",
            "由我AI的主要功能是什么？",
            ["router", "rag", "response", "citation"]
        )
        
        await self.run_test_case(
            "RAG_Conversation_History",
            "What did we discuss about predictability in RL?",
            ["router", "rag", "response", "citation"]
        )
        
        # Web Search Agent Tests
        print("\n\n### WEB SEARCH AGENT TESTS ###")
        
        await self.run_test_case(
            "WebSearch_Current_Events",
            "What are the latest developments in AI regulation in 2024?",
            ["router", "web_search", "response", "citation"]
        )
        
        await self.run_test_case(
            "WebSearch_Recent_News",
            "What happened with OpenAI this week?",
            ["router", "web_search", "response", "citation"]
        )
        
        # Attachment Agent Tests
        print("\n\n### ATTACHMENT AGENT TESTS ###")
        
        await self.run_test_case(
            "Attachment_PDF_Analysis",
            "Summarize the key findings in this paper",
            ["router", "attachment", "response", "citation"],
            [TEST_ATTACHMENTS["pdfs"][0]]  # G1 paper
        )
        
        await self.run_test_case(
            "Attachment_Image_Understanding",
            "Explain the reinforcement learning process shown in this diagram",
            ["router", "attachment", "response", "citation"],
            [TEST_ATTACHMENTS["images"][0]]
        )
        
        await self.run_test_case(
            "Attachment_Multiple_Files",
            "Compare the approaches in these papers and relate them to the diagram",
            ["router", "attachment", "response", "citation"],
            TEST_ATTACHMENTS["pdfs"][:2] + [TEST_ATTACHMENTS["images"][0]]
        )
        
        # Code Interpreter Tests
        print("\n\n### CODE INTERPRETER TESTS ###")
        
        await self.run_test_case(
            "Code_Data_Analysis",
            "Write Python code to calculate the average number of embeddings per note if I have 9 notes and 190 total embeddings",
            ["router", "code_interpreter", "response", "citation"]
        )
        
        await self.run_test_case(
            "Code_Visualization",
            "Create a matplotlib bar chart showing these note counts: PDF=3, YouTube=4, Document=1, Audio=1",
            ["router", "code_interpreter", "response", "citation"]
        )
        
        await self.run_test_case(
            "Code_Mathematical",
            "Solve the optimization problem: minimize x^2 + y^2 subject to x + y = 10",
            ["router", "code_interpreter", "response", "citation"]
        )
        
        # Mixed Agent Tests
        print("\n\n### MIXED AGENT TESTS ###")
        
        await self.run_test_case(
            "Mixed_RAG_Code",
            "Analyze the performance metrics mentioned in the G1 paper and create a comparison chart",
            ["router", "rag", "code_interpreter", "response", "citation"]
        )
        
        await self.run_test_case(
            "Mixed_RAG_Web",
            "How do the startup growth strategies in my notes compare to current AI startup trends?",
            ["router", "rag", "web_search", "response", "citation"]
        )
        
        await self.run_test_case(
            "Mixed_Attachment_RAG",
            "How does this paper's approach differ from the PARL paper in my notes?",
            ["router", "attachment", "rag", "response", "citation"],
            [TEST_ATTACHMENTS["pdfs"][1]]  # PARL paper as attachment
        )
        
        # Error Scenario Tests
        print("\n\n### ERROR SCENARIO TESTS ###")
        
        await self.run_test_case(
            "Error_Invalid_Attachment",
            "Analyze this file",
            ["router", "attachment", "response"],
            ["https://invalid-url-that-does-not-exist.com/file.pdf"]
        )
        
        await self.run_test_case(
            "Error_Empty_Query",
            "",
            ["router", "response"]
        )
        
        # Generate summary report
        self.generate_summary_report()

    def generate_summary_report(self):
        """Generate a summary report of all test results"""
        print(f"\n\n{'='*80}")
        print("TEST SUMMARY REPORT")
        print(f"{'='*80}")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == "PASSED")
        failed_tests = sum(1 for r in self.results if r.status == "FAILED")
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        # Agent activation statistics
        agent_stats = {}
        for result in self.results:
            for agent in result.actual_agents:
                agent_stats[agent] = agent_stats.get(agent, 0) + 1
                
        print(f"\nAgent Activation Statistics:")
        for agent, count in sorted(agent_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent}: {count} times ({count/total_tests*100:.1f}%)")
        
        # Failed tests details
        if failed_tests > 0:
            print(f"\nFailed Tests Details:")
            for result in self.results:
                if result.status == "FAILED":
                    print(f"\n  Test: {result.test_name}")
                    print(f"  Query: {result.query}")
                    print(f"  Expected Agents: {result.expected_agents}")
                    print(f"  Actual Agents: {result.actual_agents}")
                    if result.error:
                        print(f"  Error: {result.error}")
                    if result.notes:
                        print(f"  Notes: {result.notes}")
        
        # Save detailed results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                "test_run": {
                    "timestamp": datetime.now().isoformat(),
                    "ml_server": ML_SERVER_URL,
                    "test_user_id": TEST_USER_ID,
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests
                },
                "results": [r.to_dict() for r in self.results],
                "agent_statistics": agent_stats
            }, f, indent=2)
            
        print(f"\nDetailed results saved to: {results_file}")

async def main():
    """Main test runner"""
    tester = MultiAgentTester()
    
    try:
        # Check if ML server is running
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ML_SERVER_URL}/health")
            if response.status_code != 200:
                print(f"ML Server not responding at {ML_SERVER_URL}")
                return
                
        # Run all tests
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed: {str(e)}")
    finally:
        await tester.client.aclose()

if __name__ == "__main__":
    print("Multi-Agent Test Suite - Real Environment")
    print("Make sure:")
    print("1. ML Server is running on port 5001")
    print("2. ML Server is configured to use test database (port 5454)")
    print("3. You have internet access for web search and attachment downloads")
    
    print("\nStarting tests automatically...")
    
    asyncio.run(main())