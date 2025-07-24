#!/usr/bin/env python3
"""Test context search functionality"""

import asyncio
import requests
import json

async def test_context_search():
    # Start test ML server on port 5002
    url = "http://localhost:5002/v1/multi-agent/response"
    
    # Test request
    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "Tell me about AI startups"
            }
        ],
        "user_id": 10001,
        "enable_rag": True,
        "stream": False
    }
    
    print("Sending request to multi-agent endpoint...")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    response = requests.post(url, json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        print("\nResponse received:")
        print(json.dumps(result, indent=2))
        
        # Check agent trace
        if "agent_trace" in result:
            print("\n=== Agent Trace ===")
            for agent in result["agent_trace"]:
                print(f"\nAgent: {agent['agent']}")
                print(f"Status: {agent['status']}")
                if "result" in agent:
                    if agent["agent"] == "context_search":
                        print(f"Found notes: {agent['result'].get('metadata', {}).get('note_ids', [])}")
                        print(f"Total chunks: {agent['result'].get('metadata', {}).get('total_chunks', 0)}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("Make sure the test ML server is running on port 5002:")
    print("python test_server.py")
    print("\nTesting context search...\n")
    asyncio.run(test_context_search())