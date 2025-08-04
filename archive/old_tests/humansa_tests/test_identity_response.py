#!/usr/bin/env python3
"""
Test identity response handling in Pattern 2
"""

import asyncio
import json
import aiohttp

API_URL = "http://localhost:6001/v2/humansa/responses/create"

async def test_identity():
    """Test identity queries"""
    
    test_queries = [
        "你是谁？",
        "介绍一下诺亚新舟",
        "什么是小诺？",
        "你们公司的口号是什么？"
    ]
    
    async with aiohttp.ClientSession() as session:
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}")
            
            request_data = {
                "model": "gpt-4-turbo",
                "input": query,
                "user_id": "test_identity_001"
            }
            
            async with session.post(API_URL, json=request_data) as response:
                result = await response.json()
                
                # Extract text from output
                output = result.get("output", [])
                text = ""
                for item in output:
                    if item.get("type") == "output_text":
                        text = item.get("text", "")
                        break
                
                print(f"Response: {text}")
                
                # Check for keywords
                keywords = ["诺亚新舟", "小诺", "以爱行舟", "亲近相守"]
                found = [kw for kw in keywords if kw in text]
                print(f"\nFound keywords: {found}")
                
                # Check metadata
                metadata = result.get("metadata", {})
                print(f"Response agent processed: {metadata.get('response_agent_processed')}")
                print(f"Response type: {metadata.get('response_type')}")

if __name__ == "__main__":
    print("Testing Identity Response Handling")
    asyncio.run(test_identity())