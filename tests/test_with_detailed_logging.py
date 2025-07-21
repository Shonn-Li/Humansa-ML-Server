#!/usr/bin/env python3
"""
Enhanced test suite with detailed logging for multi-agent system
Saves structured logs for each test case with full output item tracking
"""

import asyncio
import httpx
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import traceback

class DetailedAgentTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.base_url = "http://localhost:5002/v1/multi-agent/response"
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_base_dir = Path(f"test_logs/{self.timestamp}")
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        
    def save_test_log(self, test_name: str, log_data: Dict):
        """Save detailed log for a test case"""
        safe_name = test_name.replace(':', '_').replace(' ', '_').replace('/', '_')
        log_file = self.log_base_dir / f"{safe_name}.json"
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
            
        # Also create human-readable version
        readable_file = self.log_base_dir / f"{safe_name}_readable.txt"
        with open(readable_file, 'w') as f:
            self._write_readable_log(f, log_data)
            
    def _write_readable_log(self, f, log_data: Dict):
        """Write human-readable version of log"""
        f.write(f"TEST: {log_data['test_name']}\n")
        f.write(f"TIME: {log_data['timestamp']}\n")
        f.write(f"STATUS: {log_data['status']}\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"QUERY: {log_data['query']}\n")
        if log_data.get('attachments'):
            f.write(f"ATTACHMENTS: {log_data['attachments']}\n")
        f.write("\n")
        
        # Output items flow
        f.write("OUTPUT ITEMS FLOW:\n")
        f.write("-"*80 + "\n")
        for item in log_data.get('output_items', []):
            f.write(f"\n{item['timestamp']} - {item['type']} (ID: {item.get('id', 'N/A')})\n")
            
            if item['type'] == 'reasoning':
                f.write(f"  Agent: {item.get('agent', 'unknown')}\n")
                f.write(f"  Content: {item.get('content', '')[:200]}...\n")
                
            elif item['type'] == 'tool_call':
                f.write(f"  Tool: {item.get('tool_name', 'unknown')}\n")
                f.write(f"  Status: {item.get('status', 'unknown')}\n")
                
            elif item['type'] == 'message':
                f.write(f"  Content preview: {item.get('content', '')[:200]}...\n")
                
            elif item['type'] == 'citation':
                f.write(f"  Citations added: {item.get('citation_count', 0)}\n")
                
        # Agent summary
        f.write("\n\nAGENT EXECUTION SUMMARY:\n")
        f.write("-"*80 + "\n")
        for agent, info in log_data.get('agents_executed', {}).items():
            f.write(f"- {agent}: {info['status']} (took {info.get('duration', 'N/A')}s)\n")
            
        # Final response
        f.write("\n\nFINAL RESPONSE:\n")
        f.write("-"*80 + "\n")
        f.write(log_data.get('final_response', 'No response')[:1000])
        if len(log_data.get('final_response', '')) > 1000:
            f.write("\n... [truncated]")
            
        # Citations
        if log_data.get('citations'):
            f.write("\n\nCITATIONS:\n")
            f.write("-"*80 + "\n")
            for i, citation in enumerate(log_data.get('citations', []), 1):
                f.write(f"[{i}] {citation}\n")
                
        # Errors
        if log_data.get('errors'):
            f.write("\n\nERRORS:\n")
            f.write("-"*80 + "\n")
            for error in log_data['errors']:
                f.write(f"- {error}\n")
        
    async def test_query(self, name: str, query: str, attachments: List[str] = None, 
                        stream: bool = True) -> Dict:
        """Test a single query with detailed logging"""
        
        # Initialize log data
        log_data = {
            "test_name": name,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "attachments": attachments or [],
            "stream": stream,
            "output_items": [],
            "agents_executed": {},
            "status": "running",
            "errors": [],
            "final_response": "",
            "citations": [],
            "raw_events": []  # Store all raw events for debugging
        }
        
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": stream,
            "enable_citations": True,
            "attachments": attachments or []
        }
        
        try:
            if stream:
                await self._test_streaming(request_data, log_data)
            else:
                await self._test_non_streaming(request_data, log_data)
                
            log_data["status"] = "success" if log_data["final_response"] else "failed"
            
        except Exception as e:
            log_data["status"] = "error"
            log_data["errors"].append(f"Exception: {str(e)}")
            log_data["errors"].append(traceback.format_exc())
            
        # Save the log
        self.save_test_log(name, log_data)
        
        # Return summary
        return {
            "name": name,
            "status": log_data["status"],
            "agents": list(log_data["agents_executed"].keys()),
            "has_citations": len(log_data["citations"]) > 0,
            "response_length": len(log_data["final_response"]),
            "errors": log_data["errors"]
        }
        
    async def _test_streaming(self, request_data: Dict, log_data: Dict):
        """Test streaming response with detailed event tracking"""
        
        # Print key events to console for debugging
        print(f"  🔄 Starting streaming request...")
        
        async with self.client.stream('POST', self.base_url, json=request_data) as response:
            event_count = 0
            current_agents = {}
            key_events_shown = 0
            
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data == '[DONE]':
                        print(f"  ✅ Stream completed ({event_count} events)")
                        break
                        
                    try:
                        event = json.loads(event_data)
                        event_count += 1
                        log_data["raw_events"].append(event)
                        
                        event_type = event.get('type', '')
                        
                        # Print key events to console (limit to avoid spam)
                        if key_events_shown < 10 and any(k in event_type for k in ['output_item.added', 'reasoning', 'tool_call', 'attachment']):
                            if 'output_item.added' in event_type:
                                item = event.get('item', {})
                                print(f"  📦 Output item: {item.get('type', 'unknown')} (ID: {item.get('id', 'N/A')[:12]}...)")
                            elif 'reasoning' in event_type and 'delta' in event:
                                delta = event.get('delta', '')[:50]
                                if delta:
                                    print(f"  💭 Reasoning: {delta}...")
                            elif 'tool_call' in event_type:
                                print(f"  🔧 Tool call: {event_type}")
                            key_events_shown += 1
                        
                        # Track output items
                        if 'output_item.added' in event_type:
                            item = event.get('item', {})
                            output_item = {
                                "timestamp": datetime.now().isoformat(),
                                "type": item.get('type', 'unknown'),
                                "id": item.get('id', ''),
                                "sequence": event.get('sequence_number', event_count)
                            }
                            
                            # Detect agent from item ID
                            item_id = item.get('id', '')
                            if item_id.startswith('router_'):
                                output_item['agent'] = 'router'
                                current_agents['router'] = {"status": "started", "start_time": datetime.now()}
                            elif item_id.startswith('ws_'):
                                output_item['agent'] = 'web_search'
                                current_agents['web_search'] = {"status": "started", "start_time": datetime.now()}
                            elif item_id.startswith('rag_'):
                                output_item['agent'] = 'rag'
                                current_agents['rag'] = {"status": "started", "start_time": datetime.now()}
                            elif item_id.startswith('attachment_'):
                                output_item['agent'] = 'attachment'
                                current_agents['attachment'] = {"status": "started", "start_time": datetime.now()}
                            elif item_id.startswith('cit_'):
                                output_item['agent'] = 'citation'
                                current_agents['citation'] = {"status": "started", "start_time": datetime.now()}
                                
                            log_data["output_items"].append(output_item)
                            
                        # Track reasoning content
                        elif 'reasoning' in event_type:
                            if event_type == 'response.reasoning_text.delta':
                                text = event.get('delta', '')
                                # Find the last reasoning item and append content
                                for item in reversed(log_data["output_items"]):
                                    if item['type'] == 'reasoning':
                                        item['content'] = item.get('content', '') + text
                                        break
                                        
                                # Detect agents from reasoning text
                                if 'routed to agents:' in text:
                                    agent_list = text.split('routed to agents:')[1].strip()
                                    for agent in agent_list.split(','):
                                        agent_name = agent.strip()
                                        if agent_name and agent_name not in current_agents:
                                            current_agents[agent_name] = {"status": "queued", "start_time": datetime.now()}
                                            
                        # Track tool calls
                        elif 'tool_call' in event_type or 'function_call' in event_type:
                            log_data["output_items"].append({
                                "timestamp": datetime.now().isoformat(),
                                "type": "tool_call",
                                "tool_name": event.get('name', 'unknown'),
                                "status": "in_progress" if 'in_progress' in event_type else "completed"
                            })
                            
                        # Track content
                        elif event_type == 'response.output_text.delta':
                            log_data["final_response"] += event.get('delta', '')
                            
                        # Track when items are done
                        elif 'output_item.done' in event_type:
                            item = event.get('item', {})
                            item_id = item.get('id', '')
                            
                            # Mark agent as completed
                            for agent, info in current_agents.items():
                                if info["status"] == "started":
                                    if (agent == 'router' and item_id.startswith('router_')) or \
                                       (agent == 'web_search' and item_id.startswith('ws_')) or \
                                       (agent == 'rag' and item_id.startswith('rag_')) or \
                                       (agent == 'attachment' and item_id.startswith('attachment_')) or \
                                       (agent == 'citation' and item_id.startswith('cit_')):
                                        info["status"] = "completed"
                                        info["duration"] = (datetime.now() - info["start_time"]).total_seconds()
                                        
                        # Extract metadata from usage event
                        elif event_type == 'response.usage' and 'metadata' in event:
                            metadata = event['metadata']
                            if 'agent_results' in metadata:
                                for agent_key, agent_data in metadata['agent_results'].items():
                                    agent_name = agent_key.replace('_agent', '')
                                    log_data["agents_executed"][agent_name] = {
                                        "status": agent_data.get('status', 'unknown'),
                                        "data": agent_data.get('data', {})
                                    }
                                    
                    except Exception as e:
                        log_data["errors"].append(f"Event parsing error: {str(e)}")
                        
            # Copy current agents to executed agents
            for agent, info in current_agents.items():
                if agent not in log_data["agents_executed"]:
                    log_data["agents_executed"][agent] = info
                    
    async def _test_non_streaming(self, request_data: Dict, log_data: Dict):
        """Test non-streaming response"""
        response = await self.client.post(self.base_url, json=request_data)
        
        if response.status_code != 200:
            log_data["errors"].append(f"HTTP {response.status_code}: {response.text}")
            return
            
        result = response.json()
        
        # Extract response
        if 'choices' in result and result['choices']:
            log_data["final_response"] = result['choices'][0].get('message', {}).get('content', '')
            
        # Extract metadata
        if 'metadata' in result:
            metadata = result['metadata']
            
            # Extract agents
            if 'agent_results' in metadata:
                for agent_key, agent_data in metadata['agent_results'].items():
                    agent_name = agent_key.replace('_agent', '')
                    log_data["agents_executed"][agent_name] = {
                        "status": agent_data.get('status', 'unknown'),
                        "data": agent_data.get('data', {})
                    }
                    
            # Extract workflow info
            if 'workflow_time' in metadata:
                log_data["workflow_time"] = metadata['workflow_time']
                
        # Extract citations from response
        content = log_data["final_response"]
        citations = []
        
        # Look for numbered citations
        import re
        citation_pattern = r'\[(\d+)\]'
        citation_numbers = set(re.findall(citation_pattern, content))
        
        # Look for Sources or References section
        if 'Sources:' in content or 'References:' in content:
            lines = content.split('\n')
            in_sources = False
            for line in lines:
                if 'Sources:' in line or 'References:' in line:
                    in_sources = True
                    continue
                if in_sources and line.strip():
                    if line.strip().startswith('[') and ']' in line:
                        citations.append(line.strip())
                        
        log_data["citations"] = citations
        
    async def run_comprehensive_test_suite(self):
        """Run all test cases with detailed logging"""
        print("="*80)
        print("COMPREHENSIVE MULTI-AGENT TEST SUITE WITH DETAILED LOGGING")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Logs saved to: {self.log_base_dir}")
        print("="*80)
        
        # Define comprehensive test cases
        test_cases = [
            # Basic agent tests
            ("Simple Query", "What is 2+2?", None, True),
            ("Simple Query Non-Stream", "What is 2+2?", None, False),
            
            # RAG Tests
            ("RAG: Note Query Stream", "What information do I have about the PARL paper?", None, True),
            ("RAG: Note Query Non-Stream", "What information do I have about the PARL paper?", None, False),
            ("RAG with Citations", "What do my notes say about reinforcement learning? Include citations.", None, True),
            
            # Web Search Tests
            ("Web Search Stream", "What are the latest AI developments today?", None, True),
            ("Web Search Non-Stream", "What are the latest AI developments today?", None, False),
            ("Web Search with Citations", "What is machine learning? Cite sources.", None, True),
            
            # Attachment Tests (Critical for validation)
            ("Single PDF Attachment Stream", "Summarize this paper", ["https://arxiv.org/pdf/2505.18499.pdf"], True),
            ("Single PDF Attachment Non-Stream", "Summarize this paper", ["https://arxiv.org/pdf/2505.18499.pdf"], False),
            ("Multiple Attachments", "Compare these papers", 
             ["https://arxiv.org/pdf/2311.10122.pdf", "https://arxiv.org/pdf/2505.18499.pdf"], True),
            ("Image Attachment", "What's shown in this diagram?", ["https://arxiv.org/html/2407.09124v1/x1.png"], True),
            
            # Mixed Agent Tests
            ("RAG + Web Search", "How do my notes compare to current AI trends?", None, True),
            ("Attachment + Citation", "Analyze this paper and cite key points", 
             ["https://arxiv.org/pdf/2311.10122.pdf"], True),
            
            # Citation Tests
            ("Force Citations Stream", "Explain quantum computing. You must include citations [1], [2], etc.", None, True),
            ("Force Citations Non-Stream", "Explain quantum computing. You must include citations [1], [2], etc.", None, False),
        ]
        
        # Run tests
        results = []
        for test_case in test_cases:
            name = test_case[0]
            query = test_case[1]
            attachments = test_case[2]
            stream = test_case[3] if len(test_case) > 3 else True
            
            print(f"\n{'='*80}")
            print(f"TEST: {name}")
            print(f"STREAM: {stream}")
            print(f"QUERY: {query}")
            if attachments:
                print(f"ATTACHMENTS: {attachments}")
            print("-"*80)
            
            result = await self.test_query(name, query, attachments, stream)
            results.append(result)
            
            # Print summary
            print(f"STATUS: {result['status']}")
            print(f"AGENTS: {' → '.join(result['agents']) if result['agents'] else 'None detected'}")
            print(f"CITATIONS: {'Yes' if result['has_citations'] else 'No'}")
            print(f"RESPONSE LENGTH: {result['response_length']} chars")
            
            # Show response preview
            if result['response_length'] > 0:
                # Load the log to get response preview
                try:
                    log_file = self.log_base_dir / f"{name.replace(':', '_').replace(' ', '_').replace('/', '_')}.json"
                    with open(log_file, 'r') as f:
                        log_data = json.load(f)
                        response_preview = log_data.get('final_response', '')[:200]
                        if response_preview:
                            print(f"RESPONSE PREVIEW: {response_preview}...")
                except:
                    pass
            
            if result['errors']:
                print(f"ERRORS: {len(result['errors'])} errors")
                for error in result['errors']:  # Show all errors for debugging
                    print(f"  - {error}")
                    
            # Small delay between tests
            await asyncio.sleep(2)
            
        # Summary
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print("="*80)
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        total_count = len(results)
        
        print(f"Total Tests: {total_count}")
        print(f"Successful: {success_count} ({success_count/total_count*100:.1f}%)")
        print(f"Failed: {total_count - success_count}")
        
        # Agent detection summary
        print("\nAgent Detection Summary:")
        agent_counts = {}
        for result in results:
            for agent in result['agents']:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
                
        for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent}: {count} tests")
            
        # Citation summary
        citation_tests = sum(1 for r in results if r['has_citations'])
        print(f"\nCitation Detection: {citation_tests}/{total_count} tests had citations")
        
        # Failed tests
        failed_tests = [r for r in results if r['status'] != 'success']
        if failed_tests:
            print("\nFailed Tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['status']}")
                
        print(f"\n📁 Detailed logs saved to: {self.log_base_dir}")
        print("   Each test has both .json and _readable.txt versions")
        
        await self.client.aclose()
        
    async def analyze_output_item_types(self):
        """Analyze and document all output item types from the API"""
        print("\n" + "="*80)
        print("ANALYZING OUTPUT ITEM TYPES")
        print("="*80)
        
        # Run a simple test to collect output item types
        request_data = {
            "messages": [{"role": "user", "content": "What is AI? Search for information and cite sources."}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": True,
            "enable_citations": True
        }
        
        output_item_types = {}
        event_types = set()
        
        async with self.client.stream('POST', self.base_url, json=request_data) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data == '[DONE]':
                        break
                        
                    try:
                        event = json.loads(event_data)
                        event_type = event.get('type', '')
                        event_types.add(event_type)
                        
                        # Collect output items
                        if 'item' in event:
                            item = event['item']
                            item_type = item.get('type', 'unknown')
                            if item_type not in output_item_types:
                                output_item_types[item_type] = {
                                    "example": item,
                                    "event_types": set()
                                }
                            output_item_types[item_type]["event_types"].add(event_type)
                            
                    except:
                        pass
                        
        print("\nOUTPUT ITEM TYPES FOUND:")
        print("-"*80)
        for item_type, info in output_item_types.items():
            print(f"\n{item_type.upper()}:")
            print(f"  Event types: {', '.join(info['event_types'])}")
            print(f"  Example: {json.dumps(info['example'], indent=4)[:200]}...")
            
        print("\n\nALL EVENT TYPES:")
        print("-"*80)
        for event_type in sorted(event_types):
            print(f"  - {event_type}")
            
        # Save analysis
        analysis_file = self.log_base_dir / "output_item_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump({
                "output_item_types": {k: {"event_types": list(v["event_types"]), "example": v["example"]} 
                                     for k, v in output_item_types.items()},
                "all_event_types": sorted(list(event_types))
            }, f, indent=2)
            
        print(f"\n📄 Analysis saved to: {analysis_file}")

async def main():
    tester = DetailedAgentTester()
    
    # First analyze output item types
    await tester.analyze_output_item_types()
    
    # Then run comprehensive test suite
    await tester.run_comprehensive_test_suite()

if __name__ == "__main__":
    asyncio.run(main())