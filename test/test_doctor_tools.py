#!/usr/bin/env python3
"""
Test script for Humansa agentic endpoint with doctor tool calls.
Tests the cleaned-up endpoint that uses direct agent responses without LLM post-processing.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


async def test_humansa_endpoint_direct():
    """Test the Humansa endpoint directly with medical appointment booking"""

    # Test requests for different scenarios
    test_scenarios = [
        {
            "name": "Introduction Test",
            "description": "Test self-introduction when user greets",
            "messages": [
                {
                    "role": "user",
                    "content": "你好，请介绍一下你自己"
                }
            ],
            "expected": "Should introduce as Humansa AI assistant with company background"
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
            "expected": "Should use find_doctor_availability and related tools"
        },
        {
            "name": "Mixed Request Test",
            "description": "Test medical + web search combination",
            "messages": [
                {
                    "role": "user",
                    "content": "帮我预约个最近一周的医生，要在深圳的, 然后帮我看看最近的新闻"
                }
            ],
            "expected": "Should use medical tools + web search tools"
        }
    ]

    # Base request template
    base_request = {
        "model": "gpt-4.1-nano",
        "user_id": 43,
        "conversation_id": 999,
        "enable_rag": True,
        "enable_citations": True,
        "enable_web_search": True,  # Enable for mixed tests
        "enable_title_generation": False,
        "stream": True,
        "completion_type": "humansa",
        "attachments": [],
        "enable_realtime_streaming": True
    }

#!/usr/bin/env python3
"""
Test script for Humansa agentic endpoint with doctor tool calls.
Tests the cleaned-up endpoint that uses direct agent responses without LLM post-processing.
"""


async def test_single_scenario(session, scenario, scenario_num, total_scenarios):
    """Test a single scenario against the Humansa endpoint"""

    print(f"\n{'='*60}")
    print(f"🧪 SCENARIO {scenario_num}/{total_scenarios}: {scenario['name']}")
    print(f"📝 Description: {scenario['description']}")
    print(f"❓ Query: {scenario['messages'][0]['content']}")
    print(f"🎯 Expected: {scenario['expected']}")
    print(f"{'='*60}")

    # Build test request
    test_request = {
        "messages": scenario['messages'],
        "model": "gpt-4.1-nano",
        "user_id": 43,
        "conversation_id": 999 + scenario_num,
        "enable_rag": True,
        "enable_citations": True,
        "enable_web_search": scenario.get('enable_web_search', True),
        "enable_title_generation": False,
        "stream": True,
        "completion_type": "humansa",
        "attachments": [],
        "enable_realtime_streaming": True
    }

    # Output file with timestamp and scenario name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = scenario['name'].replace(" ", "_").lower()
    output_file = f"humansa_test_{safe_name}_{timestamp}.txt"

    try:
        start_time = time.time()

        async with session.post(
            "http://localhost:5001/humansa/response",
            json=test_request,
            headers={"Content-Type": "application/json"}
        ) as response:

            print(f"📊 Response status: {response.status}")
            print(f"📊 Content-Type: {response.headers.get('Content-Type')}")

            if response.status != 200:
                error_text = await response.text()
                print(f"❌ Error response: {error_text}")
                return {
                    "scenario": scenario['name'],
                    "success": False,
                    "error": error_text,
                    "duration": time.time() - start_time
                }

            # Track metrics
            metrics = {
                "scenario": scenario['name'],
                "success": True,
                "event_count": 0,
                "total_text_length": 0,
                "reasoning_count": 0,
                "tool_call_count": 0,
                "function_call_count": 0,
                "medical_events": 0,
                "introduction_detected": False,
                "tools_used": [],
                "duration": 0
            }

            # Track all output items for detailed analysis
            # Format: {"index": int, "type": str, "id": str, "content": str, "status": str}
            output_items = []
            current_output_items = {}  # Track by item_id for updates

            # Medical and introduction keywords
            medical_keywords = ["医生", "预约", "appointment",
                                "doctor", "clinic", "medical", "深圳", "诊所"]
            intro_keywords = ["humansa", "诺亚新舟", "ai智能助理", "以爱行舟", "三甲", "专家"]

            # Open output file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(
                    f"=== HUMANSA ENDPOINT TEST - {scenario['name'].upper()} ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Query: {scenario['messages'][0]['content']}\n")
                f.write(f"Expected: {scenario['expected']}\n")
                f.write(
                    f"Request: {json.dumps(test_request, indent=2, ensure_ascii=False)}\n")
                f.write(f"Response Status: {response.status}\n")
                f.write(
                    f"Content-Type: {response.headers.get('Content-Type')}\n")
                f.write(
                    f"======================================================\n\n")

                # Read streaming response
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()

                    if not line_str:
                        continue

                    # Parse new canonical format
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Remove "data: "

                        # Check for completion signal
                        if data_str == "[DONE]":
                            metrics["duration"] = time.time() - start_time
                            print(
                                f"🏁 Stream completed. Total events: {metrics['event_count']}")
                            print(
                                f"📝 Total text: {metrics['total_text_length']} chars")
                            print(
                                f"🧠 Reasoning: {metrics['reasoning_count']} chunks")
                            print(
                                f"🔧 Tools: {metrics['tool_call_count']} calls")
                            print(
                                f"🏥 Medical events: {metrics['medical_events']}")
                            print(
                                f"👋 Introduction: {'✅' if metrics['introduction_detected'] else '❌'}")
                            f.write(f"=== STREAM COMPLETED ===\n")
                            break

                        # Parse JSON data
                        try:
                            parsed_data = json.loads(data_str)
                            metrics["event_count"] += 1

                            # Get event type
                            event_type = parsed_data.get(
                                'event', parsed_data.get('type', 'unknown'))

                            # Check for medical and introduction content
                            event_text = json.dumps(
                                parsed_data, ensure_ascii=False).lower()
                            is_medical = any(
                                keyword in event_text for keyword in medical_keywords)
                            is_intro = any(
                                keyword in event_text for keyword in intro_keywords)

                            # Track output items for detailed analysis
                            if event_type == "response.output_item.added":
                                item = parsed_data.get('item', {})
                                output_index = parsed_data.get(
                                    'output_index', -1)
                                item_id = item.get('id', 'unknown')
                                item_type = item.get('type', 'unknown')

                                output_item = {
                                    "index": output_index,
                                    "type": item_type,
                                    "id": item_id,
                                    "content": "",
                                    "status": item.get('status', 'in_progress'),
                                    "events": []
                                }
                                output_items.append(output_item)
                                current_output_items[item_id] = output_item

                            elif event_type in ["response.reasoning_text.delta", "response.reasoning_text.done"]:
                                item_id = parsed_data.get('item_id', '')
                                if item_id in current_output_items:
                                    if event_type == "response.reasoning_text.delta":
                                        delta = parsed_data.get('delta', '')
                                        current_output_items[item_id]["content"] += delta
                                        current_output_items[item_id]["events"].append(
                                            f"Delta: {delta[:50]}...")
                                    elif event_type == "response.reasoning_text.done":
                                        text = parsed_data.get('text', '')
                                        # Final content
                                        current_output_items[item_id]["content"] = text
                                        current_output_items[item_id]["events"].append(
                                            f"Done: {text[:50]}...")

                            elif event_type == "response.output_text.delta":
                                item_id = parsed_data.get('item_id', '')
                                if item_id in current_output_items:
                                    delta = parsed_data.get('delta', '')
                                    current_output_items[item_id]["content"] += delta
                                    current_output_items[item_id]["events"].append(
                                        f"Delta: {delta[:50]}...")

                            elif event_type == "response.function_tool_result.delta":
                                item_id = parsed_data.get('item_id', '')
                                if item_id in current_output_items:
                                    delta = parsed_data.get('delta', '')
                                    current_output_items[item_id]["content"] += delta
                                    current_output_items[item_id]["events"].append(
                                        f"Tool Result: {delta[:30]}...")

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

                            if is_medical:
                                metrics["medical_events"] += 1
                            if is_intro:
                                metrics["introduction_detected"] = True

                            # Track different event types
                            if event_type == "response.output_text.delta":
                                delta = parsed_data.get(
                                    'data', {}).get('delta', '')
                                metrics["total_text_length"] += len(delta)

                                if is_intro:
                                    print(
                                        f"��💬 Introduction Text: '{delta[:50]}{'...' if len(delta) > 50 else ''}'")
                                elif is_medical:
                                    print(
                                        f"🏥💬 Medical Text: '{delta[:50]}{'...' if len(delta) > 50 else ''}'")
                                else:
                                    print(
                                        f"💬 Text: '{delta[:30]}{'...' if len(delta) > 30 else ''}'")

                            elif event_type == "response.reasoning_text.delta":
                                delta = parsed_data.get(
                                    'data', {}).get('delta', '')
                                metrics["reasoning_count"] += 1
                                print(
                                    f"🧠 Reasoning: '{delta[:40]}{'...' if len(delta) > 40 else ''}'")

                            elif "function" in event_type or "tool" in event_type:
                                metrics["function_call_count"] += 1
                                metrics["tool_call_count"] += 1

                                # Extract function/tool name
                                func_name = (parsed_data.get('data', {}).get('item', {}).get('name', '') or
                                             parsed_data.get('data', {}).get('name', '') or
                                             parsed_data.get('item', {}).get('name', '') or
                                             parsed_data.get('name', ''))

                                if func_name and func_name not in metrics["tools_used"]:
                                    metrics["tools_used"].append(func_name)

                                if any(keyword in func_name.lower() for keyword in ["doctor", "appointment", "medical", "clinic"]):
                                    print(
                                        f"🏥🔧 Medical Tool: {event_type} - {func_name}")
                                else:
                                    print(
                                        f"🔧 Tool: {event_type} - {func_name}")

                            elif event_type == "response.created":
                                print(f"🚀 Response Created")
                            elif event_type == "response.in_progress":
                                print(f"⏳ Response In Progress")
                            elif event_type == "response.completed":
                                print(f"✅ Response Completed")
                            else:
                                marker = "🏥" if is_medical else "👋" if is_intro else ""
                                print(f"{marker}📨 Event: {event_type}")

                            # Write to file
                            status = "🏥 MEDICAL" if is_medical else "👋 INTRO" if is_intro else ""
                            f.write(
                                f"EVENT #{metrics['event_count']}: {event_type} {status}\n")
                            f.write(
                                f"{json.dumps(parsed_data, indent=2, ensure_ascii=False)}\n\n")

                        except json.JSONDecodeError as e:
                            print(f"❌ JSON Parse Error: {e}")
                            f.write(
                                f"EVENT #{metrics['event_count']}: PARSE ERROR\n")
                            f.write(f"Raw Data: {data_str}\n")
                            f.write(f"Error: {e}\n\n")

                # Write summary
                f.write(f"=== TEST SUMMARY ===\n")
                f.write(f"Scenario: {scenario['name']}\n")
                f.write(f"Total events: {metrics['event_count']}\n")
                f.write(
                    f"Total text length: {metrics['total_text_length']} characters\n")
                f.write(f"Reasoning chunks: {metrics['reasoning_count']}\n")
                f.write(f"Tool calls: {metrics['tool_call_count']}\n")
                f.write(f"Function calls: {metrics['function_call_count']}\n")
                f.write(f"Medical events: {metrics['medical_events']}\n")
                f.write(
                    f"Introduction detected: {metrics['introduction_detected']}\n")
                f.write(f"Tools used: {', '.join(metrics['tools_used'])}\n")
                f.write(f"Duration: {metrics['duration']:.2f} seconds\n\n")

                # Write detailed output item analysis
                f.write(f"=== DETAILED OUTPUT ITEM ANALYSIS ===\n")
                f.write(f"Total output items: {len(output_items)}\n\n")

                # Group items by type for analysis
                items_by_type = {}
                for item in output_items:
                    item_type = item['type']
                    if item_type not in items_by_type:
                        items_by_type[item_type] = []
                    items_by_type[item_type].append(item)

                # Write summary by type
                f.write("📊 OUTPUT ITEMS BY TYPE:\n")
                for item_type, items in items_by_type.items():
                    f.write(f"  {item_type}: {len(items)} items\n")
                f.write("\n")

                # Write each output item in detail
                for i, item in enumerate(output_items):
                    f.write(f"OUTPUT ITEM #{i+1}:\n")
                    f.write(f"  Index: {item['index']}\n")
                    f.write(f"  Type: {item['type']}\n")
                    f.write(f"  ID: {item['id']}\n")
                    f.write(f"  Status: {item['status']}\n")
                    f.write(
                        f"  Content Length: {len(item['content'])} chars\n")
                    f.write(
                        f"  Content Preview: {item['content'][:100]}{'...' if len(item['content']) > 100 else ''}\n")
                    f.write(f"  Events: {len(item['events'])}\n")
                    # Show first 5 events
                    for j, event in enumerate(item['events'][:5]):
                        f.write(f"    Event {j+1}: {event}\n")
                    if len(item['events']) > 5:
                        f.write(
                            f"    ... and {len(item['events']) - 5} more events\n")
                    f.write("\n")

                # Detect duplicates
                f.write("🔍 DUPLICATE ANALYSIS:\n")
                content_groups = {}
                for item in output_items:
                    if item['type'] == 'reasoning':  # Focus on reasoning duplicates
                        content = item['content'].strip()
                        if content:
                            if content not in content_groups:
                                content_groups[content] = []
                            content_groups[content].append(item)

                duplicates_found = False
                for content, items in content_groups.items():
                    if len(items) > 1:
                        duplicates_found = True
                        f.write(
                            f"  DUPLICATE REASONING CONTENT ({len(items)} items):\n")
                        f.write(
                            f"    Content: {content[:100]}{'...' if len(content) > 100 else ''}\n")
                        f.write(
                            f"    Items: {[f'#{item['index']} ({item['id']})' for item in items]}\n\n")

                if not duplicates_found:
                    f.write("  ✅ No duplicate reasoning content found\n\n")

                # Tool call sequence analysis
                f.write("🔧 TOOL CALL SEQUENCE:\n")
                tool_items = [item for item in output_items if item['type'] in [
                    'function_tool_call', 'function_tool_result']]
                if tool_items:
                    for i, item in enumerate(tool_items):
                        f.write(
                            f"  Tool {i+1}: {item['type']} - Index {item['index']} - {item['id']}\n")
                        if item['content']:
                            f.write(
                                f"    Content: {item['content'][:80]}{'...' if len(item['content']) > 80 else ''}\n")
                else:
                    f.write("  No tool calls found\n")
                f.write("\n")

                # Final assistant message analysis
                message_items = [
                    item for item in output_items if item['type'] == 'message']
                if message_items:
                    f.write("💬 FINAL ASSISTANT MESSAGES:\n")
                    for item in message_items:
                        f.write(f"  Message: {item['content']}\n")
                else:
                    f.write("💬 No final assistant messages found\n")

            print(f"📄 Output saved to: {output_file}")
            return metrics

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "scenario": scenario['name'],
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time
        }


async def test_humansa_endpoint():
    """Test the Humansa endpoint with multiple scenarios"""

    # Test scenarios
    test_scenarios = [
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
            "expected": "Should use find_doctor_availability and related tools",
            "enable_web_search": False
        },
        {
            "name": "Mixed Request Test",
            "description": "Test medical + web search combination",
            "messages": [
                {
                    "role": "user",
                    "content": "帮我预约个最近一周的医生，要在深圳的, 然后帮我看看最近的新闻"
                }
            ],
            "expected": "Should use medical tools + web search tools",
            "enable_web_search": True
        }
    ]

    print(f"🧪 Testing Humansa Agentic Endpoint - Direct Agent Responses")
    print(f"🌐 Endpoint: http://localhost:5001/humansa/response")
    print(f"📊 Test scenarios: {len(test_scenarios)}")
    print(f"🎯 Testing cleaned-up architecture (no post-agent LLM)")

    overall_start = time.time()
    results = []

    try:
        async with aiohttp.ClientSession() as session:
            for i, scenario in enumerate(test_scenarios, 1):
                result = await test_single_scenario(session, scenario, i, len(test_scenarios))
                results.append(result)

                # Brief pause between tests
                if i < len(test_scenarios):
                    await asyncio.sleep(2)

        # Final summary
        overall_duration = time.time() - overall_start
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]

        print(f"\n{'='*60}")
        print(f"🎯 FINAL TEST SUMMARY")
        print(f"{'='*60}")
        print(f"📊 Total scenarios: {len(test_scenarios)}")
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        print(f"⏱️  Total duration: {overall_duration:.2f} seconds")

        for result in successful:
            print(
                f"✅ {result['scenario']}: {result.get('event_count', 0)} events, {result.get('tool_call_count', 0)} tools")

        for result in failed:
            print(
                f"❌ {result['scenario']}: {result.get('error', 'Unknown error')}")

        # Check specific functionality
        intro_tests = [r for r in successful if 'introduction' in r['scenario'].lower(
        ) and r.get('introduction_detected', False)]
        medical_tests = [r for r in successful if 'doctor' in r['scenario'].lower(
        ) and r.get('medical_events', 0) > 0]

        print(f"\n🔍 FUNCTIONALITY ANALYSIS:")
        print(
            f"👋 Introduction functionality: {'✅ WORKING' if intro_tests else '❌ NOT WORKING'}")
        print(
            f"🏥 Medical tools functionality: {'✅ WORKING' if medical_tests else '❌ NOT WORKING'}")

        if len(successful) == len(test_scenarios):
            print(f"\n🎉 ALL TESTS PASSED! Humansa endpoint is working correctly.")
        else:
            print(f"\n⚠️  Some tests failed. Check individual logs for details.")

    except Exception as e:
        print(f"❌ Overall test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Starting Humansa Agentic Endpoint Test Suite...")
    asyncio.run(test_humansa_endpoint())
