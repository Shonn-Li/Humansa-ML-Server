#!/usr/bin/env python3
"""Quick test for appointment form system"""

import requests
import json
import sys

BASE_URL = "http://localhost:5001"

def test_appointment():
    """Test basic appointment flow"""
    print("Testing appointment form system...")
    
    # Test 1: Simple appointment request
    print("\n1. Testing simple appointment request...")
    response = requests.post(
        f"{BASE_URL}/v2/humansa/responses/create",
        json={
            "model": "gpt-4-turbo",
            "input": "我想预约李明医生明天上午9点看头痛",
            "user_id": "test_user_123"
        },
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    print(f"✓ Response ID: {data.get('id')}")
    
    # Extract output
    output_texts = []
    has_tool_use = False
    
    if "output" in data:
        for item in data["output"]:
            if item.get("type") == "text":
                output_texts.append(item.get("text", ""))
            elif item.get("type") == "tool_use":
                has_tool_use = True
                tool_name = item.get("tool_use", {}).get("name", "")
                print(f"✓ Tool used: {tool_name}")
    
    full_output = " ".join(output_texts)
    print(f"\nResponse: {full_output[:200]}...")
    
    # Check for form creation indicators
    has_preview = "预约信息" in full_output
    has_doctor = "李明" in full_output
    has_time = "明天" in full_output or "上午" in full_output
    asks_confirmation = "确认" in full_output
    
    print(f"\n✓ Has preview: {has_preview}")
    print(f"✓ Has doctor info: {has_doctor}")
    print(f"✓ Has time info: {has_time}")
    print(f"✓ Asks for confirmation: {asks_confirmation}")
    
    # Check metadata for form_id
    form_id = None
    if "metadata" in data:
        form_id = data["metadata"].get("form_id")
        if form_id:
            print(f"✓ Form ID in metadata: {form_id}")
    
    # Look for form_id in output
    if not form_id:
        import re
        for text in output_texts:
            match = re.search(r'form_[a-f0-9]{12}', text)
            if match:
                form_id = match.group(0)
                print(f"✓ Form ID found in text: {form_id}")
                break
    
    # Test 2: Confirm appointment
    if asks_confirmation and data.get("id"):
        print("\n2. Testing appointment confirmation...")
        
        confirm_response = requests.post(
            f"{BASE_URL}/v2/humansa/responses/create",
            json={
                "model": "gpt-4-turbo",
                "input": "确认",
                "user_id": "test_user_123",
                "previous_response_id": data["id"]
            },
            headers={"Content-Type": "application/json"}
        )
        
        if confirm_response.status_code == 200:
            confirm_data = confirm_response.json()
            confirm_texts = []
            
            if "output" in confirm_data:
                for item in confirm_data["output"]:
                    if item.get("type") == "text":
                        confirm_texts.append(item.get("text", ""))
            
            confirm_output = " ".join(confirm_texts)
            
            # Check for confirmation
            has_success = "成功" in confirm_output
            match = re.search(r'APT-\d+', confirm_output)
            has_confirmation_code = match is not None
            
            if has_confirmation_code:
                print(f"✓ Booking confirmed! Code: {match.group(0)}")
            else:
                print(f"✗ No confirmation code found")
                print(f"Response: {confirm_output[:200]}...")
    
    return True

if __name__ == "__main__":
    try:
        success = test_appointment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)