#!/bin/bash
# HUMANSA V2 - 70 Comprehensive Test Cases with Follow-up Conversations (FIXED)
# Shows full agent thinking, tool calls, memory context, and multi-turn conversations

echo "============================================"
echo "HUMANSA AI AGENT V2 - 70 TEST CASES"
echo "WITH FOLLOW-UP CONVERSATIONS (FIXED)"
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

# Step 2: Run SQL scripts to populate test data in specific order
echo -e "\n${YELLOW}Step 2: Populating test database...${NC}"
cd test_environment/sql

# Define SQL files in specific order
SQL_FILES=(
    "01_extensions.sql"
    "02_create_tables.sql"
    "03_test_data.sql"
    "04_embeddings_simple.sql"
    "05_test_conversations.sql"
    "06_humansa_test_data.sql"
    "07_humansa_his_alignment.sql"
    "08_appointment_management.sql"
    "create_missing_tables.sql"
    "fix_doctor_table_schema.sql"
    "create_product_tables.sql"
    "fix_medical_service_schema.sql"
    "insert_comprehensive_test_data.sql"
    "insert_product_test_data.sql"
    "fix_product_categories.sql"
)

# Run each SQL file in order
for sql_file in "${SQL_FILES[@]}"; do
    if [ -f "$sql_file" ]; then
        echo "Running $sql_file..."
        PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -f "$sql_file" > /dev/null 2>&1
    fi
done

cd ../..
echo -e "${GREEN}✅ Test data populated${NC}"

# Step 3: Start the ML server with enhanced logging
echo -e "\n${YELLOW}Step 3: Starting ML server on port ${ML_SERVER_PORT} with enhanced logging...${NC}"
# Kill any existing server on port 5001
lsof -ti:${ML_SERVER_PORT} | xargs kill -9 2>/dev/null || true
sleep 2

# Start server with enhanced logging for V2
export HUMANSA_ENHANCED_LOGGING=true
python -m src.main --port 6001 > server_enhanced.log 2>&1 &
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

# Create results directory
mkdir -p test_results_v2_40cases_enhanced
TEST_RESULTS_DIR="test_results_v2_40cases_enhanced"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="${TEST_RESULTS_DIR}/results_${TIMESTAMP}.md"
PROCESS_LOG="${TEST_RESULTS_DIR}/process_log_${TIMESTAMP}.md"

# Function to test API with enhanced process logging
test_api_enhanced() {
    local test_num=$1
    local user_id=$2
    local query=$3
    local category=$4
    local description=$5
    
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Test #${test_num}: ${category}${NC}"
    echo -e "${BLUE}Description:${NC} ${description}"
    echo -e "${BLUE}User:${NC} ${user_id}"
    echo -e "${BLUE}Query:${NC} ${query}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Log to process file
    echo -e "\n## Test #${test_num}: ${category} - ${description}" >> "$PROCESS_LOG"
    echo -e "**User:** ${user_id}" >> "$PROCESS_LOG"
    echo -e "**Query:** ${query}" >> "$PROCESS_LOG"
    echo -e "**Time:** $(date)" >> "$PROCESS_LOG"
    echo -e "\n### Process Flow:" >> "$PROCESS_LOG"
    
    # First, get memory context for this user
    echo -e "\n${MAGENTA}📚 Checking Memory Context...${NC}"
    echo -e "\n#### Memory Context:" >> "$PROCESS_LOG"
    
    memory_response=$(curl -s -X GET "http://localhost:${ML_SERVER_PORT}/v2/humansa/memory/context/${user_id}")
    memory_content=$(echo "$memory_response" | jq -r '.' 2>/dev/null || echo "$memory_response")
    echo -e "${CYAN}Memory: ${memory_content}${NC}"
    echo '```json' >> "$PROCESS_LOG"
    echo "$memory_content" >> "$PROCESS_LOG"
    echo '```' >> "$PROCESS_LOG"
    
    # Make API call with streaming to see the full process
    echo -e "\n${YELLOW}Processing Query with Full Logging...${NC}"
    echo -e "\n#### Agent Processing:" >> "$PROCESS_LOG"
    echo '```' >> "$PROCESS_LOG"
    
    # Create request payload
    request_payload=$(cat <<EOF
{
    "user_id": "${user_id}",
    "messages": [{"role": "user", "content": "${query}"}],
    "stream": true,
    "debug": true
}
EOF
)
    
    # Stream the response and capture all steps
    echo -e "${GREEN}Agent Response:${NC}"
    echo -e "\n### Test #${test_num}: ${category}" >> "$RESULTS_FILE"
    echo -e "**Description:** ${description}" >> "$RESULTS_FILE"
    echo -e "**User:** ${user_id}" >> "$RESULTS_FILE"
    echo -e "**Query:** ${query}" >> "$RESULTS_FILE"
    echo -e "\n#### Response:" >> "$RESULTS_FILE"
    echo '```' >> "$RESULTS_FILE"
    
    # Make the API call and stream the response
    while IFS= read -r line; do
        if [[ $line == data:* ]]; then
            data="${line#data: }"
            
            if [[ $data == "[DONE]" ]]; then
                break
            fi
            
            if [[ ! -z "$data" ]]; then
                # Extract content from the JSON response
                content=$(echo "$data" | jq -r '.choices[0].delta.content // empty' 2>/dev/null)
                if [[ ! -z "$content" ]]; then
                    echo -ne "$content"
                    echo -n "$content" >> "$PROCESS_LOG"
                    echo -n "$content" >> "$RESULTS_FILE"
                fi
                
                # Also check for debug events
                debug_info=$(echo "$data" | jq -r '.debug // empty' 2>/dev/null)
                if [[ ! -z "$debug_info" ]]; then
                    echo -e "\n${MAGENTA}[DEBUG] ${debug_info}${NC}"
                fi
            fi
        fi
    done < <(curl -sN -X POST "http://localhost:${ML_SERVER_PORT}/v2/humansa/chat" \
        -H "Content-Type: application/json" \
        -d "$request_payload")
    
    echo # New line after response
    echo '```' >> "$PROCESS_LOG"
    echo '```' >> "$RESULTS_FILE"
    echo -e "\n---\n" >> "$RESULTS_FILE"
    
    # Brief pause between tests
    sleep 2
}

# FIXED Function for multi-turn conversations with proper JSON handling
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
    
    # Log to process file
    echo -e "\n## Test #${test_num}: ${category} - ${description} [FOLLOW-UP]" >> "$PROCESS_LOG"
    echo -e "**User:** ${user_id}" >> "$PROCESS_LOG"
    echo -e "**Type:** Multi-turn Conversation" >> "$PROCESS_LOG"
    echo -e "**Time:** $(date)" >> "$PROCESS_LOG"
    
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
            echo -e "${GREEN}Response:${NC}"
            echo -e "#### Response:" >> "$RESULTS_FILE"
            echo '```' >> "$RESULTS_FILE"
            echo -e "#### Agent Processing:" >> "$PROCESS_LOG"
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
            
            # Add assistant response to message history
            if [[ ! -z "$full_response" ]]; then
                # Remove any thinking markers to get clean response
                clean_response="$full_response"
                if [[ "$full_response" == *"✅ **最终回答**:"* ]]; then
                    clean_response=$(echo "$full_response" | sed -n '/✅ \*\*最终回答\*\*:/,$p' | sed '1s/.*✅ \*\*最终回答\*\*:[[:space:]]*//')
                fi
                
                # Add assistant message to array using jq for proper escaping
                jq --arg content "$clean_response" '. += [{"role": "assistant", "content": $content}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            else
                echo -e "\n${RED}Warning: Empty response received${NC}"
                echo -e "\n**Warning:** Empty response received" >> "$RESULTS_FILE"
                # Add empty assistant message to maintain conversation flow
                jq '. += [{"role": "assistant", "content": ""}]' "$TEMP_MESSAGES" > "${TEMP_MESSAGES}.tmp" && mv "${TEMP_MESSAGES}.tmp" "$TEMP_MESSAGES"
            fi
            
            # Pause between turns
            sleep 3
        fi
    done
    
    # Clean up temp file
    rm -f "$TEMP_MESSAGES"
    
    # Log conversation summary
    echo -e "\n**Conversation Summary:** ${turn_count} turns completed" >> "$RESULTS_FILE"
    echo -e "\n**Conversation Summary:** ${turn_count} turns completed" >> "$PROCESS_LOG"
    
    # Brief pause between tests
    sleep 2
}

# Initialize results files
echo "# HUMANSA V2 - 70 Test Cases with Follow-up Conversations (FIXED)" > "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "Environment: Test (Port 5454)" >> "$RESULTS_FILE"
echo "Mode: Enhanced Logging with Multi-turn Conversations" >> "$RESULTS_FILE"

echo "# HUMANSA V2 - Process Flow Log (FIXED)" > "$PROCESS_LOG"
echo "Date: $(date)" >> "$PROCESS_LOG"
echo "This log shows the complete agent thinking process, tool calls, and memory context" >> "$PROCESS_LOG"

# Category 1: Identity and Introduction Tests (1-5)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 1: IDENTITY AND INTRODUCTION TESTS =====${NC}"

test_api_enhanced 1 "test_user_1" "你好" "Identity" "Basic greeting"
test_api_enhanced 2 "test_user_2" "你是谁？" "Identity" "Direct identity query"
test_api_enhanced 3 "test_user_3" "介绍一下诺亚新舟" "Identity" "Company introduction"
test_api_enhanced 4 "test_user_4" "你们的口号是什么？" "Identity" "Company slogan"
test_api_enhanced 5 "test_user_5" "你能做什么？" "Identity" "Capability inquiry"

# Category 2: Doctor Search Tests (6-10)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 2: DOCTOR SEARCH TESTS =====${NC}"

test_api_enhanced 6 "test_user_6" "我想找个骨科医生" "Doctor Search" "Specialty-based search"
test_api_enhanced 7 "test_user_7" "张三医生在吗？" "Doctor Search" "Name-based search"
test_api_enhanced 8 "test_user_8" "北京有哪些医生？" "Doctor Search" "Location-based search"
test_api_enhanced 9 "test_user_9" "最贵的医生是谁？" "Doctor Search" "Price-based search"
test_api_enhanced 10 "test_user_10" "有会说英语的医生吗？" "Doctor Search" "Language preference"

# Category 3: Appointment Booking Tests (11-15)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 3: APPOINTMENT BOOKING TESTS =====${NC}"

test_api_enhanced 11 "test_user_11" "我想预约张三医生" "Appointment" "Direct doctor booking"
test_api_enhanced 12 "test_user_12" "帮我预约明天上午的骨科" "Appointment" "Time-based booking"
test_api_enhanced 13 "test_user_13" "查看下周的可预约时间" "Appointment" "Availability check"
test_api_enhanced 14 "test_user_14" "取消我的预约" "Appointment" "Cancellation request"
test_api_enhanced 15 "test_user_15" "改约到下周三" "Appointment" "Rescheduling request"

# Category 4: Clinic and Service Tests (16-20)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 4: CLINIC AND SERVICE TESTS =====${NC}"

test_api_enhanced 16 "test_user_16" "离我最近的诊所在哪？" "Clinic" "Location query"
test_api_enhanced 17 "test_user_17" "血常规多少钱？" "Service" "Price inquiry"
test_api_enhanced 18 "test_user_18" "体检套餐有哪些？" "Service" "Package inquiry"
test_api_enhanced 19 "test_user_19" "诊所几点开门？" "Clinic" "Hours inquiry"
test_api_enhanced 20 "test_user_20" "上海诊所的电话是多少？" "Clinic" "Contact info"

# Category 5: Medical Consultation Tests (21-25)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 5: MEDICAL CONSULTATION TESTS =====${NC}"

test_api_enhanced 21 "test_user_21" "我最近总是失眠怎么办？" "Medical" "Sleep issue"
test_api_enhanced 22 "test_user_22" "孩子发烧39度该怎么处理？" "Medical" "Fever management"
test_api_enhanced 23 "test_user_23" "胸口疼痛呼吸困难" "Medical" "Emergency symptoms"
test_api_enhanced 24 "test_user_24" "高血压能吃什么药？" "Medical" "Medication query"
test_api_enhanced 25 "test_user_25" "体检报告显示血糖偏高" "Medical" "Test result interpretation"

# Category 6: Memory Persistence Tests (26-30)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 6: MEMORY PERSISTENCE TESTS =====${NC}"

# First, store information
test_api_enhanced 26 "memory_test_user_1" "我叫张三，住在北京，今年45岁" "Memory" "Store personal info"
test_api_enhanced 26.2 "memory_test_user_1" "我对花生和海鲜过敏" "Memory" "Store allergies"
test_api_enhanced 26.3 "memory_test_user_1" "我有高血压，每天吃降压药" "Memory" "Store medical condition"

# Then, test recall
test_api_enhanced 27 "memory_test_user_1" "你知道我的基本信息吗？" "Memory" "Recall personal info"
test_api_enhanced 28 "memory_test_user_1" "我有什么过敏史和慢性病？" "Memory" "Recall medical history"

# Cross-session continuity
test_api_enhanced 29 "memory_test_user_2" "我想找骨科医生，我膝盖老是疼" "Memory" "Session 1"
test_api_enhanced 29.2 "memory_test_user_2" "上次我说的膝盖问题，有推荐的医生吗？" "Memory" "Session 2 continuity"

# Complex memory integration
test_api_enhanced 30 "memory_test_user_3" "我住在深圳，想找离家近的诊所" "Memory" "Store location"
test_api_enhanced 30.2 "memory_test_user_3" "我女儿5岁，经常感冒" "Memory" "Store child info"
test_api_enhanced 30.3 "memory_test_user_3" "推荐一个适合看儿童感冒的医生，最好在我附近" "Memory" "Complex integration"

# Category 7: Product Recommendation Tests (31-40)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 7: PRODUCT RECOMMENDATION TESTS =====${NC}"

test_api_enhanced 31 "test_user_31" "你们有什么保健品推荐吗？" "Product" "General product inquiry"
test_api_enhanced 32 "test_user_32" "我想买维生素D，有什么推荐？" "Product" "Vitamin recommendation"
test_api_enhanced 33 "test_user_33" "家里老人需要血压计，推荐一款" "Product" "Medical equipment"
test_api_enhanced 34 "test_user_34" "有500元以下的保健品吗？" "Product" "Price range filter"
test_api_enhanced 35 "test_user_35" "我失眠严重，有什么产品可以帮助睡眠？" "Product" "Health condition based"
test_api_enhanced 36 "test_user_36" "有医美面膜吗？" "Product" "Beauty product"
test_api_enhanced 37 "test_user_37" "有什么健康套餐推荐？" "Product" "Package recommendation"
test_api_enhanced 38 "test_user_38" "孕妇需要补充什么营养品？" "Product" "Mother-baby products"
test_api_enhanced 39 "test_user_39" "有西洋参吗？" "Product" "Traditional Chinese medicine"
test_api_enhanced 40 "test_user_40" "怎么购买这些产品？" "Product" "Purchase guidance"

# Category 8: Complete Appointment Booking Flows (41-50)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 8: COMPLETE APPOINTMENT BOOKING FLOWS =====${NC}"

test_api_followup 41 "booking_user_1" \
    "Turn 1|我想预约骨科医生|Turn 2|北京的张伟医生可以|Turn 3|下周二上午10点|Turn 4|我叫李明，电话13800138000|Turn 5|确认预约" \
    "Appointment Booking Flow" \
    "Complete booking from search to confirmation"

test_api_followup 42 "booking_user_2" \
    "Turn 1|帮我预约明天的儿科医生|Turn 2|上午几点有空？|Turn 3|9点可以|Turn 4|给我女儿看，她叫小美，我电话15900001111" \
    "Appointment Booking Flow" \
    "Booking for family member"

test_api_followup 43 "booking_user_3" \
    "Turn 1|我想看内科医生|Turn 2|有什么医生推荐？|Turn 3|那个王强医生吧|Turn 4|这周五下午|Turn 5|张三，13612345678|Turn 6|好的确认" \
    "Appointment Booking Flow" \
    "Booking with doctor recommendation"

test_api_followup 44 "cancel_user_1" \
    "Turn 1|取消我的预约|Turn 2|手机号13800138000|Turn 3|是明天上午10点张伟医生的|Turn 4|确认取消" \
    "Appointment Cancellation" \
    "Complete cancellation flow"

test_api_followup 45 "reschedule_user_1" \
    "Turn 1|我要改约|Turn 2|原来是这周三，想改到下周一|Turn 3|手机号13900002222|Turn 4|上午还是下午都可以|Turn 5|确认改约" \
    "Appointment Rescheduling" \
    "Complete rescheduling flow"

test_api_followup 46 "booking_user_4" \
    "Turn 1|北京哪里可以看骨科？|Turn 2|协和医院怎么样？|Turn 3|帮我预约张伟医生|Turn 4|最近什么时候有号？|Turn 5|周四上午吧|Turn 6|王小华，18600003333" \
    "Appointment Booking Flow" \
    "Location-based booking with availability check"

test_api_followup 47 "booking_user_5" \
    "Turn 1|我膝盖疼，需要看医生|Turn 2|已经疼了一个星期了|Turn 3|好的，帮我预约骨科|Turn 4|明天下午可以吗？|Turn 5|李强，13700004444" \
    "Appointment Booking Flow" \
    "Symptom-based booking"

test_api_followup 48 "booking_user_6" \
    "Turn 1|查看本周可以预约的医生|Turn 2|有儿科医生吗？|Turn 3|李娜医生什么时候有空？|Turn 4|周三上午预约|Turn 5|孩子叫小明，我是他妈妈，电话15800005555" \
    "Appointment Booking Flow" \
    "Availability check before booking"

test_api_followup 49 "booking_user_7" \
    "Turn 1|最便宜的医生是谁？|Turn 2|内科的呢？|Turn 3|好，就王强医生|Turn 4|这周任何时间都行|Turn 5|赵六，13500006666" \
    "Appointment Booking Flow" \
    "Price-conscious booking"

test_api_followup 50 "booking_user_8" \
    "Turn 1|我想做个体检|Turn 2|有什么体检套餐？|Turn 3|基础套餐包括什么？|Turn 4|好的，预约这个|Turn 5|下周末可以吗？|Turn 6|刘洋，18900007777" \
    "Appointment Booking Flow" \
    "Health checkup booking"

# Category 9: Product Purchase Flows (51-55)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 9: PRODUCT PURCHASE FLOWS =====${NC}"

test_api_followup 51 "purchase_user_1" \
    "Turn 1|我想买维生素C|Turn 2|有哪些品牌？|Turn 3|价格分别是多少？|Turn 4|要最便宜的那个|Turn 5|买两瓶|Turn 6|怎么付款？" \
    "Product Purchase Flow" \
    "Complete vitamin purchase"

test_api_followup 52 "purchase_user_2" \
    "Turn 1|有血压计吗？|Turn 2|推荐一个家用的|Turn 3|这个准确吗？|Turn 4|好，我要这个|Turn 5|可以送货上门吗？" \
    "Product Purchase Flow" \
    "Medical device purchase"

test_api_followup 53 "purchase_user_3" \
    "Turn 1|孕妇吃什么钙片好？|Turn 2|有进口的吗？|Turn 3|国产的呢？|Turn 4|那就国产的吧，便宜点|Turn 5|一盒能吃多久？|Turn 6|买3盒" \
    "Product Purchase Flow" \
    "Pregnancy supplement purchase"

test_api_followup 54 "purchase_user_4" \
    "Turn 1|失眠用什么产品？|Turn 2|褪黑素有副作用吗？|Turn 3|还有其他选择吗？|Turn 4|那个中药的多少钱？|Turn 5|先买一盒试试" \
    "Product Purchase Flow" \
    "Sleep aid purchase with concerns"

test_api_followup 55 "purchase_user_5" \
    "Turn 1|老人补钙吃什么？|Turn 2|液体钙和片剂哪个好？|Turn 3|维生素D要一起吃吗？|Turn 4|有套装吗？|Turn 5|好，买个套装" \
    "Product Purchase Flow" \
    "Elderly supplement package"

# Category 10: Medical Consultation Flows (56-60)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 10: MEDICAL CONSULTATION FLOWS =====${NC}"

test_api_followup 56 "consult_user_1" \
    "Turn 1|我最近老是头疼|Turn 2|已经一个星期了|Turn 3|主要是下午会疼|Turn 4|需要看什么科？|Turn 5|好的，帮我预约神经内科" \
    "Medical Consultation Flow" \
    "Symptom to appointment"

test_api_followup 57 "consult_user_2" \
    "Turn 1|小孩发烧怎么办？|Turn 2|38.5度|Turn 3|已经烧了两天|Turn 4|需要马上去医院吗？|Turn 5|好，帮我预约儿科急诊" \
    "Medical Consultation Flow" \
    "Urgent care consultation"

test_api_followup 58 "consult_user_3" \
    "Turn 1|体检报告显示血糖偏高|Turn 2|空腹血糖6.8|Turn 3|需要吃药吗？|Turn 4|应该看哪个科？|Turn 5|帮我预约内分泌科医生" \
    "Medical Consultation Flow" \
    "Test results consultation"

test_api_followup 59 "consult_user_4" \
    "Turn 1|怀孕三个月了|Turn 2|需要做什么检查？|Turn 3|NT检查是什么？|Turn 4|什么时候做合适？|Turn 5|帮我预约产科检查" \
    "Medical Consultation Flow" \
    "Pregnancy consultation"

test_api_followup 60 "consult_user_5" \
    "Turn 1|最近睡不好|Turn 2|入睡困难，容易醒|Turn 3|已经持续一个月了|Turn 4|可能是什么原因？|Turn 5|需要看心理科吗？|Turn 6|好，帮我预约" \
    "Medical Consultation Flow" \
    "Sleep disorder consultation"

# Category 11: Memory and Context Tests (61-65)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 11: MEMORY AND CONTEXT TESTS =====${NC}"

test_api_followup 61 "memory_user_4" \
    "Turn 1|我住在上海，40岁|Turn 2|我有糖尿病史|Turn 3|最近血糖控制不好|Turn 4|帮我找个好的内分泌医生|Turn 5|要离我家近的" \
    "Memory Context Flow" \
    "Location and condition aware booking"

test_api_followup 62 "memory_user_5" \
    "Turn 1|我儿子8岁，经常咳嗽|Turn 2|每年冬天都会发作|Turn 3|可能是过敏吗？|Turn 4|上海哪里看儿童过敏好？|Turn 5|帮我预约检查" \
    "Memory Context Flow" \
    "Child health history"

test_api_followup 63 "memory_user_6" \
    "Turn 1|我上次在你们这看的骨科|Turn 2|医生说要复查|Turn 3|是张伟医生|Turn 4|能约同一个医生吗？|Turn 5|下周二可以吗？" \
    "Memory Context Flow" \
    "Follow-up appointment"

test_api_followup 64 "memory_user_7" \
    "Turn 1|我妈妈70岁了|Turn 2|她有高血压和糖尿病|Turn 3|最近想做个全面体检|Turn 4|有适合老年人的套餐吗？|Turn 5|包括哪些项目？|Turn 6|好的，预约这个" \
    "Memory Context Flow" \
    "Family member health management"

test_api_followup 65 "memory_user_8" \
    "Turn 1|记住我对青霉素过敏|Turn 2|我还对花粉过敏|Turn 3|春天症状会加重|Turn 4|有什么预防的药吗？|Turn 5|需要提前多久开始吃？" \
    "Memory Context Flow" \
    "Allergy management"

# Category 12: Error Recovery and Edge Cases (66-70)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 12: ERROR RECOVERY AND EDGE CASES =====${NC}"

test_api_followup 66 "error_user_1" \
    "Turn 1|我想预约张三医生|Turn 2|哦，那有其他骨科医生吗？|Turn 3|张伟医生也可以|Turn 4|明天有号吗？|Turn 5|那后天呢？|Turn 6|好的，后天上午，陈明，13300001111" \
    "Error Recovery Flow" \
    "Doctor not found recovery"

test_api_followup 67 "error_user_2" \
    "Turn 1|取消预约|Turn 2|忘记预约号了|Turn 3|手机号是13800138000|Turn 4|不对，是13800138001|Turn 5|对，是明天的那个" \
    "Error Recovery Flow" \
    "Incorrect information correction"

test_api_followup 68 "error_user_3" \
    "Turn 1|我要最贵的体检套餐|Turn 2|太贵了，有便宜点的吗？|Turn 3|5000以内的|Turn 4|这个包括什么？|Turn 5|可以分期付款吗？" \
    "Error Recovery Flow" \
    "Price adjustment flow"

test_api_followup 69 "error_user_4" \
    "Turn 1|帮我预约明天的医生|Turn 2|哦忘了说，要妇科的|Turn 3|深圳的|Turn 4|不对，我在广州|Turn 5|下午2点可以吗？" \
    "Error Recovery Flow" \
    "Multiple corrections"

test_api_followup 70 "error_user_5" \
    "Turn 1|买维生素|Turn 2|不是维生素C，是维生素D|Turn 3|成人吃的|Turn 4|不对，是给小孩吃的|Turn 5|3岁小孩|Turn 6|要草莓味的" \
    "Error Recovery Flow" \
    "Product selection corrections"

# Summary
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}TEST SUITE COMPLETED!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n## Summary" >> "$RESULTS_FILE"
echo "- Total tests: 70 (40 single-turn + 30 multi-turn conversations)" >> "$RESULTS_FILE"
echo "- Categories tested: Identity, Doctor Search, Appointments, Clinics, Medical, Memory, Products" >> "$RESULTS_FILE"
echo "- New categories: Complete Booking Flows, Purchase Flows, Consultation Flows, Context Testing, Error Recovery" >> "$RESULTS_FILE"
echo "- Process log: $PROCESS_LOG" >> "$RESULTS_FILE"
echo "- Results saved to: $RESULTS_FILE" >> "$RESULTS_FILE"

echo -e "\n${GREEN}✅ Results saved to:${NC}"
echo -e "   - Main results: ${RESULTS_FILE}"
echo -e "   - Process log: ${PROCESS_LOG}"
echo -e "   - Server log: server_enhanced.log"

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
kill $SERVER_PID 2>/dev/null
echo -e "${GREEN}✅ Server stopped${NC}"

echo -e "\n${BOLD}Next steps:${NC}"
echo "1. Review the main results in: $RESULTS_FILE"
echo "2. Analyze the detailed process flow in: $PROCESS_LOG"
echo "3. Check server logs for errors in: server_enhanced.log"
echo "4. Look for patterns in agent thinking and tool usage"