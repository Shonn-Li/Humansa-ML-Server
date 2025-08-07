#!/bin/bash
# HUMANSA V2 - 40 Comprehensive Test Cases with Enhanced Logging
# Shows full agent thinking, tool calls, memory context, and responses

echo "============================================"
echo "HUMANSA AI AGENT V2 - 40 TEST CASES"
echo "WITH ENHANCED PROCESS LOGGING"
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

# Function to test API with Response API and enhanced process logging
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
    
    # Create request payload for Response API
    request_payload=$(cat <<EOF
{
    "model": "gpt-4-turbo",
    "input": "${query}",
    "user_id": "${user_id}",
    "metadata": {"test_id": ${test_num}, "debug": true}
}
EOF
)
    
    # Stream the response using Response API and capture all steps
    echo -e "${GREEN}Agent Response:${NC}"
    echo -e "${YELLOW}🔍 Showing tool calls and reasoning...${NC}"
    
    # Use curl with -N flag for no buffering
    full_response=""
    while IFS= read -r line; do
        # Remove "data: " prefix
        if [[ $line == data:* ]]; then
            data="${line#data: }"
            
            # Skip [DONE] message
            if [[ $data == "[DONE]" ]]; then
                break
            fi
            
            # Parse JSON chunk
            if [[ ! -z "$data" ]]; then
                # Parse Response API events
                event_type=$(echo "$data" | jq -r '.event // empty' 2>/dev/null)
                
                if [[ $event_type == "response.created" ]]; then
                    response_id=$(echo "$data" | jq -r '.data.id // empty' 2>/dev/null)
                    echo -e "${BLUE}📝 Response ID: ${response_id}${NC}"
                    echo "Response ID: ${response_id}" >> "$PROCESS_LOG"
                    
                elif [[ $event_type == "response.output_item.done" ]]; then
                    item=$(echo "$data" | jq -r '.data.item // empty' 2>/dev/null)
                    item_type=$(echo "$item" | jq -r '.type // empty' 2>/dev/null)
                    
                    if [[ $item_type == "text" ]]; then
                        text=$(echo "$item" | jq -r '.text // empty' 2>/dev/null)
                        # Check if it's thinking or final response
                        if [[ $text == *"思考"* ]] || [[ $text == *"Thought"* ]]; then
                            echo -e "${CYAN}💭 Thinking: ${text:0:100}...${NC}"
                            echo "💭 Thinking: ${text}" >> "$PROCESS_LOG"
                        else
                            full_response="$text"
                            echo -e "${GREEN}$text${NC}"
                            echo "$text" >> "$PROCESS_LOG"
                        fi
                        
                    elif [[ $item_type == "tool_use" ]]; then
                        tool_name=$(echo "$item" | jq -r '.tool_use.name // empty' 2>/dev/null)
                        tool_input=$(echo "$item" | jq -r '.tool_use.input // empty' 2>/dev/null)
                        echo -e "${BLUE}🔧 Tool Use: ${tool_name}${NC}"
                        echo -e "${BLUE}   Input: ${tool_input}${NC}"
                        echo "🔧 Tool Use: ${tool_name}" >> "$PROCESS_LOG"
                        echo "   Input: ${tool_input}" >> "$PROCESS_LOG"
                        
                    elif [[ $item_type == "tool_result" ]]; then
                        tool_output=$(echo "$item" | jq -r '.tool_result.output // empty' 2>/dev/null)
                        echo -e "${MAGENTA}📊 Tool Result: ${tool_output:0:100}...${NC}"
                        echo "📊 Tool Result: ${tool_output}" >> "$PROCESS_LOG"
                    fi
                    
                elif [[ $event_type == "response.done" ]]; then
                    usage=$(echo "$data" | jq -r '.data.usage // empty' 2>/dev/null)
                    total_tokens=$(echo "$usage" | jq -r '.total_tokens // 0' 2>/dev/null)
                    echo -e "${CYAN}📈 Tokens used: ${total_tokens}${NC}"
                    echo "📈 Tokens used: ${total_tokens}" >> "$PROCESS_LOG"
                fi
            fi
        fi
    done < <(curl -sN -X POST "http://localhost:${ML_SERVER_PORT}/v2/humansa/responses/stream" \
        -H "Content-Type: application/json" \
        -d "$request_payload")
    
    echo # New line after streaming
    echo '```' >> "$PROCESS_LOG"
    
    # Log to main results file
    echo -e "\n## Test #${test_num}: ${category}" >> "$RESULTS_FILE"
    echo -e "**Description:** ${description}" >> "$RESULTS_FILE"
    echo -e "**User:** ${user_id}" >> "$RESULTS_FILE"
    echo -e "**Query:** ${query}" >> "$RESULTS_FILE"
    echo -e "\n### Response:" >> "$RESULTS_FILE"
    echo '```' >> "$RESULTS_FILE"
    echo "$full_response" >> "$RESULTS_FILE"
    echo '```' >> "$RESULTS_FILE"
    
    # Brief pause between tests
    sleep 2
}

# Initialize results files
echo "# HUMANSA V2 - 40 Test Cases Results" > "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "Environment: Test (Port 5454)" >> "$RESULTS_FILE"
echo "Mode: Enhanced Logging with Process Flow" >> "$RESULTS_FILE"

echo "# HUMANSA V2 - Process Flow Log" > "$PROCESS_LOG"
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

# Summary
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}TEST SUITE COMPLETED!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n## Summary" >> "$RESULTS_FILE"
echo "- Total tests: 40 (+ memory sub-tests)" >> "$RESULTS_FILE"
echo "- Categories tested: Identity, Doctor Search, Appointments, Clinics, Medical, Memory, Products" >> "$RESULTS_FILE"
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