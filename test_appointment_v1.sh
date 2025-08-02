#!/bin/bash

echo "Testing Appointment Form System via v1 API..."
echo "============================================"

# Test 1: Simple appointment request
echo -e "\n1. Testing appointment creation..."

RESPONSE=$(curl -s -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "我想预约李明医生明天上午9点看头痛"}],
    "stream": false
  }')

echo "Response received. Parsing..."

# Extract the assistant's message
MESSAGE=$(echo "$RESPONSE" | jq -r '.choices[0].message.content' 2>/dev/null)

if [ -z "$MESSAGE" ]; then
  echo "Error: No response received"
  echo "Raw response:"
  echo "$RESPONSE" | head -100
else
  echo -e "\nAssistant response:"
  echo "$MESSAGE"
  
  # Check for appointment elements
  echo -e "\nChecking response elements:"
  echo "$MESSAGE" | grep -q "李明" && echo "✓ Doctor name found" || echo "✗ Doctor name not found"
  echo "$MESSAGE" | grep -q "明天" && echo "✓ Date found" || echo "✗ Date not found"
  echo "$MESSAGE" | grep -q "上午" && echo "✓ Time found" || echo "✗ Time not found"
  echo "$MESSAGE" | grep -q "头痛" && echo "✓ Symptoms found" || echo "✗ Symptoms not found"
  echo "$MESSAGE" | grep -q "预约" && echo "✓ Appointment mentioned" || echo "✗ Appointment not mentioned"
  echo "$MESSAGE" | grep -q "确认" && echo "✓ Confirmation requested" || echo "✗ No confirmation request"
  
  # Look for form_id
  if echo "$MESSAGE" | grep -q "form_"; then
    FORM_ID=$(echo "$MESSAGE" | grep -o 'form_[a-f0-9]\{12\}' | head -1)
    echo "✓ Form ID found: $FORM_ID"
  else
    echo "✗ No form ID found"
  fi
fi

# Test 2: Multi-turn conversation
echo -e "\n\n2. Testing multi-turn conversation..."

# First turn - incomplete request
RESPONSE1=$(curl -s -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "我想看医生"}],
    "stream": false
  }')

MESSAGE1=$(echo "$RESPONSE1" | jq -r '.choices[0].message.content' 2>/dev/null)
echo -e "\nFirst turn - User: 我想看医生"
echo "Assistant: $MESSAGE1" | head -3

# Second turn - add symptoms
echo -e "\nSecond turn - User: 我最近头痛得厉害"

RESPONSE2=$(curl -s -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "我想看医生"},
      {"role": "assistant", "content": "'"$MESSAGE1"'"},
      {"role": "user", "content": "我最近头痛得厉害"}
    ],
    "stream": false
  }')

MESSAGE2=$(echo "$RESPONSE2" | jq -r '.choices[0].message.content' 2>/dev/null)
echo "Assistant: $MESSAGE2" | head -3

# Third turn - choose doctor
echo -e "\nThird turn - User: 就看李明医生吧，明天上午可以吗"

RESPONSE3=$(curl -s -X POST http://localhost:5001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "我想看医生"},
      {"role": "assistant", "content": "'"$MESSAGE1"'"},
      {"role": "user", "content": "我最近头痛得厉害"},
      {"role": "assistant", "content": "'"$MESSAGE2"'"},
      {"role": "user", "content": "就看李明医生吧，明天上午可以吗"}
    ],
    "stream": false
  }')

MESSAGE3=$(echo "$RESPONSE3" | jq -r '.choices[0].message.content' 2>/dev/null)
echo "Assistant: $MESSAGE3" | head -5

# Check if form was created in final turn
echo -e "\nChecking if appointment was created:"
echo "$MESSAGE3" | grep -q "预约信息" && echo "✓ Appointment preview shown" || echo "✗ No appointment preview"
echo "$MESSAGE3" | grep -q "确认" && echo "✓ Confirmation requested" || echo "✗ No confirmation request"

# Test 3: Test with v2 endpoint if available
echo -e "\n\n3. Testing v2 responses endpoint..."

V2_RESPONSE=$(curl -s -X POST http://localhost:5001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "input": "我想预约张伟医生后天下午看胃痛",
    "user_id": "test_user_v2"
  }')

if echo "$V2_RESPONSE" | jq '.' >/dev/null 2>&1; then
  echo "V2 endpoint is available!"
  echo "$V2_RESPONSE" | jq -r '.output[] | select(.type=="text") | .text' 2>/dev/null | head -5
else
  echo "V2 endpoint not available or returned invalid JSON"
fi