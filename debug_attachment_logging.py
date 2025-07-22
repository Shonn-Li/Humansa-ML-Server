#!/usr/bin/env python3
"""Debug script to check attachment agent logging in test results"""

import httpx
import asyncio
import json
from datetime import datetime

async def test_attachment_agent():
    """Test attachment agent execution and logging"""
    base_url = "http://localhost:5001/v1/multi-agent/response"
    
    # Test case with attachment
    request = {
        "messages": [{"role": "user", "content": "What is this document about?"}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "stream": False,
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
    }
    
    print("="*60)
    print("ATTACHMENT AGENT DEBUG TEST")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print(f"Request: {json.dumps(request, indent=2)}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(base_url, json=request)
            
            if response.status_code == 200:
                data = response.json()
                
                print("\n" + "="*60)
                print("RESPONSE ANALYSIS")
                print("="*60)
                
                # Check metadata
                metadata = data.get("metadata", {})
                print(f"\n1. Metadata exists: {'✅' if metadata else '❌'}")
                
                # Check agent_results
                agent_results = metadata.get("agent_results", {})
                print(f"2. Agent results exists: {'✅' if agent_results else '❌'}")
                
                # List all agents in results
                print(f"\n3. All agents in results:")
                for agent_name, agent_data in agent_results.items():
                    print(f"   - {agent_name}: status={agent_data.get('status', 'unknown')}")
                
                # Check router decision
                router_decision = metadata.get("router_decision", {})
                print(f"\n4. Router decision:")
                print(f"   - Tool: {router_decision.get('selected_tool')}")
                print(f"   - Confidence: {router_decision.get('confidence')}")
                print(f"   - Reasoning: {router_decision.get('reasoning', 'N/A')[:100]}...")
                
                # Check for attachment agent specifically
                print(f"\n5. Attachment agent check:")
                attachment_in_results = "attachment_agent" in agent_results
                print(f"   - In agent_results: {'✅' if attachment_in_results else '❌'}")
                
                if attachment_in_results:
                    attach_data = agent_results["attachment_agent"]
                    print(f"   - Status: {attach_data.get('status')}")
                    print(f"   - Data keys: {list(attach_data.get('data', {}).keys())}")
                    
                    # Check attachment data details
                    attach_inner_data = attach_data.get('data', {})
                    if 'metadata' in attach_inner_data:
                        attach_meta = attach_inner_data['metadata']
                        print(f"   - Attachment count: {attach_meta.get('attachment_count', 0)}")
                        print(f"   - Context length: {attach_meta.get('context_length', 0)}")
                
                # Check enabled agents from router
                router_agent_data = agent_results.get("router_agent", {})
                if router_agent_data.get('status') == 'success':
                    router_data = router_agent_data.get('data', {})
                    enabled_agents = router_data.get('enabled_agents', [])
                    print(f"\n6. Enabled agents from router: {enabled_agents}")
                    print(f"   - Attachment enabled: {'✅' if 'attachment' in enabled_agents else '❌'}")
                
                # Check response content
                response_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"\n7. Response references attachment: {'✅' if 'arxiv' in response_content.lower() or 'paper' in response_content.lower() else '❌'}")
                print(f"   Response preview: {response_content[:200]}...")
                
                # Save full response for analysis
                with open("attachment_debug_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"\n8. Full response saved to: attachment_debug_response.json")
                
            else:
                print(f"\n❌ Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\nMake sure ML server is running on port 5001")
    print("Starting debug test in 3 seconds...\n")
    asyncio.run(asyncio.sleep(3))
    asyncio.run(test_attachment_agent())