#!/bin/bash
# Test only appointment booking (Test #12)

echo "Testing Appointment Booking (Test #12)"
echo "======================================"

# Test case 12
user_id="test_user_12"
query="帮我预约明天上午的骨科"

echo "User: $user_id"
echo "Query: $query"
echo ""

# Make the request
response=$(curl -s -X POST http://localhost:5001/v2/humansa/chat \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$user_id\",
        \"messages\": [{\"role\": \"user\", \"content\": \"$query\"}],
        \"stream\": false
    }")

# Extract content
content=$(echo "$response" | jq -r '.choices[0].message.content' 2>/dev/null)

echo "Response:"
echo "$content"
echo ""

# Check for error
if [[ "$content" == *"Reached max iterations"* ]]; then
    echo "❌ FAILED: Agent reached max iterations"
elif [[ "$content" == *"骨科"* ]] && [[ "$content" == *"医生"* ]]; then
    echo "✅ PASSED: Found orthopedic doctors"
else
    echo "⚠️ Check manually"
fi