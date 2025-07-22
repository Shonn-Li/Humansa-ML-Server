#!/usr/bin/env python3
"""
Quick Test Script for Multi-Agent v1 Response Endpoint

This script provides a quick test of the multi-agent endpoint with basic scenarios.
Tests using User ID 3 as requested.

Usage:
    python test_multi_agent_quick.py
"""

import asyncio
import json
import aiohttp
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test configuration
ML_SERVER_URL = "http://localhost:5001"
MULTI_AGENT_ENDPOINT = f"{ML_SERVER_URL}/v1/multi-agent/response"

# Test user ID (using user ID 3 as requested)
TEST_USER_ID = 3


async def test_server_connection():
    """Test if the server is running and responding"""
    try:
        async with aiohttp.ClientSession() as session:
            # Try to test the multi-agent endpoint directly instead of root
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
                # Any response (including errors) means the server is running
                if response.status in [200, 400, 500]:
                    print("✅ Server is running")
                    return True
                else:
                    print(
                        f"❌ Server returned unexpected status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Server connection failed: {str(e)}")
        return False


async def test_multi_agent_endpoint():
    """Quick test of the multi-agent endpoint"""

    print("🚀 Quick Multi-Agent Endpoint Test")
    print("=" * 40)
    print(f"Server: {ML_SERVER_URL}")
    print(f"User ID: {TEST_USER_ID}")
    print("=" * 40)

    # Test cases
    test_cases = [
        {
            "name": "Simple Non-Streaming",
            "request": {
                "messages": [
                    {"role": "user", "content": "Hello! Can you introduce yourself?"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False,
                "enable_citations": False,
                "completion_type": "system"
            }
        },
        {
            "name": "Empty Notes/Conversations",
            "request": {
                "messages": [
                    {"role": "user", "content": "What can you tell me about my notes?"}
                ],
                "user_id": TEST_USER_ID,
                "model": "gpt-4.1-nano",
                "stream": False,
                "note_ids": [],
                "conversation_ids": [],
                "enable_citations": True,
                "completion_type": "system"
            }
        }
    ]

    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print("-" * 30)

            try:
                async with session.post(
                    MULTI_AGENT_ENDPOINT,
                    json=test_case["request"],
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status == 200:
                        result = await response.json()

                        # Check if it's a valid response
                        if result.get("status") == "success":
                            print("✅ Test passed!")

                            # Print basic info
                            data = result.get("data", {})
                            usage = data.get("usage", {})

                            print(
                                f"   • Response length: {len(data.get('response', ''))}")
                            print(
                                f"   • Workflow time: {usage.get('workflow_time', 0):.2f}s")
                            print(
                                f"   • Enabled agents: {usage.get('enabled_agents', [])}")

                            # Print response preview
                            response_text = data.get("response", "")
                            if response_text:
                                preview = response_text[:100] + "..." if len(
                                    response_text) > 100 else response_text
                                print(f"   • Response preview: {preview}")

                        else:
                            print(
                                f"❌ Test failed: {result.get('error', 'Unknown error')}")

                    else:
                        error_text = await response.text()
                        print(f"❌ HTTP Error {response.status}: {error_text}")

            except Exception as e:
                print(f"❌ Test failed with exception: {str(e)}")

if __name__ == "__main__":
    async def main():
        # Check server connection first
        if not await test_server_connection():
            print("\n❌ Cannot connect to server. Please start the ML server first.")
            sys.exit(1)

        # Run the tests
        await test_multi_agent_endpoint()
        print("\n✅ Quick test complete!")

    # Run the async main function
    asyncio.run(main())
