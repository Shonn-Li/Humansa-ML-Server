#!/usr/bin/env python3
"""
Consolidated Test Scenario Runner for Humansa Endpoint

This script runs multiple test scenarios and consolidates all results into a single report
with detailed output item analysis for easier debugging and visualization.
"""

import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp


class ConsolidatedTestRunner:
    """Runs multiple test scenarios and consolidates results"""
    
    def __init__(self):
        self.base_url = "http://localhost:5001"
        self.endpoint = "/humansa/response"
        self.all_results = []
        self.consolidated_report = []
        
    def define_test_scenarios(self) -> List[Dict[str, Any]]:
        """Define all test scenarios to run"""
        return [
            {
                "name": "Introduction Test",
                "description": "Test self-introduction when user greets",
                "messages": [
                    {
                        "role": "user", 
                        "content": "你好，请介绍一下你自己"
                    }
                ],
                "expected": "Should introduce as Humansa AI assistant with company background",
                "enable_web_search": False
            },
            {
                "name": "Doctor Appointment Test", 
                "description": "Test medical appointment booking with tools",
                "messages": [
                    {
                        "role": "user",
                        "content": "帮我预约个最近一周的医生，要在深圳的，专科是心血管科"
                    }
                ],
                "expected": "Should find doctors, check availability, ASK FOR CONFIRMATION, then book",
                "enable_web_search": False
            },
            {
                "name": "Complex Medical Query",
                "description": "Test complex medical question with web search",
                "messages": [
                    {
                        "role": "user",
                        "content": "我想了解一下心血管疾病的预防方法，以及在深圳哪里可以做相关检查"
                    }
                ],
                "expected": "Should provide medical info and suggest local medical facilities",
                "enable_web_search": True
            },
            {
                "name": "Follow-up Conversation",
                "description": "Test conversation with context",
                "messages": [
                    {
                        "role": "user",
                        "content": "我上次问过心血管科的问题"
                    },
                    {
                        "role": "assistant", 
                        "content": "我记得您询问了心血管疾病的预防方法和深圳的检查地点。您还有什么具体问题吗？"
                    },
                    {
                        "role": "user",
                        "content": "现在想直接预约一个医生"
                    }
                ],
                "expected": "Should understand context and proceed with appointment booking",
                "enable_web_search": False
            }
        ]
    
    async def run_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario and return detailed results"""
        print(f"\n🧪 Running: {scenario['name']}")
        print(f"📝 Description: {scenario['description']}")
        print(f"💭 Expected: {scenario['expected']}")
        
        start_time = time.time()
        
        # Prepare request - using the EXACT format from working test_doctor_tools.py
        payload = {
            "messages": scenario["messages"],
            "model": "gpt-4.1-nano",
            "user_id": 43,
            "conversation_id": 1000 + len(self.all_results),  # Unique conversation ID
            "enable_rag": True,
            "enable_citations": True,
            "enable_web_search": scenario.get("enable_web_search", True),
            "enable_title_generation": False,
            "stream": True,
            "completion_type": "humansa",
            "attachments": [],
            "enable_realtime_streaming": True
        }
        
        # Initialize metrics and tracking
        metrics = {
            "scenario": scenario["name"],
            "success": False,
            "total_events": 0,
            "reasoning_count": 0,
            "function_call_count": 0,
            "tool_call_count": 0,
            "medical_events": 0,
            "introduction_detected": False,
            "tools_used": [],
            "total_text_length": 0,
            "duration": 0,
            "final_message": "",
            "issues_detected": []
        }
        
        output_items = []
        current_output_items = {}
        event_log = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}{self.endpoint}", 
                                      json=payload,
                                      headers={"Content-Type": "application/json"}) as response:
                    
                    print(f"📊 Response status: {response.status}")
                    print(f"📊 Content-Type: {response.headers.get('Content-Type')}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    print(f"🟢 Connected to stream...")
                    
                    # Process streaming response - EXACT format from working test_doctor_tools.py
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        
                        if not line_str:
                            continue
                        
                        # Parse new canonical format - EXACT match to working version
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]  # Remove "data: "
                            
                            # Check for completion signal
                            if data_str == "[DONE]":
                                metrics["duration"] = time.time() - start_time
                                metrics["success"] = True
                                print(f"🏁 Stream completed. Total events: {metrics['total_events']}")
                                break
                            
                            # Parse JSON data
                            try:
                                parsed_data = json.loads(data_str)
                                metrics["total_events"] += 1
                                
                                # Get event type - EXACT match to working version
                                event_type = parsed_data.get('event', parsed_data.get('type', 'unknown'))
                                
                                # Log event for detailed analysis
                                event_log.append({
                                    "type": event_type,
                                    "data": parsed_data,
                                    "timestamp": time.time() - start_time
                                })
                                
                                # Track output items - using working version logic
                                await self._process_output_item_event(parsed_data, event_type, output_items, current_output_items)
                                
                                # Update metrics - using working version logic
                                await self._update_metrics(parsed_data, event_type, metrics)
                                
                                # Real-time status updates
                                self._print_event_summary(event_type, parsed_data)
                                
                            except json.JSONDecodeError as e:
                                print(f"❌ JSON Parse Error: {e}")
                                continue
            
            # Calculate final metrics
            metrics["duration"] = time.time() - start_time
            
            # Extract final message from output items
            message_items = [item for item in output_items if item['type'] == 'message']
            if message_items:
                metrics["final_message"] = message_items[-1]['content']
            
            # Detect issues
            metrics["issues_detected"] = self._detect_issues(output_items, metrics)
            
            print(f"✅ Scenario completed in {metrics['duration']:.2f}s")
            print(f"📝 Total text: {metrics['total_text_length']} chars")
            print(f"🧠 Reasoning: {metrics['reasoning_count']} chunks")
            print(f"� Tools: {metrics['tool_call_count']} calls")
            print(f"🏥 Medical events: {metrics['medical_events']}")
            print(f"👋 Introduction: {'✅' if metrics['introduction_detected'] else '❌'}")
            print(f"�📊 Events: {metrics['total_events']}, Tools: {', '.join(metrics['tools_used']) if metrics['tools_used'] else 'None'}")
            
            return {
                "metrics": metrics,
                "output_items": output_items,
                "event_log": event_log,
                "scenario": scenario
            }
            
        except Exception as e:
            metrics["duration"] = time.time() - start_time
            metrics["success"] = False
            print(f"❌ Scenario failed: {e}")
            
            return {
                "metrics": metrics,
                "output_items": output_items,
                "event_log": event_log,
                "scenario": scenario,
                "error": str(e)
            }
    
    async def _process_output_item_event(self, parsed_data: Dict, event_type: str, 
                                       output_items: List, current_output_items: Dict):
        """Process output item events for detailed tracking"""
        
        if event_type == "response.output_item.added":
            item = parsed_data.get('item', {})
            output_index = parsed_data.get('output_index', -1)
            item_id = item.get('id', 'unknown')
            item_type = item.get('type', 'unknown')
            
            output_item = {
                "index": output_index,
                "type": item_type,
                "id": item_id,
                "content": "",
                "status": item.get('status', 'in_progress'),
                "events": [],
                "function_name": ""  # Add function name tracking
            }
            
            # Extract function name for function_tool_call items
            if item_type == 'function_tool_call':
                func_name = (
                    item.get('function', {}).get('name', '') or
                    item.get('call', {}).get('function', {}).get('name', '') or
                    item.get('name', '')
                )
                output_item["function_name"] = func_name
            
            output_items.append(output_item)
            current_output_items[item_id] = output_item
            
        elif event_type in ["response.reasoning_text.delta", "response.reasoning_text.done"]:
            item_id = parsed_data.get('item_id', '')
            if item_id in current_output_items:
                if event_type == "response.reasoning_text.delta":
                    delta = parsed_data.get('delta', '')
                    current_output_items[item_id]["content"] += delta
                    current_output_items[item_id]["events"].append(f"Delta: {delta[:50]}...")
                elif event_type == "response.reasoning_text.done":
                    text = parsed_data.get('text', '')
                    current_output_items[item_id]["content"] = text  # Final content
                    current_output_items[item_id]["events"].append(f"Done: {text[:50]}...")
                    
        elif event_type == "response.output_text.delta":
            item_id = parsed_data.get('item_id', '')
            if item_id in current_output_items:
                delta = parsed_data.get('delta', '')
                current_output_items[item_id]["content"] += delta
                current_output_items[item_id]["events"].append(f"Delta: {delta[:50]}...")
                
        elif event_type == "response.function_tool_result.delta":
            item_id = parsed_data.get('item_id', '')
            if item_id in current_output_items:
                delta = parsed_data.get('delta', '')
                current_output_items[item_id]["content"] += delta
                current_output_items[item_id]["events"].append(f"Tool Result: {delta[:30]}...")
                
        elif event_type == "response.output_item.done":
            item = parsed_data.get('item', {})
            item_id = item.get('id', '')
            if item_id in current_output_items:
                current_output_items[item_id]["status"] = "completed"
                # If there's final content in the item, use it
                if 'content' in item and item['content']:
                    if isinstance(item['content'], list) and len(item['content']) > 0:
                        if isinstance(item['content'][0], dict) and 'text' in item['content'][0]:
                            current_output_items[item_id]["content"] = item['content'][0]['text']
    
    async def _update_metrics(self, parsed_data: Dict, event_type: str, metrics: Dict):
        """Update metrics based on event - EXACT logic from working test_doctor_tools.py"""
        medical_keywords = ["医生", "预约", "appointment", "doctor", "clinic", "medical", "深圳", "诊所"]
        intro_keywords = ["humansa", "诺亚新舟", "ai智能助理", "以爱行舟", "三甲", "专家"]
        
        # Check for medical and introduction content
        event_text = json.dumps(parsed_data, ensure_ascii=False).lower()
        is_medical = any(keyword in event_text for keyword in medical_keywords)
        is_intro = any(keyword in event_text for keyword in intro_keywords)
        
        if is_medical:
            metrics["medical_events"] += 1
        if is_intro:
            metrics["introduction_detected"] = True
        
        # Track different event types - EXACT logic from working version
        if event_type == "response.output_text.delta":
            delta = parsed_data.get('data', {}).get('delta', '') or parsed_data.get('delta', '')
            metrics["total_text_length"] += len(delta)
            
        elif event_type == "response.reasoning_text.delta":
            delta = parsed_data.get('data', {}).get('delta', '') or parsed_data.get('delta', '')
            metrics["reasoning_count"] += 1
        
        elif "function" in event_type or "tool" in event_type:
            metrics["function_call_count"] += 1
            metrics["tool_call_count"] += 1
            
            # Extract function/tool name - Enhanced extraction from multiple sources
            func_name = (
                parsed_data.get('data', {}).get('item', {}).get('name', '') or 
                parsed_data.get('data', {}).get('name', '') or
                parsed_data.get('item', {}).get('name', '') or
                parsed_data.get('name', '') or
                parsed_data.get('function', {}).get('name', '')
            )
            
            # Also try to extract from function_call structure if available
            if not func_name and 'item' in parsed_data:
                item = parsed_data['item']
                if isinstance(item, dict):
                    func_name = (
                        item.get('function', {}).get('name', '') or
                        item.get('call', {}).get('function', {}).get('name', '')
                    )
            
            if func_name and func_name not in metrics["tools_used"]:
                metrics["tools_used"].append(func_name)
    
    def _print_event_summary(self, event_type: str, parsed_data: Dict):
        """Print concise real-time event summaries - matching working version logic"""
        
        # Check for medical and introduction content
        medical_keywords = ["医生", "预约", "appointment", "doctor", "clinic", "medical", "深圳", "诊所"]
        intro_keywords = ["humansa", "诺亚新舟", "ai智能助理", "以爱行舟", "三甲", "专家"]
        
        event_text = json.dumps(parsed_data, ensure_ascii=False).lower()
        is_medical = any(keyword in event_text for keyword in medical_keywords)
        is_intro = any(keyword in event_text for keyword in intro_keywords)
        
        if event_type == "response.reasoning_text.delta":
            delta = parsed_data.get('delta', '')
            print(f"🧠 Reasoning: '{delta[:40]}{'...' if len(delta) > 40 else ''}'")
        
        elif event_type == "response.output_text.delta":
            delta = parsed_data.get('delta', '')
            if is_intro:
                print(f"👋💬 Introduction Text: '{delta[:50]}{'...' if len(delta) > 50 else ''}'")
            elif is_medical:
                print(f"🏥💬 Medical Text: '{delta[:50]}{'...' if len(delta) > 50 else ''}'")
            else:
                print(f"💬 Text: '{delta[:30]}{'...' if len(delta) > 30 else ''}'")
        
        elif "function" in event_type or "tool" in event_type:
            # Extract function/tool name - Enhanced extraction from multiple sources
            func_name = (
                parsed_data.get('data', {}).get('item', {}).get('name', '') or 
                parsed_data.get('data', {}).get('name', '') or
                parsed_data.get('item', {}).get('name', '') or
                parsed_data.get('name', '') or
                parsed_data.get('function', {}).get('name', '')
            )
            
            # Also try to extract from function_call structure if available
            if not func_name and 'item' in parsed_data:
                item = parsed_data['item']
                if isinstance(item, dict):
                    func_name = (
                        item.get('function', {}).get('name', '') or
                        item.get('call', {}).get('function', {}).get('name', '')
                    )
            
            if any(keyword in func_name.lower() for keyword in ["doctor", "appointment", "medical", "clinic"]):
                print(f"🏥🔧 Medical Tool: {event_type} - {func_name}")
            else:
                print(f"🔧 Tool: {event_type} - {func_name}")
        
        elif event_type == "response.created":
            print(f"🚀 Response Created")
        elif event_type == "response.in_progress":
            print(f"⏳ Response In Progress")
        elif event_type == "response.completed":
            print(f"✅ Response Completed")
        else:
            marker = "🏥" if is_medical else "👋" if is_intro else ""
            print(f"{marker}📨 Event: {event_type}")
    
    def _detect_issues(self, output_items: List, metrics: Dict) -> List[str]:
        """Detect potential issues in the test results"""
        issues = []
        
        # Check for duplicate reasoning
        reasoning_items = [item for item in output_items if item['type'] == 'reasoning']
        content_groups = {}
        for item in reasoning_items:
            content = item['content'].strip()
            if content:
                if content not in content_groups:
                    content_groups[content] = []
                content_groups[content].append(item)
        
        for content, items in content_groups.items():
            if len(items) > 1:
                issues.append(f"Duplicate reasoning content ({len(items)} instances)")
        
        # Check for direct booking without confirmation (for appointment tests)
        if "appointment" in metrics["scenario"].lower() or "预约" in metrics["scenario"]:
            tools_used = metrics["tools_used"]
            if "book_appointment" in tools_used and "find_doctor_availability" in tools_used:
                # Check if there was proper confirmation flow
                final_message = metrics["final_message"].lower()
                if "已成功" in final_message or "confirmed" in final_message:
                    issues.append("Direct booking detected - may lack user confirmation")
        
        return issues
    
    def write_consolidated_report(self, all_results: List[Dict], output_file: str):
        """Write a comprehensive consolidated report"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("HUMANSA ENDPOINT CONSOLIDATED TEST REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Scenarios: {len(all_results)}\n\n")
            
            # Executive Summary
            f.write("📊 EXECUTIVE SUMMARY\n")
            f.write("-" * 30 + "\n")
            
            total_events = sum(r["metrics"]["total_events"] for r in all_results)
            total_duration = sum(r["metrics"]["duration"] for r in all_results)
            successful_scenarios = sum(1 for r in all_results if r["metrics"]["success"])
            
            f.write(f"Success Rate: {successful_scenarios}/{len(all_results)} ({successful_scenarios/len(all_results)*100:.1f}%)\n")
            f.write(f"Total Events Processed: {total_events}\n")
            f.write(f"Total Duration: {total_duration:.2f} seconds\n")
            f.write(f"Average Duration: {total_duration/len(all_results):.2f} seconds\n\n")
            
            # All Tools Used Across All Scenarios
            all_tools = set()
            for result in all_results:
                all_tools.update(result["metrics"]["tools_used"])
            f.write(f"All Tools Used: {', '.join(sorted(all_tools)) if all_tools else 'None'}\n\n")
            
            # Issues Summary
            all_issues = []
            for result in all_results:
                all_issues.extend(result["metrics"]["issues_detected"])
            
            if all_issues:
                f.write("🚨 ISSUES DETECTED ACROSS ALL SCENARIOS\n")
                f.write("-" * 40 + "\n")
                for issue in set(all_issues):  # Deduplicate
                    count = all_issues.count(issue)
                    f.write(f"  • {issue} (appeared {count} time{'s' if count > 1 else ''})\n")
                f.write("\n")
            
            # Detailed Results for Each Scenario
            for i, result in enumerate(all_results, 1):
                f.write("=" * 60 + "\n")
                f.write(f"SCENARIO #{i}: {result['metrics']['scenario']}\n")
                f.write("=" * 60 + "\n")
                
                scenario = result["scenario"]
                metrics = result["metrics"]
                output_items = result["output_items"]
                
                f.write(f"Description: {scenario['description']}\n")
                f.write(f"Expected: {scenario['expected']}\n")
                f.write(f"Enable Web Search: {scenario.get('enable_web_search', False)}\n\n")
                
                # Basic Metrics
                f.write("📈 METRICS\n")
                f.write("-" * 15 + "\n")
                f.write(f"Success: {'✅ Yes' if metrics['success'] else '❌ No'}\n")
                f.write(f"Duration: {metrics['duration']:.2f} seconds\n")
                f.write(f"Total events: {metrics['total_events']}\n")
                f.write(f"Reasoning events: {metrics['reasoning_count']}\n")
                f.write(f"Function calls: {metrics['function_call_count']}\n")
                f.write(f"Medical events: {metrics['medical_events']}\n")
                f.write(f"Introduction detected: {metrics['introduction_detected']}\n")
                f.write(f"Tools used: {', '.join(metrics['tools_used']) if metrics['tools_used'] else 'None'}\n")
                f.write(f"Text length: {metrics['total_text_length']} chars\n\n")
                
                # Issues for this scenario
                if metrics["issues_detected"]:
                    f.write("🚨 ISSUES IN THIS SCENARIO\n")
                    f.write("-" * 25 + "\n")
                    for issue in metrics["issues_detected"]:
                        f.write(f"  • {issue}\n")
                    f.write("\n")
                
                # Output Items Analysis
                f.write("📋 DETAILED OUTPUT ITEM ANALYSIS\n")
                f.write("-" * 35 + "\n")
                f.write(f"Total output items: {len(output_items)}\n\n")
                
                # Group items by type
                items_by_type = {}
                for item in output_items:
                    item_type = item['type']
                    if item_type not in items_by_type:
                        items_by_type[item_type] = []
                    items_by_type[item_type].append(item)
                
                # Summary by type
                f.write("📊 OUTPUT ITEMS BY TYPE:\n")
                for item_type, items in items_by_type.items():
                    f.write(f"  {item_type}: {len(items)} items\n")
                f.write("\n")
                
                # Each output item in detail
                for j, item in enumerate(output_items):
                    f.write(f"OUTPUT ITEM #{j+1}:\n")
                    f.write(f"  Index: {item['index']}\n")
                    f.write(f"  Type: {item['type']}\n")
                    f.write(f"  ID: {item['id']}\n")
                    f.write(f"  Status: {item['status']}\n")
                    if item.get('function_name'):
                        f.write(f"  Function Name: {item['function_name']}\n")
                    f.write(f"  Content Length: {len(item['content'])} chars\n")
                    f.write(f"  Content Preview: {item['content'][:100]}{'...' if len(item['content']) > 100 else ''}\n")
                    f.write(f"  Events: {len(item['events'])}\n")
                    for k, event in enumerate(item['events'][:3]):  # Show first 3 events
                        f.write(f"    Event {k+1}: {event}\n")
                    if len(item['events']) > 3:
                        f.write(f"    ... and {len(item['events']) - 3} more events\n")
                    f.write("\n")
                
                # Duplicate Analysis for this scenario
                f.write("🔍 DUPLICATE ANALYSIS:\n")
                reasoning_items = [item for item in output_items if item['type'] == 'reasoning']
                content_groups = {}
                for item in reasoning_items:
                    content = item['content'].strip()
                    if content:
                        if content not in content_groups:
                            content_groups[content] = []
                        content_groups[content].append(item)
                
                duplicates_found = False
                for content, items in content_groups.items():
                    if len(items) > 1:
                        duplicates_found = True
                        f.write(f"  DUPLICATE REASONING CONTENT ({len(items)} items):\n")
                        f.write(f"    Content: {content[:100]}{'...' if len(content) > 100 else ''}\n")
                        f.write(f"    Items: {[f'#{item['index']} ({item['id']})' for item in items]}\n\n")
                
                if not duplicates_found:
                    f.write("  ✅ No duplicate reasoning content found\n\n")
                
                # Tool call sequence
                f.write("🔧 TOOL CALL SEQUENCE:\n")
                tool_items = [item for item in output_items if item['type'] in ['function_tool_call', 'function_tool_result']]
                if tool_items:
                    for k, item in enumerate(tool_items):
                        func_name = item.get('function_name', '')
                        func_display = f" - {func_name}" if func_name else ""
                        f.write(f"  Tool {k+1}: {item['type']}{func_display} - Index {item['index']} - {item['id']}\n")
                        if item['content']:
                            f.write(f"    Content: {item['content'][:80]}{'...' if len(item['content']) > 80 else ''}\n")
                else:
                    f.write("  No tool calls found\n")
                f.write("\n")
                
                # Final message
                if metrics["final_message"]:
                    f.write("💬 FINAL ASSISTANT MESSAGE:\n")
                    f.write(f"  {metrics['final_message']}\n\n")
                else:
                    f.write("💬 No final assistant message found\n\n")
    
    async def run_all_scenarios(self):
        """Run all test scenarios and generate consolidated report"""
        print("🚀 Starting Consolidated Humansa Endpoint Test")
        print("=" * 60)
        
        scenarios = self.define_test_scenarios()
        all_results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n📋 Scenario {i}/{len(scenarios)}")
            result = await self.run_single_scenario(scenario)
            all_results.append(result)
            
            # Brief summary
            metrics = result["metrics"]
            print(f"   Status: {'✅ Success' if metrics['success'] else '❌ Failed'}")
            print(f"   Duration: {metrics['duration']:.2f}s")
            print(f"   Events: {metrics['total_events']}")
            print(f"   Tools: {len(metrics['tools_used'])}")
            if metrics['issues_detected']:
                print(f"   Issues: {len(metrics['issues_detected'])}")
        
        # Generate consolidated report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"humansa_consolidated_test_{timestamp}.txt"
        
        self.write_consolidated_report(all_results, output_file)
        
        print(f"\n🎉 All scenarios completed!")
        print(f"📄 Consolidated report: {output_file}")
        
        # Final summary
        successful = sum(1 for r in all_results if r["metrics"]["success"])
        total_duration = sum(r["metrics"]["duration"] for r in all_results)
        
        print(f"📊 Final Summary:")
        print(f"   Success Rate: {successful}/{len(scenarios)} ({successful/len(scenarios)*100:.1f}%)")
        print(f"   Total Duration: {total_duration:.2f}s")
        print(f"   Average per Scenario: {total_duration/len(scenarios):.2f}s")


async def main():
    """Main entry point"""
    runner = ConsolidatedTestRunner()
    await runner.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())
