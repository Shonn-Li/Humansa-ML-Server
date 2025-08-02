#!/bin/bash

echo "Testing Appointment Form System..."
echo "================================="

# Test 1: Create appointment
echo -e "\n1. Testing appointment creation..."

RESPONSE=$(curl -s -X POST http://localhost:5001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "input": "我想预约李明医生明天上午9点看头痛",
    "user_id": "test_user_123"
  }')

echo "Response:"
echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"

# Extract response ID
RESPONSE_ID=$(echo "$RESPONSE" | jq -r '.id' 2>/dev/null)
echo -e "\nResponse ID: $RESPONSE_ID"

# Check for form elements
echo -e "\nChecking response content..."
echo "$RESPONSE" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | grep -E "(预约|李明|明天|确认)" || echo "No appointment info found"

# Check for tool usage
echo -e "\nChecking tool usage..."
echo "$RESPONSE" | jq -r '.output[] | select(.type=="tool_use") | .tool_use.name' 2>/dev/null || echo "No tools found"

# Test 2: Multi-turn conversation
echo -e "\n\n2. Testing multi-turn conversation..."

RESPONSE2=$(curl -s -X POST http://localhost:5001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "input": "我想看医生",
    "user_id": "test_user_456"
  }')

echo "First turn response:"
echo "$RESPONSE2" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | head -5

RESPONSE2_ID=$(echo "$RESPONSE2" | jq -r '.id' 2>/dev/null)

# Continue conversation
echo -e "\nContinuing conversation..."

RESPONSE3=$(curl -s -X POST http://localhost:5001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"gpt-4-turbo\",
    \"input\": \"头痛，想看李明医生\",
    \"user_id\": \"test_user_456\",
    \"previous_response_id\": \"$RESPONSE2_ID\"
  }")

echo "Second turn response:"
echo "$RESPONSE3" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | head -5