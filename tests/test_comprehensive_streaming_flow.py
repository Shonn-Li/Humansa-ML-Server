#!/usr/bin/env python3
"""
Comprehensive Streaming Flow Test Suite

This test suite shows detailed streaming event flow for each test case,
helping to understand:
1. What agents are triggered
2. The order of events
3. Citation annotations with real positions
4. Iterative agent capabilities
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class StreamingEvent:
    """Represents a single streaming event"""
    sequence: int
    type: str
    data: Dict[str, Any]
    timestamp: float
    
    def summary(self) -> str:
        """Get a human-readable summary of the event"""
        event_type = self.type
        
        # Extract key information based on event type
        if event_type == "response.output_item.added":
            item = self.data.get("item", {})
            item_type = item.get("type", "unknown")
            item_id = item.get("id", "N/A")
            return f"➕ Output item added: {item_type} (ID: {item_id[:12]}...)"
            
        elif event_type == "response.reasoning_text.delta":
            text = self.data.get("delta", "")[:50]
            return f"🧠 Reasoning: {text}..."
            
        elif event_type == "response.output_text.delta":
            text = self.data.get("delta", "")[:50]
            return f"📝 Response text: {text}..."
            
        elif event_type == "response.output_text.annotation.added":
            ann = self.data.get("annotation", {})
            return f"📌 Citation added: [{ann.get('text', 'N/A')}] at {ann.get('start_index', 0)}-{ann.get('end_index', 0)}"
            
        elif event_type == "response.function_tool_call.created":
            return f"🔧 Tool call created"
            
        elif event_type == "response.web_search_call.created":
            return f"🔍 Web search initiated"
            
        elif event_type == "response.file_search_call.created":
            return f"📁 File search initiated"
            
        elif event_type == "response.done":
            return f"✅ Response completed"
            
        else:
            return f"📦 {event_type}"


@dataclass
class TestResult:
    """Result of a single test case"""
    name: str
    description: str
    request: Dict[str, Any]
    events: List[StreamingEvent] = field(default_factory=list)
    response_text: str = ""
    agents_triggered: List[str] = field(default_factory=list)
    citations: List[Dict] = field(default_factory=list)
    iterations: int = 1
    error: Optional[str] = None
    duration: float = 0.0
    
    def print_flow(self):
        """Print the detailed event flow"""
        print(f"\n{'='*80}")
        print(f"TEST: {self.name}")
        print(f"{'='*80}")
        print(f"Description: {self.description}")
        print(f"Duration: {self.duration:.2f}s")
        print(f"Total Events: {len(self.events)}")
        print(f"Agents Triggered: {', '.join(self.agents_triggered) if self.agents_triggered else 'None'}")
        print(f"Iterations: {self.iterations}")
        
        if self.error:
            print(f"❌ ERROR: {self.error}")
            return
            
        # Group events by phase
        phases = defaultdict(list)
        current_phase = "initialization"
        
        for event in self.events:
            if "reasoning" in event.type:
                current_phase = "reasoning"
            elif "tool_call" in event.type or "search_call" in event.type:
                current_phase = "tool_execution"
            elif "output_text" in event.type and "annotation" not in event.type:
                current_phase = "response_generation"
            elif "annotation" in event.type:
                current_phase = "citation_annotation"
            elif "usage" in event.type or "completed" in event.type or "done" in event.type:
                current_phase = "completion"
                
            phases[current_phase].append(event)
        
        # Print events by phase
        for phase_name in ["initialization", "reasoning", "tool_execution", "response_generation", "citation_annotation", "completion"]:
            if phase_name in phases:
                print(f"\n📍 Phase: {phase_name.upper()}")
                print("-" * 60)
                for event in phases[phase_name]:
                    print(f"  [{event.sequence:3d}] {event.summary()}")
        
        # Print final response
        print(f"\n📄 FINAL RESPONSE:")
        print("-" * 60)
        print(self.response_text[:500] + "..." if len(self.response_text) > 500 else self.response_text)
        
        # Print citations if any
        if self.citations:
            print(f"\n📚 CITATIONS:")
            print("-" * 60)
            for citation in self.citations:
                print(f"  [{citation.get('text', 'N/A')}] {citation.get('title', 'N/A')}")
                print(f"       Position: {citation.get('start_index', 0)}-{citation.get('end_index', 0)}")
                print(f"       URL: {citation.get('url', 'N/A')}")


class ComprehensiveStreamingTester:
    """Test runner for comprehensive streaming tests"""
    
    def __init__(self, base_url: str = "http://localhost:5002"):
        self.base_url = base_url
        self.client = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
            
    async def run_streaming_test(self, name: str, description: str, request: Dict[str, Any]) -> TestResult:
        """Run a single streaming test and capture all events"""
        result = TestResult(name=name, description=description, request=request)
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Ensure streaming is enabled
            request["stream"] = True
            
            # Track state
            response_chunks = []
            agents_detected = set()
            
            async with self.client.stream("POST", f"{self.base_url}/v1/multi-agent/response", json=request) as response:
                sequence = 0
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                            
                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get("type", "")
                            
                            # Create event record
                            event = StreamingEvent(
                                sequence=sequence,
                                type=event_type,
                                data=event_data,
                                timestamp=asyncio.get_event_loop().time() - start_time
                            )
                            result.events.append(event)
                            sequence += 1
                            
                            # Extract information from events
                            self._process_event(event, response_chunks, agents_detected, result)
                            
                        except json.JSONDecodeError:
                            pass
            
            result.response_text = "".join(response_chunks)
            result.agents_triggered = sorted(list(agents_detected))
            result.duration = asyncio.get_event_loop().time() - start_time
            
        except Exception as e:
            result.error = str(e)
            result.duration = asyncio.get_event_loop().time() - start_time
            
        return result
    
    def _process_event(self, event: StreamingEvent, response_chunks: List[str], 
                      agents_detected: set, result: TestResult):
        """Process a single event to extract information"""
        event_type = event.type
        data = event.data
        
        # Collect response text
        if event_type == "response.output_text.delta":
            response_chunks.append(data.get("delta", ""))
            
        # Detect agents from reasoning
        if event_type == "response.reasoning_text.delta":
            text = data.get("delta", "")
            if "routed to agents:" in text:
                # Extract agent list
                agent_part = text.split("routed to agents:")[1]
                for agent in agent_part.split(","):
                    agent_name = agent.strip().lower()
                    if agent_name:
                        agents_detected.add(agent_name)
                        
        # Detect agents from item IDs
        if "item" in data:
            item_id = data["item"].get("id", "")
            if item_id.startswith("router_"):
                agents_detected.add("router")
            elif item_id.startswith("rag_"):
                agents_detected.add("rag")
            elif item_id.startswith("ws_"):
                agents_detected.add("web_search")
            elif item_id.startswith("attachment_"):
                agents_detected.add("attachment")
            elif item_id.startswith("cit_"):
                agents_detected.add("citation")
                
        # Collect citations
        if event_type == "response.output_text.annotation.added":
            annotation = data.get("annotation", {})
            result.citations.append(annotation)
            
        # Track iterations from metadata
        if event_type == "response.usage" and "metadata" in data:
            metadata = data.get("metadata", {})
            result.iterations = metadata.get("iterations", 1)
    
    async def run_test_suite(self):
        """Run comprehensive test suite"""
        print("="*80)
        print("COMPREHENSIVE STREAMING FLOW TEST SUITE")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Define test cases
        test_cases = [
            # Basic tests
            {
                "name": "Simple Query",
                "description": "Basic query without any special requirements",
                "request": {
                    "messages": [{"role": "user", "content": "What is machine learning?"}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano"
                }
            },
            
            # Citation tests
            {
                "name": "Web Search with Citations",
                "description": "Query that triggers web search and citation formatting",
                "request": {
                    "messages": [{"role": "user", "content": "What are the latest AI developments in 2024? Include sources."}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_citations": True
                }
            },
            
            # RAG tests
            {
                "name": "Knowledge Base Query",
                "description": "Query that searches user's knowledge base",
                "request": {
                    "messages": [{"role": "user", "content": "What do my notes say about PARL? Include citations."}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_citations": True
                }
            },
            
            # Attachment tests
            {
                "name": "PDF Attachment Analysis",
                "description": "Analyze attached PDF with citations",
                "request": {
                    "messages": [{"role": "user", "content": "Summarize this paper and cite key findings"}],
                    "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_citations": True
                }
            },
            
            # Multi-attachment test
            {
                "name": "Multiple Attachments",
                "description": "Compare multiple attached documents",
                "request": {
                    "messages": [{"role": "user", "content": "Compare these papers and highlight their differences"}],
                    "attachments": [
                        "https://arxiv.org/pdf/2505.18499.pdf",
                        "https://arxiv.org/pdf/2311.10122.pdf"
                    ],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_citations": True
                }
            },
            
            # Iterative reasoning test
            {
                "name": "Complex Iterative Query",
                "description": "Query requiring multiple reasoning steps",
                "request": {
                    "messages": [{"role": "user", "content": "Analyze the pros and cons of different machine learning approaches for time series forecasting, then recommend the best approach for financial data with explanations."}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_iterations": True,
                    "enable_citations": True
                }
            },
            
            # Mixed agent test
            {
                "name": "Multi-Agent Collaboration",
                "description": "Query requiring multiple agents working together",
                "request": {
                    "messages": [{"role": "user", "content": "Search for recent papers on transformer architectures, compare with my notes on attention mechanisms, and summarize the key innovations."}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_iterations": True,
                    "enable_citations": True
                }
            },
            
            # Edge cases
            {
                "name": "Empty Query Edge Case",
                "description": "Handling empty or minimal input",
                "request": {
                    "messages": [{"role": "user", "content": ""}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano"
                }
            },
            
            {
                "name": "Citation Without Sources",
                "description": "Request citations when no external sources available",
                "request": {
                    "messages": [{"role": "user", "content": "Explain recursion with citations"}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_citations": True
                }
            },
            
            # Code interpreter test (if available)
            {
                "name": "Code Execution Request",
                "description": "Query requiring code execution",
                "request": {
                    "messages": [{"role": "user", "content": "Calculate the fibonacci sequence up to 20 terms and plot it"}],
                    "user_id": 10001,
                    "model": "gpt-4.1-nano",
                    "enable_code_interpreter": True
                }
            }
        ]
        
        # Run all tests
        results = []
        for test_case in test_cases:
            print(f"\n🔄 Running test: {test_case['name']}...")
            result = await self.run_streaming_test(
                test_case["name"],
                test_case["description"],
                test_case["request"]
            )
            results.append(result)
            
            # Brief summary
            if result.error:
                print(f"   ❌ Failed: {result.error}")
            else:
                print(f"   ✅ Success: {len(result.events)} events, {len(result.agents_triggered)} agents")
        
        # Print detailed results
        print("\n" + "="*80)
        print("DETAILED TEST RESULTS")
        print("="*80)
        
        for result in results:
            result.print_flow()
        
        # Summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        
        successful = sum(1 for r in results if not r.error)
        print(f"Total Tests: {len(results)}")
        print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
        print(f"Failed: {len(results) - successful}")
        
        # Agent usage statistics
        all_agents = set()
        for result in results:
            all_agents.update(result.agents_triggered)
        
        print(f"\nAgents Used: {', '.join(sorted(all_agents))}")
        
        # Event type statistics
        event_types = defaultdict(int)
        for result in results:
            for event in result.events:
                event_types[event.type] += 1
        
        print(f"\nTop Event Types:")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {event_type}: {count}")
        
        # Citation statistics
        total_citations = sum(len(r.citations) for r in results)
        tests_with_citations = sum(1 for r in results if r.citations)
        print(f"\nCitation Statistics:")
        print(f"  Total Citations: {total_citations}")
        print(f"  Tests with Citations: {tests_with_citations}")
        
        # Iteration statistics
        multi_iteration_tests = sum(1 for r in results if r.iterations > 1)
        print(f"\nIteration Statistics:")
        print(f"  Tests with Multiple Iterations: {multi_iteration_tests}")
        if multi_iteration_tests > 0:
            avg_iterations = sum(r.iterations for r in results if r.iterations > 1) / multi_iteration_tests
            print(f"  Average Iterations (when >1): {avg_iterations:.1f}")


async def main():
    """Main entry point"""
    async with ComprehensiveStreamingTester() as tester:
        await tester.run_test_suite()


if __name__ == "__main__":
    asyncio.run(main())