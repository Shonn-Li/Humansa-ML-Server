#!/usr/bin/env python3
"""
Direct test of Response Agent functionality
"""

import sys
import os

# Add the src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from humansa.v2.response_agent import HumansaResponseAgent
import json

def test_response_agent():
    """Test the Response Agent directly"""
    
    print("\n" + "="*80)
    print("  Direct Response Agent Test")
    print("="*80 + "\n")
    
    # Initialize Response Agent
    agent = HumansaResponseAgent()
    
    # Test cases
    test_cases = [
        {
            "query": "你是谁？",
            "raw_response": {
                "id": "test_1",
                "output": [
                    {"type": "text", "text": "我是一个AI助手。"}
                ],
                "usage": {"total_tokens": 10}
            },
            "expected_type": "identity"
        },
        {
            "query": "你好",
            "raw_response": {
                "id": "test_2",
                "output": [
                    {"type": "text", "text": "你好！有什么可以帮助你的吗？"}
                ],
                "usage": {"total_tokens": 15}
            },
            "expected_type": "greeting"
        },
        {
            "query": "我想买保健品",
            "raw_response": {
                "id": "test_3",
                "output": [
                    {"type": "text", "text": "我们有很多保健品可以选择。"}
                ],
                "usage": {"total_tokens": 20}
            },
            "expected_type": "product"
        },
        {
            "query": "我现在胸痛很厉害",
            "raw_response": {
                "id": "test_4",
                "output": [
                    {"type": "text", "text": "这是紧急情况，建议您立即就医。"}
                ],
                "usage": {"total_tokens": 25}
            },
            "expected_type": "emergency"
        },
        {
            "query": "深圳有哪些诊所？",
            "raw_response": {
                "id": "test_5",
                "output": [
                    {"type": "text", "text": "relation \"humansa_clinics\" does not exist"}
                ],
                "usage": {"total_tokens": 30}
            },
            "expected_type": "general"
        }
    ]
    
    # Run tests
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['query']}")
        print("-" * 40)
        
        # Process response
        processed = agent.process_response(
            raw_response=test['raw_response'],
            query=test['query'],
            user_id="test_user"
        )
        
        # Extract processed text
        output_text = ""
        for item in processed.get('output', []):
            if item.get('type') == 'text':
                output_text = item.get('text', '')
                break
        
        # Check metadata
        metadata = processed.get('metadata', {})
        response_type = metadata.get('response_type', 'unknown')
        agent_processed = metadata.get('response_agent_processed', False)
        
        print(f"Original: {test['raw_response']['output'][0]['text'][:50]}...")
        print(f"Processed: {output_text[:100]}...")
        print(f"Response Type: {response_type} (expected: {test['expected_type']})")
        print(f"Agent Processed: {agent_processed}")
        
        # Check for key elements
        if "诺亚新舟" in output_text or "小诺" in output_text:
            print("✅ Brand identity present")
        else:
            print("❌ Brand identity missing")
        
        if response_type == test['expected_type']:
            print("✅ Correct response type detected")
        else:
            print("❌ Wrong response type")
    
    print("\n" + "="*80)
    print("  Test Complete")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_response_agent()