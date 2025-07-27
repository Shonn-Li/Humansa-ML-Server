#!/bin/bash
# Humansa V2 - 40 Comprehensive Test Cases (Including Products)
# Based on V2_TEST_CASES.md with product tests

echo "============================================"
echo "HUMANSA AI AGENT V2 - 40 TEST CASES"
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
export ML_SERVER_PORT=5001
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

# Step 2: Run SQL scripts to populate test data
echo -e "\n${YELLOW}Step 2: Populating test database...${NC}"
cd test_environment/sql
for script in *.sql; do
    echo "Running $script..."
    PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -f "$script" > /dev/null 2>&1
done

# Also load our Humansa test data
if [ -f "humansa_test_doctors.sql" ]; then
    echo "Loading Humansa test doctors..."
    PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -f "humansa_test_doctors.sql" > /dev/null 2>&1
fi

cd ../..
echo -e "${GREEN}✅ Test data populated${NC}"

# Step 3: Start the ML server
echo -e "\n${YELLOW}Step 3: Starting ML server on port ${ML_SERVER_PORT}...${NC}"
# Kill any existing server on port 5001
lsof -ti:${ML_SERVER_PORT} | xargs -r kill -9 2>/dev/null
sleep 2
# Start server with test environment (it always uses port 5001)
python -m src.main > server_test.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:${ML_SERVER_PORT}/health > /dev/null; then
        echo -e "${GREEN}✅ Server is ready${NC}"
        break
    fi
    sleep 1
done

# Create results directory
mkdir -p test_results_v2_40cases
TEST_RESULTS_DIR="test_results_v2_40cases"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="${TEST_RESULTS_DIR}/results_${TIMESTAMP}.md"

# Function to test API with enhanced output capture
test_api() {
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
    
    # Log to results file
    echo -e "\n## Test #${test_num}: ${category}" >> "$RESULTS_FILE"
    echo -e "**Description:** ${description}" >> "$RESULTS_FILE"
    echo -e "**User:** ${user_id}" >> "$RESULTS_FILE"
    echo -e "**Query:** ${query}" >> "$RESULTS_FILE"
    echo -e "**Time:** $(date)" >> "$RESULTS_FILE"
    
    # Make API call with streaming
    echo -e "\n${YELLOW}Response:${NC}"
    echo -e "\n### Response:" >> "$RESULTS_FILE"
    echo '```' >> "$RESULTS_FILE"
    
    response=$(curl -s -X POST http://localhost:${ML_SERVER_PORT}/v2/humansa/chat \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"${user_id}\",
            \"messages\": [{\"role\": \"user\", \"content\": \"${query}\"}],
            \"stream\": false
        }")
    
    # Extract and display the content
    content=$(echo "$response" | jq -r '.choices[0].message.content' 2>/dev/null)
    if [ "$content" != "null" ] && [ ! -z "$content" ]; then
        echo -e "${GREEN}$content${NC}"
        echo "$content" >> "$RESULTS_FILE"
    else
        echo -e "${RED}Error or no content in response${NC}"
        echo "Error: $response" >> "$RESULTS_FILE"
    fi
    
    echo '```' >> "$RESULTS_FILE"
    
    # Brief pause between tests
    sleep 2
}

# Initialize results file
echo "# Humansa V2 - 40 Test Cases Results" > "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "Environment: Test (Port 5454)" >> "$RESULTS_FILE"

# Category 1: Identity and Introduction Tests (1-5)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 1: IDENTITY AND INTRODUCTION TESTS =====${NC}"

test_api 1 "test_user_1" "你好" "Identity" "Basic greeting"
test_api 2 "test_user_2" "你是谁？" "Identity" "Direct identity query"
test_api 3 "test_user_3" "介绍一下诺亚新舟" "Identity" "Company introduction"
test_api 4 "test_user_4" "你们的口号是什么？" "Identity" "Company slogan"
test_api 5 "test_user_5" "你能做什么？" "Identity" "Capability inquiry"

# Category 2: Doctor Search Tests (6-10)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 2: DOCTOR SEARCH TESTS =====${NC}"

test_api 6 "test_user_6" "我想找个骨科医生" "Doctor Search" "Specialty-based search"
test_api 7 "test_user_7" "张三医生在吗？" "Doctor Search" "Name-based search"
test_api 8 "test_user_8" "北京有哪些医生？" "Doctor Search" "Location-based search"
test_api 9 "test_user_9" "最贵的医生是谁？" "Doctor Search" "Price-based search"
test_api 10 "test_user_10" "有会说英语的医生吗？" "Doctor Search" "Language preference"

# Category 3: Appointment Booking Tests (11-15)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 3: APPOINTMENT BOOKING TESTS =====${NC}"

test_api 11 "test_user_11" "我想预约张三医生" "Appointment" "Direct doctor booking"
test_api 12 "test_user_12" "帮我预约明天上午的骨科" "Appointment" "Time-based booking"
test_api 13 "test_user_13" "查看下周的可预约时间" "Appointment" "Availability check"
test_api 14 "test_user_14" "取消我的预约" "Appointment" "Cancellation request"
test_api 15 "test_user_15" "改约到下周三" "Appointment" "Rescheduling request"

# Category 4: Clinic and Service Tests (16-20)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 4: CLINIC AND SERVICE TESTS =====${NC}"

test_api 16 "test_user_16" "离我最近的诊所在哪？" "Clinic" "Location query"
test_api 17 "test_user_17" "血常规多少钱？" "Service" "Price inquiry"
test_api 18 "test_user_18" "体检套餐有哪些？" "Service" "Package inquiry"
test_api 19 "test_user_19" "诊所几点开门？" "Clinic" "Hours inquiry"
test_api 20 "test_user_20" "上海诊所的电话是多少？" "Clinic" "Contact info"

# Category 5: Medical Consultation Tests (21-25)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 5: MEDICAL CONSULTATION TESTS =====${NC}"

test_api 21 "test_user_21" "我最近总是失眠怎么办？" "Medical" "Sleep issue"
test_api 22 "test_user_22" "孩子发烧39度该怎么处理？" "Medical" "Fever management"
test_api 23 "test_user_23" "胸口疼痛呼吸困难" "Medical" "Emergency symptoms"
test_api 24 "test_user_24" "高血压能吃什么药？" "Medical" "Medication query"
test_api 25 "test_user_25" "体检报告显示血糖偏高" "Medical" "Test result interpretation"

# Category 6: Memory Persistence Tests (26-30)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 6: MEMORY PERSISTENCE TESTS =====${NC}"

# First, store information
test_api 26 "memory_test_user_1" "我叫张三，住在北京，今年45岁" "Memory" "Store personal info"
test_api 26.2 "memory_test_user_1" "我对花生和海鲜过敏" "Memory" "Store allergies"
test_api 26.3 "memory_test_user_1" "我有高血压，每天吃降压药" "Memory" "Store medical condition"

# Then, test recall
test_api 27 "memory_test_user_1" "你知道我的基本信息吗？" "Memory" "Recall personal info"
test_api 28 "memory_test_user_1" "我有什么过敏史和慢性病？" "Memory" "Recall medical history"

# Cross-session continuity
test_api 29 "memory_test_user_2" "我想找骨科医生，我膝盖老是疼" "Memory" "Session 1"
test_api 29.2 "memory_test_user_2" "上次我说的膝盖问题，有推荐的医生吗？" "Memory" "Session 2 continuity"

# Complex memory integration
test_api 30 "memory_test_user_3" "我住在深圳，想找离家近的诊所" "Memory" "Store location"
test_api 30.2 "memory_test_user_3" "我女儿5岁，经常感冒" "Memory" "Store child info"
test_api 30.3 "memory_test_user_3" "推荐一个适合看儿童感冒的医生，最好在我附近" "Memory" "Complex integration"

# Category 7: Product Recommendation Tests (31-40)
echo -e "\n${MAGENTA}${BOLD}===== CATEGORY 7: PRODUCT RECOMMENDATION TESTS =====${NC}"

test_api 31 "test_user_31" "你们有什么保健品推荐吗？" "Product" "General product inquiry"
test_api 32 "test_user_32" "我想买维生素D，有什么推荐？" "Product" "Vitamin recommendation"
test_api 33 "test_user_33" "家里老人需要血压计，推荐一款" "Product" "Medical equipment"
test_api 34 "test_user_34" "有500元以下的保健品吗？" "Product" "Price range filter"
test_api 35 "test_user_35" "我失眠严重，有什么产品可以帮助睡眠？" "Product" "Health condition based"
test_api 36 "test_user_36" "有医美面膜吗？" "Product" "Beauty product"
test_api 37 "test_user_37" "有什么健康套餐推荐？" "Product" "Package recommendation"
test_api 38 "test_user_38" "孕妇需要补充什么营养品？" "Product" "Mother-baby products"
test_api 39 "test_user_39" "有西洋参吗？" "Product" "Traditional Chinese medicine"
test_api 40 "test_user_40" "怎么购买这些产品？" "Product" "Purchase guidance"

# Summary
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}TEST SUITE COMPLETED!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n## Summary" >> "$RESULTS_FILE"
echo "- Total tests: 40 (+ memory sub-tests)" >> "$RESULTS_FILE"
echo "- Categories tested: Identity, Doctor Search, Appointments, Clinics, Medical, Memory, Products" >> "$RESULTS_FILE"
echo "- Results saved to: $RESULTS_FILE" >> "$RESULTS_FILE"

echo -e "\n${GREEN}✅ Results saved to: ${RESULTS_FILE}${NC}"

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
kill $SERVER_PID 2>/dev/null
echo -e "${GREEN}✅ Server stopped${NC}"

echo -e "\n${BOLD}Next steps:${NC}"
echo "1. Review the results in: $RESULTS_FILE"
echo "2. Check server logs in: server_test.log"
echo "3. Analyze response accuracy and completeness"