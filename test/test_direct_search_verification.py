#!/usr/bin/env python3
"""
Direct test to verify if search results are being sent in output_item.done events
Uses curl or direct HTTP requests to the ML server
"""

import subprocess
import json
import sys

def test_search_with_curl():
    """Test search functionality using curl command"""
    
    print("="*80)
    print("DIRECT SEARCH VERIFICATION TEST")
    print("="*80)
    print("Target: http://localhost:5001/v1/chat/completions")
    print("Method: Using curl to make direct HTTP request")
    print("="*80)
    
    # Test case 1: Context Search
    print("\n1. Testing Context Search...")
    
    curl_command = [
        'curl', '-X', 'POST', 'http://localhost:5001/v1/chat/completions',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search my notes for PARL"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        })
    ]
    
    print("Command:", ' '.join(curl_command[:4]), "...")
    print("\nStreaming response:")
    print("-"*60)
    
    process = subprocess.Popen(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    output_items = []
    search_results_found = False
    
    for line in process.stdout:
        if line.strip():
            if line.startswith('data: '):
                data_str = line[6:].strip()
                if data_str != '[DONE]':
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")
                        
                        # Look for output_item events
                        if event_type == "response.output_item.added":
                            item = event.get("item", {})
                            print(f"→ Output item added: {item.get('type')} (id: {item.get('id')})")
                        
                        elif event_type == "response.output_item.done":
                            item = event.get("item", {})
                            output_items.append(item)
                            print(f"\n🔍 OUTPUT_ITEM.DONE:")
                            print(f"   Type: {item.get('type')}")
                            print(f"   ID: {item.get('id')}")
                            print(f"   Status: {item.get('status')}")
                            
                            # Check for result field
                            if 'result' in item:
                                print(f"   ✅ HAS RESULT FIELD!")
                                result = item['result']
                                if isinstance(result, dict) and ('results' in result or 'search_results' in result):
                                    search_results_found = True
                                    print(f"   🎯 SEARCH RESULTS FOUND!")
                                    print(f"   Result preview: {json.dumps(result, indent=2)[:200]}...")
                            else:
                                print(f"   ❌ NO RESULT FIELD")
                                
                    except json.JSONDecodeError:
                        pass
    
    print("-"*60)
    print("\nSummary:")
    print(f"Output items collected: {len(output_items)}")
    print(f"Search results in output_item.done: {'YES' if search_results_found else 'NO'}")
    
    if not search_results_found:
        print("\n❌ ISSUE CONFIRMED: Search results are NOT being included in output_item.done events")
        print("\nExpected structure in output_item.done:")
        print(json.dumps({
            "id": "cs_xxxxx",
            "type": "context_search_call",
            "status": "completed",
            "result": {
                "results": [
                    {
                        "title": "Note Title",
                        "content": "Note content...",
                        "score": 0.95,
                        "metadata": {}
                    }
                ]
            }
        }, indent=2))
    else:
        print("\n✅ Search results ARE being included in output_item.done events")
    
    return search_results_found

def test_with_python_requests():
    """Alternative test using Python requests library"""
    try:
        import requests
        
        print("\n\n2. Testing with Python requests library...")
        print("-"*60)
        
        url = "http://localhost:5001/v1/chat/completions"
        payload = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search the web for quantum computing 2025"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        }
        
        response = requests.post(url, json=payload, stream=True)
        
        output_items = []
        search_results_found = False
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str != '[DONE]':
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type", "")
                            
                            if event_type == "response.output_item.done":
                                item = event.get("item", {})
                                if item.get("type") == "web_search_call":
                                    print(f"\n🔍 Web Search Output Item Done:")
                                    print(f"   Full item: {json.dumps(item, indent=2)[:500]}...")
                                    
                                    if 'result' in item:
                                        search_results_found = True
                                        
                        except json.JSONDecodeError:
                            pass
        
        print(f"\nWeb search results in output_item.done: {'YES' if search_results_found else 'NO'}")
        return search_results_found
        
    except ImportError:
        print("\n⚠️  requests library not installed, skipping Python test")
        return False

if __name__ == "__main__":
    print("\n🔍 Testing ML Server Search Result Output")
    print("This test verifies if search results are being sent in output_item.done events\n")
    
    # Test with curl
    curl_result = test_search_with_curl()
    
    # Test with Python requests if available
    python_result = test_with_python_requests()
    
    # Final verdict
    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80)
    
    if not curl_result and not python_result:
        print("❌ CONFIRMED BUG: Search results are NOT being included in output_item.done events")
        print("\nThe ML server is completing search tool calls without including the actual search results.")
        print("This prevents the frontend from accessing the search data that was found.")
        print("\nFix needed in multi_agent_endpoint_v2.py:")
        print("- When completing context_search_call, include the search results")
        print("- When completing file_search_call, include the file search results")  
        print("- When completing web_search_call, include the web search results")
    else:
        print("✅ Search results ARE being properly included in output_item.done events")
    
    sys.exit(0 if (curl_result or python_result) else 1)