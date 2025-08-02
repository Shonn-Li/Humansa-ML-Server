#!/usr/bin/env python3
"""
Direct test of workflow orchestrator
"""

import json
import urllib.request
import urllib.error
from datetime import datetime


def test_workflow_orchestrator():
    """Test workflow orchestrator directly"""
    base_url = "http://localhost:6001"
    
    # First check if workflow is enabled
    print("Checking orchestrator status...")
    
    # Simple product query that should trigger ProductAgent
    query = "童年故事DHA"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_workflow_direct",
        "stream": False,
        "temperature": 0.1,
        "metadata": {
            "orchestrator": "workflow",
            "force_workflow": True
        }
    }
    
    print(f"\n{'='*60}")
    print(f"Testing Workflow Orchestrator Directly")
    print(f"Query: {query}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*60}\n")
    
    # Make request
    try:
        req = urllib.request.Request(
            f"{base_url}/v1-humansa/chat/completions",
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract content
            content = ""
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            
            print("Response:")
            print("-" * 60)
            print(content)
            print("-" * 60)
            
            # Check response structure
            print(f"\n{'='*60}")
            print("Response Analysis:")
            
            # Look for signs of workflow orchestrator
            workflow_signs = [
                "Thought:",
                "Action:",
                "Observation:",
                "call_productagent",
                "call_generalagent",
                "call_appointmentagent"
            ]
            
            found_workflow = any(sign in content for sign in workflow_signs)
            
            # Look for signs of old tools
            old_tool_signs = [
                "recommend_product",
                "search_doctor",
                "book_appointment"
            ]
            
            found_old_tools = any(sign in content for sign in old_tool_signs)
            
            print(f"✅ Workflow orchestrator patterns found" if found_workflow else "❌ No workflow patterns")
            print(f"❌ Old tool patterns found (BAD)" if found_old_tools else "✅ No old tool patterns")
            
            # Check for product info
            has_products = any(p in content for p in ['童年故事', 'DHA', '藻油'])
            print(f"✅ Product info found" if has_products else "❌ No product info")
            
            print(f"{'='*60}\n")
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}")
        error_data = e.read().decode('utf-8')
        print(f"Error: {error_data[:500]}")
    except Exception as e:
        print(f"❌ Error: {e}")


def check_v2_health():
    """Check V2 health endpoint"""
    base_url = "http://localhost:6001"
    
    try:
        req = urllib.request.Request(f"{base_url}/v1-humansa/v2/health")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("V2 Health Status:")
            print(json.dumps(data, indent=2))
            
            # Check for workflow orchestrator
            if 'components' in data:
                if 'workflow_orchestrator' in data['components']:
                    print("\n✅ Workflow orchestrator is enabled!")
                else:
                    print("\n❌ Workflow orchestrator not found in components")
            
    except Exception as e:
        print(f"Health check failed: {e}")


if __name__ == "__main__":
    print("\n🧪 Testing Workflow Orchestrator\n")
    
    # Check health first
    check_v2_health()
    
    print("\n" + "="*60 + "\n")
    
    # Test workflow orchestrator
    test_workflow_orchestrator()
    
    print("\n✅ Test completed!\n")