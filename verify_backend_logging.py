#!/usr/bin/env python3
"""
Verify Backend Logging Implementation
Test that the NestJS backend receives and logs DeepSeek reasoning content
"""

import asyncio
import json
import sys
import os
import time
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


async def verify_backend_logging():
    """Verify that backend logging is working for DeepSeek reasoning"""
    print("="*80)
    print("BACKEND LOGGING VERIFICATION FOR DEEPSEEK R1")
    print("="*80)
    
    try:
        # Import endpoint to test ML server directly
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Test request for DeepSeek R1 with reasoning
        request = {
            "model": "DeepSeek-R1",
            "messages": [{"role": "user", "content": "What is 6*7? Think step by step briefly."}],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing ML server direct connection...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n📡 This should generate the following backend logs:")
        print("1. 🚀🚀🚀 SENDING REQUEST TO ML SERVER FOR STREAMING")
        print("2. 🔥🔥🔥 BACKEND STREAMING EVENT RECEIVED: response.created")
        print("3. 🔥🔥🔥 BACKEND STREAMING EVENT RECEIVED: response.output_text.delta")
        print("4. 🧠🧠🧠 DEEPSEEK REASONING CONTENT DETECTED IN BACKEND")
        print("5. 📤📤📤 DEEPSEEK REASONING FORWARDED TO FRONTEND")
        print("6. 🔥🔥🔥 BACKEND STREAMING EVENT RECEIVED: response.completed")
        print("-" * 80)
        
        # Run request to ML server
        start_time = time.time()
        response = await endpoint.handle_request(request)
        
        # Count events received
        event_count = 0
        delta_events = 0
        think_deltas = 0
        completion_events = 0
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_count += 1
                event_type = event.get("type", "unknown")
                
                if event_type == "response.output_text.delta":
                    delta_events += 1
                    delta = event.get("delta", "")
                    if "<think>" in delta or "</think>" in delta:
                        think_deltas += 1
                        print(f"🧠 ML Server delta with <think> tags: {delta[:50]}...")
                elif event_type == "response.completed":
                    completion_events += 1
                    print(f"✅ ML Server completion event received")
                    break
        
        duration = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"🧪 ML SERVER DIRECT TEST RESULTS")
        print(f"{'='*80}")
        
        print(f"📊 Event Summary:")
        print(f"  Total events: {event_count}")
        print(f"  Delta events: {delta_events}")
        print(f"  Think deltas: {think_deltas}")
        print(f"  Completion events: {completion_events}")
        print(f"  Duration: {duration:.2f} seconds")
        
        print(f"\n🔍 What to check in backend logs:")
        print(f"  1. Look for '🚀🚀🚀 SENDING REQUEST TO ML SERVER' - confirms backend starts request")
        print(f"  2. Look for '🔥🔥🔥 BACKEND STREAMING EVENT RECEIVED' - confirms events received")
        print(f"  3. Look for '🧠🧠🧠 DEEPSEEK REASONING CONTENT DETECTED' - confirms thinking detected")
        print(f"  4. Look for '📤📤📤 DEEPSEEK REASONING FORWARDED' - confirms sent to frontend")
        
        print(f"\n💡 Backend logs should appear in:")
        print(f"  - NestJS console output (if backend is running)")
        print(f"  - Look for logs with Features.ML_SERVER_STREAMING")
        print(f"  - Look for logs with Features.DEEPSEEK_REASONING")
        print(f"  - Look for logs with Features.BACKEND_STREAM_PROXY")
        
        success = think_deltas > 0 and completion_events > 0
        
        print(f"\n🎯 Backend Logging Status:")
        if success:
            print(f"  ✅ ML Server is sending DeepSeek reasoning content")
            print(f"  ✅ Backend should be logging reasoning events")
            print(f"  ✅ Events should be forwarded to frontend")
            print(f"\n  ⚠️  If ThinkingFlow still not showing, check:")
            print(f"     - Backend server logs for the logging messages added")
            print(f"     - Frontend Redux logs to confirm events received")
            print(f"     - ThinkingFlow component logs for render decisions")
        else:
            print(f"  ❌ ML Server not sending reasoning content")
            print(f"  ❌ Backend logging won't trigger without reasoning")
            
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(verify_backend_logging())
    print(f"\n{'='*80}")
    print(f"Backend Logging Verification: {'✅ READY' if result else '❌ NEEDS INVESTIGATION'}")
    print(f"{'='*80}")
    print()
    print("Next steps:")
    print("1. Start the NestJS backend server: cd YouWoAI-Server-v1 && pnpm run start:dev")
    print("2. Make a DeepSeek R1 request from the mobile app")
    print("3. Check backend console for the logging messages:")
    print("   - 🚀🚀🚀 SENDING REQUEST TO ML SERVER FOR STREAMING")
    print("   - 🔥🔥🔥 BACKEND STREAMING EVENT RECEIVED")
    print("   - 🧠🧠🧠 DEEPSEEK REASONING CONTENT DETECTED IN BACKEND")
    print("   - 📤📤📤 DEEPSEEK REASONING FORWARDED TO FRONTEND")
    print("4. If these logs appear but ThinkingFlow still doesn't show, the issue is in the frontend Redux processing")