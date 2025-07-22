#!/usr/bin/env python3
"""
Consolidated Test for O3 Demo - Output Item Completions Only

This script runs multiple test scenarios and focuses exclusively on output_item.done events,
similar to the original doctor tools test style, providing a clean completion-focused report.
"""

import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp


class O3OutputItemTestRunner:
    """Runs test scenarios tracking only output item completions"""

    def __init__(self):
        self.base_url = "http://localhost:5001"
        self.endpoint = "/humansa/o3-demo"
        self.all_results = []

    def define_test_scenarios(self) -> List[Dict[str, Any]]:
        """Define test scenarios focused on output item completion tracking"""
        return [
            # {
            #     "name": "Introduction Test",
            #     "description": "Test self-introduction with O3",
            #     "messages": [
            #         {
            #             "role": "user",
            #             "content": "你好，请介绍一下你自己"
            #         }
            #     ],
            #     "expected": "Should introduce as Humansa AI assistant"
            # },
            {
                "name": "Doctor Appointment Test",
                "description": "Test medical appointment booking with O3 tools",
                "messages": [
                    {
                        "role": "user",
                        "content": "帮我预约个最近一周的医生，要在深圳的，专科是心血管科"
                    }
                ],
                "expected": "Should find doctors, check availability, and book appointment"
            },
            # {
            #     "name": "Complex Medical Query",
            #     "description": "Test complex medical question with O3 reasoning",
            #     "messages": [
            #         {
            #             "role": "user",
            #             "content": "我想了解一下心血管疾病的预防方法，以及在深圳哪里可以做相关检查"
            #         }
            #     ],
            #     "expected": "Should provide medical info and suggest local medical facilities"
            # },
            # {
            #     "name": "Follow-up Conversation",
            #     "description": "Test multi-turn conversation with O3",
            #     "messages": [
            #         {
            #             "role": "user",
            #             "content": "我上次问过心血管科的问题"
            #         },
            #         {
            #             "role": "assistant",
            #             "content": "我记得您询问了心血管疾病的预防方法和深圳的检查地点。您还有什么具体问题吗？"
            #         },
            #         {
            #             "role": "user",
            #             "content": "现在想直接预约一个医生"
            #         }
            #     ],
            #     "expected": "Should understand context and proceed with appointment booking"
            # }
        ]

    async def run_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario and return only output item completion data"""
        print(f"\n🧪 Running: {scenario['name']}")
        print(f"📝 Description: {scenario['description']}")
        print(f"💭 Expected: {scenario['expected']}")

        start_time = time.time()

        # Prepare request using O3 demo endpoint
        payload = {
            "messages": scenario["messages"],
            "model": "gpt-o4-mini",
            "user_id": f"o3_test_{int(time.time())}",
            "conversation_id": int(time.time()),
            "enable_rag": True,
            "enable_citations": True,
            "enable_web_search": scenario.get("enable_web_search", False),
            "enable_title_generation": False,
            "stream": True,
            "completion_type": "o3_demo",
            "attachments": [],
            "enable_realtime_streaming": True
        }

        # Metrics focused on output item completions only
        metrics = {
            "scenario_name": scenario["name"],
            "success": False,
            "total_events": 0,
            "output_items_completed": 0,
            "output_item_types": {},
            "completion_times": [],
            "final_message": "",
            "has_humansa_content": False,
            "has_medical_content": False,
            "has_tool_calls": False,
            "duration": 0
        }

        output_items = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{self.endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ HTTP {response.status}: {error_text}")
                        return {**metrics, "error": error_text}

                    # Process streaming response - ONLY track output_item.done events
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()

                        if not line_str:
                            continue

                        if line_str.startswith("data: "):
                            data_str = line_str[6:]  # Remove "data: "

                            # Check for completion signal
                            if data_str == "[DONE]":
                                metrics["duration"] = time.time() - start_time
                                metrics["success"] = True
                                print(
                                    f"🏁 Stream completed. Output items: {metrics['output_items_completed']}")
                                break

                            # Parse JSON data
                            try:
                                parsed_data = json.loads(data_str)
                                metrics["total_events"] += 1
                                event_type = parsed_data.get(
                                    'event', parsed_data.get('type', 'unknown'))

                                # ONLY process output_item.done events
                                if event_type == "response.output_item.done":
                                    completion_time = time.time() - start_time
                                    item = parsed_data.get('item', {})
                                    item_id = item.get(
                                        'id', f'item_{len(output_items)}')
                                    item_type = item.get('type', 'unknown')
                                    output_index = item.get(
                                        'index', len(output_items))

                                    # Extract content based on canonical JSON format from spec
                                    content = ""
                                    content_details = {}
                                    
                                    if item_type == 'message':
                                        # Assistant message: extract from content array
                                        if 'content' in item and isinstance(item['content'], list):
                                            full_text = ""
                                            all_annotations = []
                                            for content_part in item['content']:
                                                if content_part.get('type') == 'output_text':
                                                    part_text = content_part.get('text', '')
                                                    full_text += part_text
                                                    part_annotations = content_part.get('annotations', [])
                                                    all_annotations.extend(part_annotations)
                                            content = full_text
                                            if all_annotations:
                                                content_details['annotations'] = all_annotations
                                                content_details['annotation_count'] = len(all_annotations)
                                        elif 'content' in item:
                                            content = str(item['content'])
                                            
                                    elif item_type == 'reasoning':
                                        # Reasoning: O3 uses 'summary' field instead of 'content'
                                        if 'summary' in item:
                                            summary = item['summary']
                                            if isinstance(summary, list) and summary:
                                                # Extract text from O3 reasoning summary format
                                                for summary_part in summary:
                                                    if isinstance(summary_part, dict) and summary_part.get('type') == 'summary_text':
                                                        content = summary_part.get('text', '')
                                                        break
                                                if not content:
                                                    content = str(summary)
                                            else:
                                                content = str(summary)
                                        elif 'content' in item and isinstance(item['content'], list):
                                            for content_part in item['content']:
                                                if content_part.get('type') == 'reasoning_text':
                                                    content = content_part.get('text', '')
                                                    break
                                        elif 'content' in item:
                                            content = str(item['content'])
                                        else:
                                            content = "[No reasoning content available]"
                                    elif item_type == 'function_tool_call':
                                        # Function tool call: extract function name and args
                                        func_name = item.get('name', 'unknown_function')
                                        func_args = item.get('arguments', '')
                                        func_output = item.get('output', '')
                                        content = f"Function: {func_name}"
                                        content_details['function_name'] = func_name
                                        content_details['arguments'] = func_args
                                        content_details['output'] = func_output
                                        metrics["has_tool_calls"] = True
                                        
                                    elif item_type == 'function_tool_result':
                                        # Function tool result: extract from content array
                                        if 'content' in item and isinstance(item['content'], list):
                                            for content_part in item['content']:
                                                if content_part.get('type') == 'output_text':
                                                    content = content_part.get('text', '')
                                                    break
                                        elif 'content' in item:
                                            content = str(item['content'])
                                            
                                    elif item_type == 'web_search_call':
                                        # Web search call: extract query and results
                                        action = item.get('action', {})
                                        results = item.get('results', [])
                                        query = action.get('query', '')
                                        content = f"Web search: {query}"
                                        content_details['query'] = query
                                        content_details['results_count'] = len(results)
                                        content_details['results'] = results[:3]  # First 3 results
                                        
                                    else:
                                        # Generic content extraction
                                        if 'content' in item:
                                            if isinstance(item['content'], list) and item['content']:
                                                content = str(item['content'][0].get('text', item['content'][0]))
                                            else:
                                                content = str(item['content'])
                                        else:
                                            content = f"[{item_type} item completed]"

                                    # Store completed output item
                                    output_item = {
                                        "index": output_index,
                                        "type": item_type,
                                        "id": item_id,
                                        "content": content,
                                        "content_details": content_details,
                                        "completion_time": completion_time,
                                        "raw_item": item  # Store raw item for debugging
                                    }
                                    output_items.append(output_item)

                                    # Update metrics
                                    metrics["output_items_completed"] += 1
                                    metrics["output_item_types"][item_type] = metrics["output_item_types"].get(
                                        item_type, 0) + 1
                                    metrics["completion_times"].append(
                                        completion_time)

                                    # Track content for analysis
                                    if item_type == 'message':
                                        metrics["final_message"] = content

                                    # Content analysis
                                    content_lower = content.lower()
                                    if any(term in content_lower for term in ['humansa', '诺亚新舟', '高端诊所', '医疗助理']):
                                        metrics["has_humansa_content"] = True
                                    if any(term in content_lower for term in ['预约', '医生', '诊所', '医疗', '健康']):
                                        metrics["has_medical_content"] = True

                                    # Log completion (like original doctor tools test)
                                    print(
                                        f"    ✅ {item_type.upper()} completed (#{output_index}, {completion_time:.2f}s)")
                                    if content and len(content) > 0:
                                        preview_length = 300
                                        content_preview = content[:preview_length] + "..." if len(content) > preview_length else content
                                        print(f"       Content ({len(content)} chars): {content_preview}")
                                    
                                    # Only show meaningful content details
                                    if content_details:
                                        meaningful_details = []
                                        for key, value in content_details.items():
                                            if key == 'annotations' and value:  # Only show if annotations exist
                                                meaningful_details.append(f"{key}({len(value)})")
                                            elif key != 'annotations' and value:  # Show other non-empty details
                                                meaningful_details.append(key)
                                        if meaningful_details:
                                            print(f"       Details: {meaningful_details}")
                                    
                                    # Debug: Show raw content structure if content seems truncated
                                    if item_type == 'message' and item.get('content') and len(content) > 0:
                                        raw_content = item.get('content', [])
                                        if isinstance(raw_content, list) and len(raw_content) > 1:
                                            print(f"       DEBUG: Message has {len(raw_content)} content parts")
                                            for i, part in enumerate(raw_content):
                                                part_text = part.get('text', '') if isinstance(part, dict) else str(part)
                                                print(f"              Part {i+1}: {len(part_text)} chars")
                                        elif isinstance(raw_content, list) and len(raw_content) == 1:
                                            part = raw_content[0]
                                            if isinstance(part, dict) and 'text' in part:
                                                part_text = part['text']
                                                if len(part_text) != len(content):
                                                    print(f"       DEBUG: Text length mismatch - raw: {len(part_text)}, extracted: {len(content)}")
                                                if 'annotations' in part:
                                                    print(f"       DEBUG: Found {len(part['annotations'])} annotations in content")

                            except json.JSONDecodeError:
                                # Skip invalid JSON
                                pass

            return {**metrics, "output_items": output_items}

        except Exception as e:
            print(f"❌ Error in {scenario['name']}: {e}")
            return {**metrics, "error": str(e)}

    async def run_all_scenarios(self):
        """Run all test scenarios and generate consolidated report"""
        scenarios = self.define_test_scenarios()

        print(f"🚀 Starting O3 Demo Output Item Completion Tests")
        print(f"📊 Running {len(scenarios)} scenarios")
        print(f"🎯 Focus: output_item.done events only")
        print("=" * 80)

        # Run all scenarios
        for scenario in scenarios:
            result = await self.run_single_scenario(scenario)
            self.all_results.append(result)

        # Generate consolidated report
        await self.generate_consolidated_report()

    async def generate_consolidated_report(self):
        """Generate a consolidated report focusing only on output item completions"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"o3_demo_output_items_consolidated_{timestamp}.txt"

        print(f"\n📊 Generating consolidated report: {report_file}")

        with open(report_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write(
                "O3 DEMO ENDPOINT - OUTPUT ITEM COMPLETIONS CONSOLIDATED REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Scenarios: {len(self.all_results)}\n\n")

            # Executive Summary
            successful_tests = [
                r for r in self.all_results if r.get("success", False)]
            total_output_items = sum(
                r.get("output_items_completed", 0) for r in self.all_results)
            total_duration = sum(r.get("duration", 0)
                                 for r in self.all_results)

            f.write("📊 EXECUTIVE SUMMARY - OUTPUT ITEM COMPLETIONS\n")
            f.write("-" * 50 + "\n")
            f.write(
                f"Success Rate: {len(successful_tests)}/{len(self.all_results)} ({len(successful_tests)/len(self.all_results)*100:.1f}%)\n")
            f.write(f"Total Output Items Completed: {total_output_items}\n")
            f.write(f"Total Duration: {total_duration:.2f} seconds\n")
            f.write(
                f"Average Duration: {total_duration/len(self.all_results):.2f} seconds\n\n")

            # Output item type summary
            all_types = {}
            for result in self.all_results:
                for item_type, count in result.get("output_item_types", {}).items():
                    all_types[item_type] = all_types.get(item_type, 0) + count

            f.write("📋 OUTPUT ITEM TYPES COMPLETED ACROSS ALL SCENARIOS:\n")
            for item_type, count in sorted(all_types.items()):
                f.write(f"  {item_type}: {count} items\n")
            f.write("\n")

            # Content analysis summary
            humansa_scenarios = [r for r in self.all_results if r.get(
                "has_humansa_content", False)]
            medical_scenarios = [r for r in self.all_results if r.get(
                "has_medical_content", False)]
            tool_scenarios = [r for r in self.all_results if r.get(
                "has_tool_calls", False)]

            f.write("🔍 CONTENT ANALYSIS:\n")
            f.write(
                f"  Scenarios with Humansa content: {len(humansa_scenarios)}/{len(self.all_results)}\n")
            f.write(
                f"  Scenarios with medical content: {len(medical_scenarios)}/{len(self.all_results)}\n")
            f.write(
                f"  Scenarios with tool calls: {len(tool_scenarios)}/{len(self.all_results)}\n\n")

            # Detailed scenario results
            f.write("=" * 80 + "\n")
            f.write("DETAILED SCENARIO RESULTS - OUTPUT ITEM COMPLETIONS ONLY\n")
            f.write("=" * 80 + "\n\n")

            for i, result in enumerate(self.all_results, 1):
                f.write(f"SCENARIO #{i}: {result['scenario_name']}\n")
                f.write("-" * 60 + "\n")
                f.write(
                    f"Success: {'✅ Yes' if result.get('success', False) else '❌ No'}\n")
                f.write(f"Duration: {result.get('duration', 0):.2f} seconds\n")
                f.write(
                    f"Output items completed: {result.get('output_items_completed', 0)}\n")
                f.write(
                    f"Final message: {'✅ Yes' if result.get('final_message', '') else '❌ No'}\n")
                f.write(
                    f"Humansa content: {'✅ Yes' if result.get('has_humansa_content', False) else '❌ No'}\n")
                f.write(
                    f"Medical content: {'✅ Yes' if result.get('has_medical_content', False) else '❌ No'}\n")
                f.write(
                    f"Tool calls: {'✅ Yes' if result.get('has_tool_calls', False) else '❌ No'}\n\n")

                # Output item details
                f.write("📦 OUTPUT ITEMS COMPLETED:\n")
                output_items = result.get("output_items", [])
                if output_items:
                    for idx, item in enumerate(output_items):
                        f.write(
                            f"  #{idx+1}: {item['type'].upper()} (ID: {item['id']}, {item['completion_time']:.2f}s)\n")
                        f.write(f"       Content Length: {len(item['content'])} chars\n")
                        content_preview = item['content'][:800] + "..." if len(
                            item['content']) > 800 else item['content']
                        f.write(f"       Content: {content_preview}\n")
                        
                        # Show content details if meaningful
                        if item.get('content_details'):
                            details = item['content_details']
                            meaningful_details = []
                            for key, value in details.items():
                                if key == 'annotations' and value:  # Only show if annotations exist
                                    meaningful_details.append(f"{key}({len(value)})")
                                elif key != 'annotations' and value:  # Show other non-empty details
                                    meaningful_details.append(key)
                            if meaningful_details:
                                f.write(f"       Details: {meaningful_details}\n")
                            
                        # Show raw item structure for debugging if content is empty
                        if not item['content'] and item.get('raw_item'):
                            raw_keys = list(item['raw_item'].keys())
                            f.write(f"       Raw item keys: {raw_keys}\n")
                            if 'content' in item['raw_item']:
                                f.write(f"       Raw content: {item['raw_item']['content']}\n")
                else:
                    f.write("  (No output items completed)\n")

                if result.get('error'):
                    f.write(f"\n❌ Error: {result['error']}\n")

                f.write("\n")

        print(f"📄 Consolidated report saved to: {report_file}")

        # Summary to console
        print("\n📊 FINAL SUMMARY:")
        print(
            f"✅ Successful scenarios: {len(successful_tests)}/{len(self.all_results)}")
        print(f"📦 Total output items completed: {total_output_items}")
        print(f"⏱️  Total test duration: {total_duration:.2f} seconds")
        print(f"📋 Output item types: {', '.join(all_types.keys())}")


async def main():
    runner = O3OutputItemTestRunner()
    await runner.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())
