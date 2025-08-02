#!/bin/bash

echo "Testing Appointment Form System..."

# Test 1: Simple complete appointment request
echo -e "\n1. Testing complete appointment request..."

RESPONSE=$(curl -s -X POST http://localhost:6001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "input": "我想预约李明医生明天上午9点看头痛",
    "user_id": "test_form_user_001"
  }')

echo "Response:"
echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"

# Extract response ID if available
RESPONSE_ID=$(echo "$RESPONSE" | jq -r '.id' 2>/dev/null)

if [ ! -z "$RESPONSE_ID" ] && [ "$RESPONSE_ID" != "null" ]; then
    echo -e "\nResponse ID: $RESPONSE_ID"
    
    # Extract output text
    echo -e "\nOutput text:"
    echo "$RESPONSE" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null
    
    # Check for form elements
    echo -e "\nChecking for form elements..."
    OUTPUT_TEXT=$(echo "$RESPONSE" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | tr '\n' ' ')
    
    echo "$OUTPUT_TEXT" | grep -q "预约" && echo "✓ Appointment mentioned" || echo "✗ No appointment mention"
    echo "$OUTPUT_TEXT" | grep -q "李明" && echo "✓ Doctor found" || echo "✗ Doctor not found"
    echo "$OUTPUT_TEXT" | grep -q "明天" && echo "✓ Date found" || echo "✗ Date not found"
    echo "$OUTPUT_TEXT" | grep -q "form_" && echo "✓ Form ID found" || echo "✗ No form ID"
    
    # Test 2: Confirm appointment
    if echo "$OUTPUT_TEXT" | grep -q "确认"; then
        echo -e "\n2. Testing appointment confirmation..."
        
        CONFIRM_RESPONSE=$(curl -s -X POST http://localhost:6001/v2/humansa/responses/create \
          -H "Content-Type: application/json" \
          -d "{
            \"model\": \"gpt-4-turbo\",
            \"input\": \"确认\",
            \"user_id\": \"test_form_user_001\",
            \"previous_response_id\": \"$RESPONSE_ID\"
          }")
        
        echo "Confirmation response:"
        echo "$CONFIRM_RESPONSE" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | head -10
    fi
else
    echo "Failed to get response"
fi

# Test 3: Multi-turn conversation
echo -e "\n\n3. Testing multi-turn form collection..."

# First turn
RESPONSE1=$(curl -s -X POST http://localhost:6001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "input": "我想看医生",
    "user_id": "test_form_user_002"
  }')

echo "Turn 1 - User: 我想看医生"
echo "Assistant:"
echo "$RESPONSE1" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | head -5

RESPONSE1_ID=$(echo "$RESPONSE1" | jq -r '.id' 2>/dev/null)

if [ ! -z "$RESPONSE1_ID" ] && [ "$RESPONSE1_ID" != "null" ]; then
    # Second turn
    RESPONSE2=$(curl -s -X POST http://localhost:6001/v2/humansa/responses/create \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"gpt-4-turbo\",
        \"input\": \"头痛，想看李明医生\",
        \"user_id\": \"test_form_user_002\",
        \"previous_response_id\": \"$RESPONSE1_ID\"
      }")
    
    echo -e "\nTurn 2 - User: 头痛，想看李明医生"
    echo "Assistant:"
    echo "$RESPONSE2" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | head -5
fi