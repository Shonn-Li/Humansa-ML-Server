#!/bin/bash
# HUMANSA V2 - Run 30 tests in batches to avoid timeout

echo "============================================"
echo "HUMANSA AI AGENT V2 - BATCH TEST RUNNER"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "youwo-ml-venv/bin/activate" ]; then
    source youwo-ml-venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
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

# Check PostgreSQL
if ! pg_isready -h localhost -p 5454 -U postgres > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL test database is not running${NC}"
    exit 1
fi

# Kill existing processes
lsof -ti :6001 | xargs kill -9 2>/dev/null || true
sleep 2

# Start server
echo -e "\n${YELLOW}Starting ML server...${NC}"
python3 -m src.main --port 6001 > server_v2_batch_test.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server
echo -n "Waiting for server"
for i in {1..30}; do
    if curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Server ready${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
    echo -e "\n${RED}❌ Server failed to start${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Create batch test runner
cat > run_batch_tests.py << 'BATCHTEST'
#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:6001"

# All 30 test cases split into batches
BATCHES = [
    # Batch 1: Identity tests (1-5)
    [
        {"id": 1, "query": "你是谁？", "user_id": 123},
        {"id": 2, "query": "Who are you?", "user_id": 123},
        {"id": 3, "query": "你好", "user_id": 123},
        {"id": 5, "query": "你能做什么？", "user_id": 123}
    ],
    # Batch 2: Doctor Search (6-10)
    [
        {"id": 6, "query": "我想找一个心脏科医生", "user_id": 124},
        {"id": 7, "query": "深圳有哪些医生？", "user_id": 124},
        {"id": 8, "query": "张医生的信息", "user_id": 124},
        {"id": 9, "query": "李医生下周有空吗？", "user_id": 124},
        {"id": 10, "query": "北京的骨科医生，要有20年以上经验", "user_id": 124}
    ],
    # Batch 3: Appointments (11-15)
    [
        {"id": 11, "query": "预约王医生，我叫李明，电话13800138000，想看下周二下午", "user_id": 125},
        {"id": 12, "query": "帮我预约张医生", "user_id": 126},
        {"id": 13, "query": "我叫王芳，电话15900159000", "user_id": 126},
        {"id": 14, "query": "改一下我明天的预约，改到后天同一时间", "user_id": 125},
        {"id": 15, "query": "取消我下周三的预约", "user_id": 125}
    ],
    # Batch 4: Clinic Services (16-20)
    [
        {"id": 16, "query": "广州有哪些诊所？", "user_id": 127},
        {"id": 17, "query": "深圳诊所提供什么服务？", "user_id": 127},
        {"id": 18, "query": "肝功能检查多少钱？", "user_id": 127},
        {"id": 19, "query": "哪里的体检套餐最便宜？", "user_id": 127},
        {"id": 20, "query": "核磁共振检查需要准备什么？", "user_id": 127}
    ],
    # Batch 5: Medical & Emergency (21-25)
    [
        {"id": 21, "query": "最近总是失眠，还头痛", "user_id": 128},
        {"id": 22, "query": "我现在胸痛很厉害，呼吸困难", "user_id": 128},
        {"id": 23, "query": "阿司匹林和华法林能一起吃吗？", "user_id": 128},
        {"id": 24, "query": "我想买保健品", "user_id": 128},
        {"id": 25, "query": "头晕应该看什么科？", "user_id": 128}
    ],
    # Batch 6: Memory tests (26-30)
    [
        {"id": 26, "query": "我叫张三，住在北京，今年45岁", "user_id": "memory_test_user_1"},
        {"id": 27, "query": "我对花生和海鲜过敏，有高血压，每天吃降压药", "user_id": "memory_test_user_1"},
        {"id": 28, "query": "你知道我的基本信息吗？", "user_id": "memory_test_user_1"},
        {"id": 29, "query": "我有什么过敏史和慢性病？", "user_id": "memory_test_user_1"},
        {"id": 30, "query": "根据我的情况，推荐合适的医生", "user_id": "memory_test_user_1"}
    ]
]

async def test_single(session, test_case):
    try:
        request_data = {
            "user_id": test_case["user_id"],
            "messages": [{"role": "user", "content": test_case["query"]}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=20)
        ) as response:
            if response.status == 200:
                result = await response.json()
                return {
                    "id": test_case["id"],
                    "success": True,
                    "response": result['choices'][0]['message']['content']
                }
            else:
                return {
                    "id": test_case["id"],
                    "success": False,
                    "error": f"HTTP {response.status}"
                }
    except Exception as e:
        return {
            "id": test_case["id"],
            "success": False,
            "error": str(e)
        }

async def run_batch(batch_num, tests):
    print(f"\nRunning Batch {batch_num} ({len(tests)} tests)...")
    async with aiohttp.ClientSession() as session:
        results = []
        for test in tests:
            print(f"  Test {test['id']}: {test['query'][:50]}...")
            result = await test_single(session, test)
            if result['success']:
                print(f"    ✅ Success")
            else:
                print(f"    ❌ Failed: {result.get('error')}")
            results.append(result)
            
            # Add delay between tests
            if test['id'] in [27, 28, 29, 30]:  # Memory tests need more time
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(0.5)
        
        return results

async def main():
    all_results = []
    
    for i, batch in enumerate(BATCHES, 1):
        batch_results = await run_batch(i, batch)
        all_results.extend(batch_results)
        
        # Save intermediate results
        with open(f"batch_{i}_results.json", "w") as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
    
    # Save final results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"humansa_v2_all_30_results_{timestamp}.json", "w") as f:
        json.dump({
            "timestamp": timestamp,
            "total": len(all_results),
            "passed": sum(1 for r in all_results if r['success']),
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Completed all {len(all_results)} tests")
    print(f"Passed: {sum(1 for r in all_results if r['success'])}/{len(all_results)}")

if __name__ == "__main__":
    asyncio.run(main())
BATCHTEST

# Run batch tests
echo -e "\n${YELLOW}Running tests in batches...${NC}"
python3 run_batch_tests.py

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
kill $SERVER_PID 2>/dev/null || true

echo -e "\n${GREEN}✅ Batch testing completed!${NC}"
echo "Results saved to:"
echo "  - batch_*_results.json (individual batches)"
echo "  - humansa_v2_all_30_results_*.json (all results)"
echo "  - server_v2_batch_test.log (server logs)"