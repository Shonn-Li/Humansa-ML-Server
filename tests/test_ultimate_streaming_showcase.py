#!/usr/bin/env python3
"""
Ultimate Streaming Event Showcase

This test demonstrates all the streaming events and agent flows in the multi-agent system.
It shows exactly what events are triggered for each type of query.
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import re

class EventCollector:
    """Collects and categorizes streaming events"""
    
    def __init__(self):
        self.events = []
        self.event_counts = defaultdict(int)
        self.agents_detected = set()
        self.response_text = ""
        self.citations = []
        self.reasoning_text = ""
        
    def process_event(self, event: Dict[str, Any], sequence: int):
        """Process a single event"""
        event_type = event.get("type", "")
        self.event_counts[event_type] += 1
        
        # Store event
        self.events.append({
            "sequence": sequence,
            "type": event_type,
            "data": event
        })
        
        # Extract information
        if event_type == "response.output_text.delta":
            self.response_text += event.get("delta", "")
            
        elif event_type == "response.reasoning_text.delta":
            reasoning = event.get("delta", "")
            self.reasoning_text += reasoning
            
            # Detect agents from reasoning
            if "routed to agents:" in reasoning:
                agents_part = reasoning.split("routed to agents:")[1]
                for agent in agents_part.split(","):
                    agent_name = agent.strip().lower()
                    if agent_name:
                        self.agents_detected.add(agent_name)
                        
        elif event_type == "response.output_text.annotation.added":
            self.citations.append(event.get("annotation", {}))
            
        # Detect agents from item IDs
        elif "item" in event:
            item_id = event["item"].get("id", "")
            if item_id.startswith("router_"):
                self.agents_detected.add("router")
            elif item_id.startswith("rag_"):
                self.agents_detected.add("rag")
            elif item_id.startswith("ws_"):
                self.agents_detected.add("web_search")
            elif item_id.startswith("attachment_"):
                self.agents_detected.add("attachment")
            elif item_id.startswith("cit_"):
                self.agents_detected.add("citation")
            elif item_id.startswith("code_"):
                self.agents_detected.add("code_interpreter")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get event summary"""
        # Find citation markers in text
        citation_pattern = re.compile(r'\[(\d+)\]')
        text_citations = citation_pattern.findall(self.response_text)
        
        return {
            "total_events": len(self.events),
            "event_types": dict(self.event_counts),
            "agents_detected": list(self.agents_detected),
            "response_length": len(self.response_text),
            "citations_in_annotations": len(self.citations),
            "citations_in_text": text_citations,
            "has_reasoning": len(self.reasoning_text) > 0
        }


async def run_streaming_test(name: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single streaming test and collect all events"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    
    client = httpx.AsyncClient(timeout=60.0)
    request["stream"] = True
    
    collector = EventCollector()
    
    try:
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
            sequence = 0
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        event = json.loads(data_str)
                        collector.process_event(event, sequence)
                        sequence += 1
                    except json.JSONDecodeError:
                        pass
        
        # Print event flow
        print("\nEVENT FLOW:")
        print("-"*60)
        
        # Group events by phase
        phases = {
            "initialization": ["response.created", "response.in_progress"],
            "reasoning": ["response.reasoning", "response.output_item.added"],
            "tool_calls": ["tool_call", "search_call", "file_search", "web_search"],
            "response_generation": ["response.output_text", "response.content_part"],
            "citations": ["annotation"],
            "completion": ["response.usage", "response.completed", "response.done"]
        }
        
        current_phase = None
        for event in collector.events[:50]:  # Show first 50 events
            event_type = event["type"]
            
            # Determine phase
            for phase_name, patterns in phases.items():
                if any(pattern in event_type for pattern in patterns):
                    if current_phase != phase_name:
                        current_phase = phase_name
                        print(f"\n📍 {phase_name.upper()}:")
                    break
            
            # Format event
            if "output_item.added" in event_type:
                item = event["data"].get("item", {})
                print(f"  [{event['sequence']:3d}] ➕ {item.get('type', 'unknown')} (ID: {item.get('id', 'N/A')[:12]}...)")
            elif "reasoning_text.delta" in event_type:
                text = event["data"].get("delta", "")[:50]
                if text.strip():
                    print(f"  [{event['sequence']:3d}] 🧠 {text}...")
            elif "output_text.delta" in event_type and event['sequence'] < 20:
                text = event["data"].get("delta", "")[:50]
                if text.strip():
                    print(f"  [{event['sequence']:3d}] 📝 {text}...")
            elif "annotation.added" in event_type:
                ann = event["data"].get("annotation", {})
                print(f"  [{event['sequence']:3d}] 📌 Citation: {ann.get('text', 'N/A')} at {ann.get('start_index', 0)}-{ann.get('end_index', 0)}")
            elif event_type in ["response.done", "response.completed"]:
                print(f"  [{event['sequence']:3d}] ✅ {event_type}")
        
        if len(collector.events) > 50:
            print(f"\n  ... ({len(collector.events) - 50} more events)")
        
        # Print summary
        summary = collector.get_summary()
        print(f"\nSUMMARY:")
        print(f"  Total Events: {summary['total_events']}")
        print(f"  Agents: {', '.join(summary['agents_detected']) if summary['agents_detected'] else 'None'}")
        print(f"  Response Length: {summary['response_length']} chars")
        print(f"  Citations in Text: {summary['citations_in_text']}")
        print(f"  Citation Annotations: {summary['citations_in_annotations']}")
        
        # Show top event types
        print(f"\nTOP EVENT TYPES:")
        sorted_events = sorted(summary['event_types'].items(), key=lambda x: x[1], reverse=True)
        for event_type, count in sorted_events[:5]:
            print(f"  {event_type}: {count}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        summary = {"error": str(e)}
    finally:
        await client.aclose()
    
    return summary


async def main():
    """Run showcase tests"""
    print("="*80)
    print("ULTIMATE STREAMING EVENT SHOWCASE")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    test_cases = [
        {
            "name": "Simple Query (No Context)",
            "request": {
                "messages": [{"role": "user", "content": "What is quantum computing?"}],
                "user_id": 10001,
                "model": "gpt-4.1-nano"
            }
        },
        {
            "name": "Web Search with Citations",
            "request": {
                "messages": [{"role": "user", "content": "What are the latest breakthroughs in AI for 2024? Include sources."}],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_citations": True
            }
        },
        {
            "name": "Knowledge Base Query (RAG)",
            "request": {
                "messages": [{"role": "user", "content": "What do my notes say about reinforcement learning and PARL?"}],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_citations": True
            }
        },
        {
            "name": "PDF Attachment Processing",
            "request": {
                "messages": [{"role": "user", "content": "Summarize the key findings from this paper"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_citations": True
            }
        },
        {
            "name": "Multiple Attachments Comparison",
            "request": {
                "messages": [{"role": "user", "content": "Compare the approaches in these two papers"}],
                "attachments": [
                    "https://arxiv.org/pdf/2505.18499.pdf",
                    "https://arxiv.org/pdf/2311.10122.pdf"
                ],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_citations": True
            }
        },
        {
            "name": "Complex Multi-Step Query",
            "request": {
                "messages": [{"role": "user", "content": "Based on my notes and recent research, provide a comprehensive analysis of transformer architectures: 1) Evolution from attention mechanisms, 2) Current state-of-the-art variants, 3) Future directions. Include citations."}],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_iterations": True,
                "enable_citations": True
            }
        }
    ]
    
    # Run specific test if provided
    if len(sys.argv) > 1:
        test_num = int(sys.argv[1])
        if 0 < test_num <= len(test_cases):
            test = test_cases[test_num - 1]
            await run_streaming_test(test["name"], test["request"])
        else:
            print(f"Invalid test number. Choose 1-{len(test_cases)}")
    else:
        # Run all tests
        for i, test in enumerate(test_cases, 1):
            print(f"\n[Test {i}/{len(test_cases)}]")
            await run_streaming_test(test["name"], test["request"])
            await asyncio.sleep(2)  # Brief pause between tests
    
    print("\n" + "="*80)
    print("SHOWCASE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())