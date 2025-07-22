#!/usr/bin/env python3
"""
Extended Timeout Test for Multi-Agent System
Uses longer timeouts to allow complex queries to complete
"""

import asyncio
import sys
import os
import aiohttp
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def test_with_extended_timeout():
    """Test with extended timeouts to see if queries complete"""
    
    print("\n" + "="*60)
    print("EXTENDED TIMEOUT TEST")
    print("="*60)
    
    # Create session with very long timeout (5 minutes)
    timeout = aiohttp.ClientTimeout(total=300, connect=30, sock_read=300)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Test cases that were timing out
        test_cases = [
            {
                "name": "Context Search",
                "request": {
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": "Search my notes for information about PARL"}],
                    "stream": True,
                    "enable_citations": True,
                    "user_id": 10001
                }
            },
            {
                "name": "Multi-Agent Query",
                "request": {
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
                    "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                    "stream": True,
                    "enable_citations": True,
                    "user_id": 10001
                }
            }
        ]
        
        for test in test_cases:
            print(f"\n{'='*40}")
            print(f"Test: {test['name']}")
            print(f"Starting at: {datetime.now().strftime('%H:%M:%S')}")
            print("-"*40)
            
            try:
                start_time = datetime.now()
                
                # Import endpoint directly
                from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
                endpoint = MultiAgentChatEndpointV2()
                
                # Run request
                response = await endpoint.handle_request(test["request"])
                
                tools_used = []
                response_text = ""
                event_count = 0
                
                async for event in response:
                    event_count += 1
                    event_type = event.get("type", "")
                    
                    if event_type == "response.output_item.added":
                        item = event.get("item", {})
                        item_type = item.get("type")
                        if item_type and item_type.endswith("_call"):
                            tools_used.append(item_type)
                            elapsed = (datetime.now() - start_time).total_seconds()
                            print(f"  [{elapsed:.1f}s] Tool: {item_type}")
                    
                    elif event_type == "response.output_text.delta":
                        response_text += event.get("delta", "")
                    
                    # Show progress every 100 events
                    if event_count % 100 == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        print(f"  [{elapsed:.1f}s] Processed {event_count} events...")
                
                # Calculate total time
                total_time = (datetime.now() - start_time).total_seconds()
                
                print(f"\n✅ COMPLETED in {total_time:.1f} seconds")
                print(f"Tools used: {', '.join(tools_used)}")
                print(f"Response length: {len(response_text)} chars")
                print(f"Total events: {event_count}")
                
                # Show response preview
                if response_text:
                    print(f"\nResponse preview:")
                    print("-"*40)
                    print(response_text[:300] + ("..." if len(response_text) > 300 else ""))
                
            except asyncio.TimeoutError:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"\n❌ TIMEOUT after {elapsed:.1f} seconds")
                print("Even with 5-minute timeout, the request didn't complete")
                
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"\n❌ ERROR after {elapsed:.1f} seconds: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "="*60)
    print("FINDINGS:")
    print("- If tests complete: The issue was timeout being too short")
    print("- If tests still timeout: There's a deeper issue (infinite loop, deadlock, etc.)")
    print("- Check elapsed times to see how long operations actually take")
    print("="*60)


if __name__ == "__main__":
    # Use asyncio with debug mode to see more details
    asyncio.run(test_with_extended_timeout(), debug=True)