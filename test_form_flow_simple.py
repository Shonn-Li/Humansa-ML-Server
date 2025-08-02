#!/usr/bin/env python3
"""
Simple test for the appointment form flow
"""

import requests
import json
import time

BASE_URL = "http://localhost:6001"

def test_appointment_flow():
    """Test complete appointment flow"""
    print("=== Testing Appointment Form Flow ===\n")
    
    # Step 1: Create appointment with complete info
    print("1. Creating appointment...")
    response = requests.post(f"{BASE_URL}/v2/humansa/responses/create", json={
        "model": "gpt-4-turbo",
        "input": "我想预约李明医生明天上午9点看头痛，我叫张三，电话13800138000",
        "user_id": "test_user_flow"
    })
    
    data = response.json()
    print(f"Response ID: {data['id']}")
    print(f"Form ID: {data.get('metadata', {}).get('form_id')}")
    print(f"Output: {data['output'][0]['text'][:200]}...\n")
    
    form_id = data.get('metadata', {}).get('form_id')
    if not form_id:
        print("❌ No form_id in response!")
        return
    
    # Check if it's asking for confirmation
    if "确认" in data['output'][0]['text']:
        print("✓ System is asking for confirmation\n")
        
        # Step 2: Confirm appointment
        print("2. Confirming appointment...")
        response2 = requests.post(f"{BASE_URL}/v2/humansa/responses/create", json={
            "model": "gpt-4-turbo", 
            "input": "确认",
            "user_id": "test_user_flow",
            "previous_response_id": data['id']
        })
        
        data2 = response2.json()
        print(f"Output: {data2['output'][0]['text'][:200]}...\n")
        
        # Check for confirmation code
        text = data2['output'][0]['text']
        if "APT-" in text:
            # Extract confirmation code
            import re
            codes = re.findall(r'APT-\d+', text)
            if codes:
                print(f"✓ Got confirmation code: {codes[0]}")
            else:
                print("❌ No confirmation code found")
        else:
            print("❌ No confirmation code in response")
    else:
        print("❌ System didn't ask for confirmation")
    
    # Step 3: Test form API directly
    print("\n3. Testing form API directly...")
    
    # Get form
    form_response = requests.get(f"{BASE_URL}/v1-humansa/forms/{form_id}")
    if form_response.status_code == 200:
        form_data = form_response.json()
        print(f"✓ Form retrieved: {json.dumps(form_data['form']['form_data'], ensure_ascii=False, indent=2)}")
    else:
        print(f"❌ Failed to get form: {form_response.status_code}")
    
    # Confirm form via API
    confirm_response = requests.post(f"{BASE_URL}/v1-humansa/forms/{form_id}/confirm")
    if confirm_response.status_code == 200:
        confirm_data = confirm_response.json()
        if confirm_data.get('success'):
            print(f"✓ Form confirmed via API")
            print(f"  Confirmation code: {confirm_data.get('booking_result', {}).get('confirmation_code')}")
        else:
            print(f"❌ Form confirmation failed: {confirm_data}")
    else:
        print(f"❌ Failed to confirm form: {confirm_response.status_code}")


if __name__ == "__main__":
    test_appointment_flow()