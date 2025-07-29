#!/bin/bash
# HUMANSA V2 - 30 Multi-Turn Conversation Tests
# Dedicated test suite for verifying multi-turn conversation functionality

echo "============================================"
echo "HUMANSA V2 - 30 MULTI-TURN CONVERSATION TESTS"
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

# Step 1: Check PostgreSQL test database
echo -e "\n${YELLOW}Step 1: Checking PostgreSQL test database...${NC}"
if pg_isready -h localhost -p 5454 -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL test database is running on port 5454${NC}"
else
    echo -e "${RED}❌ PostgreSQL test database is not running on port 5454${NC}"
    echo "Please start the test database first with:"
    echo "cd test_environment && docker-compose up -d"
    exit 1
fi

# Step 2: Start/Check ML Server
echo -e "\n${YELLOW}Step 2: Checking ML server...${NC}"
if curl -s http://localhost:${ML_SERVER_PORT}/api/debug/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ML server is already running${NC}"
    SERVER_PID=""
else
    echo -e "${YELLOW}Starting ML server on port ${ML_SERVER_PORT}...${NC}"
    python -m src.main --port 6001 > server_multiturn_test.log 2>&1 &
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
RESULTS_FILE="${TEST_RESULTS_DIR}/multiturn_30_tests_${TIMESTAMP}.md"
PROCESS_LOG="${TEST_RESULTS_DIR}/multiturn_30_process_${TIMESTAMP}.md"

# Function for multi-turn conversations
test_api_followup() {
    local test_num=$1
    local user_id=$2
    local turns=$3  # Format: "Turn 1|Query1|Turn 2|Query2|Turn 3|Query3"
    local category=$4
    local description=$5
    
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Test #${test_num}: ${category}${NC}"
    echo -e "${BLUE}Description:${NC} ${description}"
    echo -e "${BLUE}User:${NC} ${user_id}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Log to process file
    echo -e "\n## Test #${test_num}: ${category} - ${description}" >> "$PROCESS_LOG"
    echo -e "**User:** ${user_id}" >> "$PROCESS_LOG"
    echo -e "**Time:** $(date)" >> "$PROCESS_LOG"
    
    # Log to results file
    echo -e "\n## Test #${test_num}: ${category}" >> "$RESULTS_FILE"
    echo -e "**Description:** ${description}" >> "$RESULTS_FILE"
    echo -e "**User:** ${user_id}" >> "$RESULTS_FILE"
    
    # Parse turns
    IFS='|' read -ra TURN_ARRAY <<< "$turns"
    
    # Create temporary file for messages array
    TEMP_MESSAGES=$(mktemp)
    echo '[]' > "$TEMP_MESSAGES"
    
    # Track success/failure
    local turn_success=0
    local turn_failures=0
    local turn_count=0
    
    # Process each turn
    for ((i=0; i<${#TURN_ARRAY[@]}; i+=2)); do
        if [ $i -lt ${#TURN_ARRAY[@]} ] && [ $((i+1)) -lt ${#TURN_ARRAY[@]} ]; then
            turn_label="${TURN_ARRAY[i]}"
            query="${TURN_ARRAY[i+1]}"
            ((turn_count++))
            
            echo -e "\n${YELLOW}${turn_label}:${NC} ${query}"
            echo -e "\n### ${turn_label}:" >> "$RESULTS_FILE"
            echo -e "**Query:** ${query}" >> "$RESULTS_FILE"
            echo -e "\n### ${turn_label}:" >> "$PROCESS_LOG"
            echo -e "**Query:** ${query}" >> "$PROCESS_LOG"
            
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
            echo -e "#### Response:" >> "$RESULTS_FILE"
            echo '```' >> "$RESULTS_FILE"
            echo -e "#### Processing:" >> "$PROCESS_LOG"
            echo '```' >> "$PROCESS_LOG"
            
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
                            echo -n "$content" >> "$PROCESS_LOG"
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
            echo '```' >> "$PROCESS_LOG"
            
            # Clean up response temp file
            rm -f "$response_temp"
            
            # Check response status and add to message history
            if [[ ! -z "$full_response" ]]; then
                ((turn_success++))
                echo -e "${GREEN}✓ Turn ${turn_count}: Response received (${#full_response} chars)${NC}"
                echo -e "**Status:** ✅ Success (${#full_response} chars)" >> "$RESULTS_FILE"
                
                # Remove any thinking markers to get clean response
                clean_response="$full_response"
                if [[ "$full_response" == *"✅ **最终回答**:"* ]]; then
                    clean_response=$(echo "$full_response" | sed -n '/✅ \*\*最终回答\*\*:/,$p' | sed '1s/.*✅ \*\*最终回答\*\*:[[:space:]]*//')
                fi
                
                # Add assistant message to array using jq for proper escaping
                jq --arg content "$clean_response" '. += [{"role": "assistant", "content": $content}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            else
                ((turn_failures++))
                echo -e "${RED}✗ Turn ${turn_count}: EMPTY RESPONSE${NC}"
                echo -e "**Status:** ❌ Failed - Empty Response" >> "$RESULTS_FILE"
                # Add empty assistant message to maintain conversation flow
                jq '. += [{"role": "assistant", "content": ""}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            fi
            
            # Brief pause between turns
            sleep 2
        fi
    done
    
    # Clean up temp file
    rm -f "$TEMP_MESSAGES"
    
    # Log summary
    local success_rate=$(awk "BEGIN {printf \"%.1f\", ${turn_success}/${turn_count}*100}")
    echo -e "\n${BOLD}Test Summary:${NC}"
    echo -e "  Total turns: ${turn_count}"
    echo -e "  Successful: ${GREEN}${turn_success}${NC}"
    echo -e "  Failed: ${RED}${turn_failures}${NC}"
    echo -e "  Success rate: ${success_rate}%"
    
    echo -e "\n**Summary:**" >> "$RESULTS_FILE"
    echo -e "- Total turns: ${turn_count}" >> "$RESULTS_FILE"
    echo -e "- Successful: ${turn_success}" >> "$RESULTS_FILE"
    echo -e "- Failed: ${turn_failures}" >> "$RESULTS_FILE"
    echo -e "- Success rate: ${success_rate}%" >> "$RESULTS_FILE"
    
    # Brief pause between tests
    sleep 2
}

# Initialize results files
echo "# HUMANSA V2 - 30 Multi-Turn Conversation Tests" > "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "Testing multi-turn conversation handling" >> "$RESULTS_FILE"

echo "# HUMANSA V2 - Multi-Turn Process Log" > "$PROCESS_LOG"
echo "Date: $(date)" >> "$PROCESS_LOG"

# Test 1-5: Basic Conversations (3-4 turns each)
echo -e "\n${MAGENTA}${BOLD}===== BASIC CONVERSATIONS (Tests 1-5) =====${NC}"

test_api_followup 1 "mt_test_1" \
    "Turn 1|你好|Turn 2|我住在北京|Turn 3|帮我找个医生" \
    "Basic Conversation" \
    "Simple greeting and doctor search"

test_api_followup 2 "mt_test_2" \
    "Turn 1|查询骨科医生|Turn 2|北京的|Turn 3|价格怎么样？|Turn 4|最便宜的是哪个？" \
    "Doctor Search Flow" \
    "Progressive doctor search with filters"

test_api_followup 3 "mt_test_3" \
    "Turn 1|我想买保健品|Turn 2|维生素类的|Turn 3|有哪些选择？|Turn 4|推荐一个" \
    "Product Inquiry" \
    "Product search and recommendation"

test_api_followup 4 "mt_test_4" \
    "Turn 1|最近睡不好|Turn 2|已经一个月了|Turn 3|需要看医生吗？|Turn 4|帮我预约" \
    "Medical Consultation" \
    "Health issue to appointment"

test_api_followup 5 "mt_test_5" \
    "Turn 1|诊所在哪里？|Turn 2|上海的|Turn 3|营业时间？|Turn 4|怎么去？" \
    "Clinic Information" \
    "Location and directions flow"

# Test 6-10: Memory Tests (4-5 turns each)
echo -e "\n${MAGENTA}${BOLD}===== MEMORY & CONTEXT TESTS (Tests 6-10) =====${NC}"

test_api_followup 6 "mt_memory_1" \
    "Turn 1|我叫王小明|Turn 2|今年35岁|Turn 3|有糖尿病|Turn 4|你记住了吗？|Turn 5|我叫什么？" \
    "Memory Test" \
    "Personal information retention"

test_api_followup 7 "mt_memory_2" \
    "Turn 1|我对青霉素过敏|Turn 2|还对海鲜过敏|Turn 3|记住这些信息|Turn 4|我有什么过敏？|Turn 5|能用青霉素吗？" \
    "Allergy Memory" \
    "Medical history retention"

test_api_followup 8 "mt_memory_3" \
    "Turn 1|我家有个5岁孩子|Turn 2|他经常感冒|Turn 3|上次看的是李医生|Turn 4|能继续找李医生吗？" \
    "Family Context" \
    "Family medical history"

test_api_followup 9 "mt_memory_4" \
    "Turn 1|上次预约的是骨科|Turn 2|是张伟医生|Turn 3|效果很好|Turn 4|想再约一次|Turn 5|还是同一个医生" \
    "Follow-up Memory" \
    "Previous appointment context"

test_api_followup 10 "mt_memory_5" \
    "Turn 1|我住在深圳南山区|Turn 2|在科技园工作|Turn 3|想找附近的诊所|Turn 4|最近的在哪？" \
    "Location Memory" \
    "Location-based recommendations"

# Test 11-15: Complete Appointment Flows (5-6 turns each)
echo -e "\n${MAGENTA}${BOLD}===== APPOINTMENT BOOKING FLOWS (Tests 11-15) =====${NC}"

test_api_followup 11 "mt_booking_1" \
    "Turn 1|预约医生|Turn 2|内科|Turn 3|北京的|Turn 4|明天可以吗？|Turn 5|上午10点|Turn 6|我叫张三，13800001111" \
    "Full Booking Flow" \
    "Complete appointment booking"

test_api_followup 12 "mt_booking_2" \
    "Turn 1|给孩子预约儿科|Turn 2|发烧了|Turn 3|今天能看吗？|Turn 4|哪个医生好？|Turn 5|就第一个吧|Turn 6|确认预约" \
    "Urgent Booking" \
    "Urgent pediatric appointment"

test_api_followup 13 "mt_booking_3" \
    "Turn 1|查看可预约时间|Turn 2|骨科的|Turn 3|这周有空吗？|Turn 4|周五下午呢？|Turn 5|3点可以" \
    "Availability Check" \
    "Time slot selection"

test_api_followup 14 "mt_booking_4" \
    "Turn 1|改约|Turn 2|原来是明天的|Turn 3|改到后天|Turn 4|还是上午|Turn 5|确认修改" \
    "Reschedule Flow" \
    "Appointment rescheduling"

test_api_followup 15 "mt_booking_5" \
    "Turn 1|取消预约|Turn 2|忘记是哪天了|Turn 3|好像是这周的|Turn 4|对，周三那个|Turn 5|确认取消" \
    "Cancellation Flow" \
    "Appointment cancellation"

# Test 16-20: Product Purchase Flows (4-5 turns each)
echo -e "\n${MAGENTA}${BOLD}===== PRODUCT PURCHASE FLOWS (Tests 16-20) =====${NC}"

test_api_followup 16 "mt_purchase_1" \
    "Turn 1|买血压计|Turn 2|家用的|Turn 3|准确度怎么样？|Turn 4|多少钱？|Turn 5|买最好的那个" \
    "Medical Device" \
    "Blood pressure monitor purchase"

test_api_followup 17 "mt_purchase_2" \
    "Turn 1|孕妇维生素|Turn 2|叶酸含量要高的|Turn 3|有副作用吗？|Turn 4|一天吃几次？|Turn 5|买一个月的量" \
    "Prenatal Vitamins" \
    "Pregnancy supplement purchase"

test_api_followup 18 "mt_purchase_3" \
    "Turn 1|老人保健品|Turn 2|增强免疫力的|Turn 3|有哪些选择？|Turn 4|国产的有吗？|Turn 5|要两盒" \
    "Senior Health" \
    "Elderly supplement selection"

test_api_followup 19 "mt_purchase_4" \
    "Turn 1|儿童钙片|Turn 2|3岁能吃的|Turn 3|什么口味？|Turn 4|不要太甜的|Turn 5|先买一瓶试试" \
    "Children's Health" \
    "Pediatric supplement"

test_api_followup 20 "mt_purchase_5" \
    "Turn 1|减肥产品|Turn 2|安全的|Turn 3|有运动配合吗？|Turn 4|效果怎么样？" \
    "Weight Management" \
    "Diet product inquiry"

# Test 21-25: Complex Medical Consultations (5-6 turns each)
echo -e "\n${MAGENTA}${BOLD}===== COMPLEX CONSULTATIONS (Tests 21-25) =====${NC}"

test_api_followup 21 "mt_complex_1" \
    "Turn 1|头疼好几天了|Turn 2|早上更严重|Turn 3|有时候还恶心|Turn 4|需要做检查吗？|Turn 5|哪个科室？|Turn 6|帮我预约" \
    "Symptom Analysis" \
    "Headache consultation flow"

test_api_followup 22 "mt_complex_2" \
    "Turn 1|体检报告不正常|Turn 2|血脂偏高|Turn 3|需要吃药吗？|Turn 4|饮食注意什么？|Turn 5|多久复查？" \
    "Test Results" \
    "Lab results consultation"

test_api_followup 23 "mt_complex_3" \
    "Turn 1|皮肤过敏|Turn 2|吃海鲜后|Turn 3|很痒|Turn 4|能用什么药？|Turn 5|需要忌口吗？|Turn 6|多久能好？" \
    "Allergy Treatment" \
    "Allergic reaction management"

test_api_followup 24 "mt_complex_4" \
    "Turn 1|关节疼痛|Turn 2|运动后加重|Turn 3|已经两周了|Turn 4|是关节炎吗？|Turn 5|怎么治疗？" \
    "Joint Pain" \
    "Orthopedic consultation"

test_api_followup 25 "mt_complex_5" \
    "Turn 1|心跳很快|Turn 2|休息时也快|Turn 3|有点胸闷|Turn 4|严重吗？|Turn 5|需要急诊吗？|Turn 6|现在怎么办？" \
    "Cardiac Symptoms" \
    "Heart-related consultation"

# Test 26-30: Error Recovery & Edge Cases (4-5 turns each)
echo -e "\n${MAGENTA}${BOLD}===== ERROR RECOVERY TESTS (Tests 26-30) =====${NC}"

test_api_followup 26 "mt_error_1" \
    "Turn 1|找王医生|Turn 2|不对，是李医生|Turn 3|骨科的李医生|Turn 4|有这个人吗？" \
    "Name Correction" \
    "Doctor name error recovery"

test_api_followup 27 "mt_error_2" \
    "Turn 1|明天预约|Turn 2|不行，后天|Turn 3|还是明天吧|Turn 4|上午还是下午好？|Turn 5|上午" \
    "Time Changes" \
    "Multiple time modifications"

test_api_followup 28 "mt_error_3" \
    "Turn 1|买维生素|Turn 2|C不对是D|Turn 3|儿童的|Turn 4|5岁孩子|Turn 5|什么品牌好？" \
    "Product Correction" \
    "Product selection changes"

test_api_followup 29 "mt_error_4" \
    "Turn 1|上海的诊所|Turn 2|不是，北京的|Turn 3|朝阳区|Turn 4|有几家？" \
    "Location Correction" \
    "City change during search"

test_api_followup 30 "mt_error_5" \
    "Turn 1|qingwen|Turn 2|请问|Turn 3|有医生吗|Turn 4|会说英语的|Turn 5|预约明天的" \
    "Language Mix" \
    "Mixed language handling"

# Summary
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}30 MULTI-TURN TESTS COMPLETED!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Calculate overall statistics
echo -e "\n## Overall Summary" >> "$RESULTS_FILE"
echo "- Total tests: 30" >> "$RESULTS_FILE"
echo "- Test categories:" >> "$RESULTS_FILE"
echo "  - Basic Conversations: Tests 1-5" >> "$RESULTS_FILE"
echo "  - Memory & Context: Tests 6-10" >> "$RESULTS_FILE"
echo "  - Appointment Flows: Tests 11-15" >> "$RESULTS_FILE"
echo "  - Product Purchases: Tests 16-20" >> "$RESULTS_FILE"
echo "  - Complex Consultations: Tests 21-25" >> "$RESULTS_FILE"
echo "  - Error Recovery: Tests 26-30" >> "$RESULTS_FILE"

echo -e "\n${GREEN}✅ Results saved to:${NC}"
echo -e "   - Main results: ${RESULTS_FILE}"
echo -e "   - Process log: ${PROCESS_LOG}"

# Cleanup
if [ ! -z "$SERVER_PID" ]; then
    echo -e "\n${YELLOW}Stopping test server...${NC}"
    kill $SERVER_PID 2>/dev/null
    echo -e "${GREEN}✅ Server stopped${NC}"
fi

echo -e "\n${BOLD}Analysis Guide:${NC}"
echo "1. Check results file for turn-by-turn success rates"
echo "2. Look for patterns in failed turns"
echo "3. Review process log for detailed agent thinking"
echo "4. Identify any systematic issues with specific turn numbers"