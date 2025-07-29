#!/bin/bash
# Quick test for multi-turn conversations - verify the fix works

echo "============================================"
echo "QUICK MULTI-TURN CONVERSATION TEST"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "youwo-ml-venv/bin/activate" ]; then
    source youwo-ml-venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found. Please create it first.${NC}"
    exit 1
fi

# Environment variables for test
export ENVIRONMENT=test
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true

# Check if server is already running
if curl -s http://localhost:${ML_SERVER_PORT}/api/debug/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is already running${NC}"
    SERVER_PID=""
else
    echo -e "${YELLOW}Starting ML server...${NC}"
    python -m src.main --port 6001 > server_quick_test.log 2>&1 &
    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"
    
    # Wait for server to start
    echo "Waiting for server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:${ML_SERVER_PORT}/api/debug/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Server is ready${NC}"
            break
        fi
        sleep 1
    done
fi

# Create results directory
mkdir -p test_results_v2_40cases_enhanced
TEST_RESULTS_DIR="test_results_v2_40cases_enhanced"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="${TEST_RESULTS_DIR}/quick_multiturn_results_${TIMESTAMP}.md"

# FIXED Function for multi-turn conversations
test_api_followup() {
    local test_num=$1
    local user_id=$2
    local turns=$3  # Format: "Turn 1|Query1|Turn 2|Query2|Turn 3|Query3"
    local category=$4
    local description=$5
    
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Test #${test_num}: ${category} - FOLLOW-UP CONVERSATION${NC}"
    echo -e "${BLUE}Description:${NC} ${description}"
    echo -e "${BLUE}User:${NC} ${user_id}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Log to results file
    echo -e "\n## Test #${test_num}: ${category} - FOLLOW-UP" >> "$RESULTS_FILE"
    echo -e "**Description:** ${description}" >> "$RESULTS_FILE"
    echo -e "**User:** ${user_id}" >> "$RESULTS_FILE"
    echo -e "**Type:** Multi-turn Conversation" >> "$RESULTS_FILE"
    
    # Parse turns
    IFS='|' read -ra TURN_ARRAY <<< "$turns"
    
    # Create temporary file for messages array
    TEMP_MESSAGES=$(mktemp)
    echo '[]' > "$TEMP_MESSAGES"
    
    # Process each turn
    turn_count=0
    for ((i=0; i<${#TURN_ARRAY[@]}; i+=2)); do
        if [ $i -lt ${#TURN_ARRAY[@]} ] && [ $((i+1)) -lt ${#TURN_ARRAY[@]} ]; then
            turn_label="${TURN_ARRAY[i]}"
            query="${TURN_ARRAY[i+1]}"
            ((turn_count++))
            
            echo -e "\n${YELLOW}${turn_label}:${NC} ${query}"
            echo -e "\n### ${turn_label}:" >> "$RESULTS_FILE"
            echo -e "**Query:** ${query}" >> "$RESULTS_FILE"
            
            # Add user message to the messages array using jq
            jq --arg content "$query" '. += [{"role": "user", "content": $content}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            
            # Read current messages array
            messages=$(cat "$TEMP_MESSAGES")
            
            # Create request payload with properly formatted JSON
            request_payload=$(jq -n \
                --arg user_id "$user_id" \
                --argjson messages "$messages" \
                '{
                    user_id: $user_id,
                    messages: $messages,
                    stream: true,
                    debug: true
                }')
            
            # Make API call
            echo -e "${GREEN}Response:${NC}"
            echo -e "#### Response:" >> "$RESULTS_FILE"
            echo '```' >> "$RESULTS_FILE"
            
            # Stream the response and capture it
            full_response=""
            response_temp=$(mktemp)
            
            # Make the API call and capture response
            curl -sN -X POST "http://localhost:${ML_SERVER_PORT}/v2/humansa/chat" \
                -H "Content-Type: application/json" \
                -d "$request_payload" > "$response_temp" &
            curl_pid=$!
            
            # Process the streaming response
            while IFS= read -r line; do
                if [[ $line == data:* ]]; then
                    data="${line#data: }"
                    
                    if [[ $data == "[DONE]" ]]; then
                        break
                    fi
                    
                    if [[ ! -z "$data" ]] && [[ "$data" != " " ]]; then
                        # Extract content from the JSON response
                        content=$(echo "$data" | jq -r '.choices[0].delta.content // empty' 2>/dev/null)
                        if [[ ! -z "$content" ]]; then
                            echo -ne "$content"
                            full_response+="$content"
                            echo -n "$content" >> "$RESULTS_FILE"
                        fi
                    fi
                fi
            done < <(tail -f "$response_temp" 2>/dev/null & echo $! > "${response_temp}.pid")
            
            # Wait for curl to finish
            wait $curl_pid
            
            # Kill tail process
            if [ -f "${response_temp}.pid" ]; then
                kill $(cat "${response_temp}.pid") 2>/dev/null
                rm "${response_temp}.pid"
            fi
            
            echo # New line
            echo '```' >> "$RESULTS_FILE"
            
            # Clean up response temp file
            rm -f "$response_temp"
            
            # Add assistant response to message history
            if [[ ! -z "$full_response" ]]; then
                echo -e "${CYAN}[Turn ${turn_count} completed - Response length: ${#full_response} chars]${NC}"
                
                # Remove any thinking markers to get clean response
                clean_response="$full_response"
                if [[ "$full_response" == *"✅ **最终回答**:"* ]]; then
                    clean_response=$(echo "$full_response" | sed -n '/✅ \*\*最终回答\*\*:/,$p' | sed '1s/.*✅ \*\*最终回答\*\*:[[:space:]]*//')
                fi
                
                # Add assistant message to array using jq for proper escaping
                jq --arg content "$clean_response" '. += [{"role": "assistant", "content": $content}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            else
                echo -e "\n${RED}⚠️  Warning: Empty response received for Turn ${turn_count}${NC}"
                echo -e "\n**⚠️  Warning:** Empty response received" >> "$RESULTS_FILE"
                # Add empty assistant message to maintain conversation flow
                jq '. += [{"role": "assistant", "content": ""}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            fi
            
            # Pause between turns
            sleep 2
        fi
    done
    
    # Clean up temp file
    rm -f "$TEMP_MESSAGES"
    
    # Log conversation summary
    echo -e "\n${GREEN}✅ Conversation Summary: ${turn_count} turns completed${NC}"
    echo -e "\n**✅ Conversation Summary:** ${turn_count} turns completed" >> "$RESULTS_FILE"
    
    # Brief pause between tests
    sleep 2
}

# Initialize results file
echo "# Quick Multi-Turn Conversation Test Results" > "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "Testing the fixed multi-turn conversation handler" >> "$RESULTS_FILE"

# Run just 3 multi-turn tests to verify the fix
echo -e "\n${MAGENTA}${BOLD}===== RUNNING 3 QUICK MULTI-TURN TESTS =====${NC}"

# Test 1: Simple 3-turn conversation
test_api_followup 1 "test_multiturn_1" \
    "Turn 1|你好|Turn 2|我想找骨科医生|Turn 3|北京的医生有哪些？" \
    "Basic Multi-Turn" \
    "Simple 3-turn conversation test"

# Test 2: 5-turn appointment booking
test_api_followup 2 "test_multiturn_2" \
    "Turn 1|我想预约骨科医生|Turn 2|北京的张伟医生可以|Turn 3|下周二上午10点|Turn 4|我叫李明，电话13800138000|Turn 5|确认预约" \
    "Appointment Booking" \
    "Complete 5-turn booking flow"

# Test 3: Product inquiry with follow-ups
test_api_followup 3 "test_multiturn_3" \
    "Turn 1|我想买维生素C|Turn 2|有哪些品牌？|Turn 3|价格是多少？|Turn 4|最便宜的那个" \
    "Product Purchase" \
    "4-turn product inquiry"

# Summary
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}QUICK TEST COMPLETED!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n## Summary" >> "$RESULTS_FILE"
echo "- Tested 3 multi-turn conversations" >> "$RESULTS_FILE"
echo "- Check if all turns received responses" >> "$RESULTS_FILE"
echo "- Look for empty response warnings" >> "$RESULTS_FILE"

echo -e "\n${GREEN}✅ Results saved to: ${RESULTS_FILE}${NC}"

# Cleanup
if [ ! -z "$SERVER_PID" ]; then
    echo -e "\n${YELLOW}Stopping test server...${NC}"
    kill $SERVER_PID 2>/dev/null
    echo -e "${GREEN}✅ Server stopped${NC}"
fi

echo -e "\n${BOLD}Check the results to see if multi-turn conversations are working properly!${NC}"