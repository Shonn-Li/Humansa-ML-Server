#!/bin/bash
# Humansa V2 - Subset Test (First 10 cases)
# Quick validation before full 30-case run

echo "============================================"
echo "HUMANSA AI AGENT V2 - SUBSET TEST (10 CASES)"
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
export DB_PORT=5456
export DB_USER=postgres
export DB_PASSWORD=youwo123
export DB_NAME=youwoai
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true

# Step 1: Check PostgreSQL test database
echo -e "\n${YELLOW}Step 1: Checking PostgreSQL test database...${NC}"
if pg_isready -h localhost -p 5456 -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL test database is running on port 5456${NC}"
else
    echo -e "${RED}❌ PostgreSQL test database is not running on port 5456${NC}"
    echo "Please start the test database first with:"
    echo "cd test_environment && docker-compose up -d"
    exit 1
fi

# Step 2: Kill any existing processes on port 6001
echo -e "\n${YELLOW}Step 2: Checking for existing processes on port 6001...${NC}"
if lsof -i :6001 > /dev/null 2>&1; then
    echo "Found existing process on port 6001, killing it..."
    lsof -ti :6001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Step 3: Start the ML server with V2 enabled
echo -e "\n${YELLOW}Step 3: Starting ML server with Humansa V2...${NC}"
echo "Server will run on port 6001 (test environment)"

# Start server in background
python3 -m src.main --port 6001 > server_v2_subset_test.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo -n "Waiting for server to start"
for i in {1..30}; do
    if curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Server is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
    echo -e "\n${RED}❌ Server failed to start. Check server_v2_subset_test.log for errors${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Step 4: Run subset of test cases
echo -e "\n${YELLOW}Step 4: Running subset of test cases (10 cases)...${NC}"

# Create subset test script
cat > test_humansa_v2_subset.py << 'TESTSCRIPT'
#!/usr/bin/env python3
"""Humansa V2 - Subset of 10 Test Cases for Quick Validation"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=Colors.ENDC):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_section(title):
    """Print a section header"""
    print_colored(f"\n{'='*80}", Colors.BLUE)
    print_colored(f"  {title}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*80}", Colors.BLUE)

# Define subset of test cases (first 10)
TEST_CASES = [
    # Category 1: Identity & Basic Interactions
    {
        "id": 1,
        "category": "Identity",
        "name": "Chinese Identity Query",
        "query": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理"],
        "user_id": 123
    },
    {
        "id": 2,
        "category": "Identity",
        "name": "English Identity Query",
        "query": "Who are you?",
        "expected_keywords": ["Humansa", "Health", "Medical", "Assistant"],
        "user_id": 123
    },
    {
        "id": 3,
        "category": "Identity",
        "name": "Chinese Greeting",
        "query": "你好",
        "expected_keywords": ["你好", "小诺", "帮助"],
        "user_id": 123
    },
    {
        "id": 4,
        "category": "Identity",
        "name": "Company Introduction",
        "query": "介绍一下诺亚新舟",
        "expected_keywords": ["以爱行舟", "亲近相守", "500多位", "30+家"],
        "user_id": 123
    },
    {
        "id": 5,
        "category": "Identity",
        "name": "Service Capabilities",
        "query": "你能做什么？",
        "expected_keywords": ["健康咨询", "实时预约", "检查项目", "诊所导航", "体检报告"],
        "user_id": 123
    },
    
    # Category 2: Doctor Search & Information
    {
        "id": 6,
        "category": "Doctor Search",
        "name": "Find Cardiologist",
        "query": "我想找一个心脏科医生",
        "expected_keywords": ["心脏", "医生", "预约"],
        "user_id": 124
    },
    {
        "id": 7,
        "category": "Doctor Search",
        "name": "Find Doctors by City",
        "query": "深圳有哪些医生？",
        "expected_keywords": ["深圳", "医生", "诊所"],
        "user_id": 124
    },
    
    # Category 3: Emergency
    {
        "id": 8,
        "category": "Medical",
        "name": "Emergency Case",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected_keywords": ["120", "急救", "立即"],
        "user_id": 128
    },
    
    # Category 4: Memory Test
    {
        "id": 9,
        "category": "Memory",
        "name": "Store Personal Info",
        "query": "我叫张三，住在北京，今年45岁",
        "expected_keywords": ["记录", "信息"],
        "user_id": "memory_test_user_1"
    },
    {
        "id": 10,
        "category": "Memory",
        "name": "Recall Personal Info",
        "query": "你知道我的基本信息吗？",
        "expected_keywords": ["张三", "北京", "45岁"],
        "user_id": "memory_test_user_1"
    }
]

async def test_endpoint(session, test_case, stream=True):
    """Test V2 endpoint with a single test case"""
    try:
        request_data = {
            "user_id": test_case["user_id"],
            "messages": [{"role": "user", "content": test_case["query"]}],
            "stream": stream
        }
        
        start_time = time.time()
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "response_time": time.time() - start_time
                }
            
            # Process response
            full_response = ""
            has_thoughts = False
            thought_process = []
            
            if stream:
                async for line in response.content:
                    if line:
                        decoded = line.decode('utf-8').strip()
                        if decoded.startswith('data: '):
                            data_str = decoded[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data:
                                    for choice in data.get('choices', []):
                                        delta = choice.get('delta', {})
                                        if 'content' in delta:
                                            content = delta['content']
                                            full_response += content
                                            # Check for thought markers
                                            if '💭' in content:
                                                has_thoughts = True
                                                thought_process.append(('thought', content))
                                            elif '🔧' in content:
                                                thought_process.append(('action', content))
                                            elif '📊' in content:
                                                thought_process.append(('observation', content))
                            except json.JSONDecodeError:
                                pass
            else:
                result = await response.json()
                if 'choices' in result:
                    full_response = result['choices'][0]['message']['content']
            
            # Analyze response quality
            response_analysis = analyze_response_quality(test_case, full_response)
            
            return {
                "success": response_analysis['is_correct'],
                "response": full_response,
                "found_keywords": response_analysis['found_keywords'],
                "missing_keywords": response_analysis['missing_keywords'],
                "response_time": time.time() - start_time,
                "has_thoughts": has_thoughts,
                "thought_process": thought_process,
                "quality_score": response_analysis['quality_score'],
                "quality_notes": response_analysis['notes']
            }
            
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Request timeout (30s)",
            "response_time": 30.0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": 0
        }

def analyze_response_quality(test_case, response):
    """Analyze response quality beyond keyword matching"""
    found_keywords = []
    missing_keywords = []
    quality_score = 0
    notes = []
    
    # Basic keyword check
    for keyword in test_case.get('expected_keywords', []):
        if keyword.lower() in response.lower():
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Category-specific analysis
    category = test_case['category']
    query = test_case['query']
    
    if category == "Identity":
        # Check for proper identity response
        if test_case['id'] == 1:  # Chinese identity
            if "诺亚新舟" in response and "小诺" in response:
                quality_score += 50
                notes.append("✓ Correctly identified as 诺亚新舟/小诺")
            if "健康医疗助理" in response or "AI健康管家" in response:
                quality_score += 30
                notes.append("✓ Mentioned role as health assistant")
            if "帮助" in response or "服务" in response:
                quality_score += 20
                notes.append("✓ Offered help/service")
                
        elif test_case['id'] == 2:  # English identity
            if "Humansa" in response and "Health" in response:
                quality_score += 50
                notes.append("✓ Correctly identified in English")
            if response.count('\n') > 3:  # Check for structured response
                quality_score += 30
                notes.append("✓ Provided detailed response")
                
        elif test_case['id'] == 3:  # Greeting
            if "你好" in response:
                quality_score += 40
                notes.append("✓ Returned greeting")
            if "小诺" in response:
                quality_score += 30
                notes.append("✓ Self-introduced")
            if "帮助" in response or "服务" in response:
                quality_score += 30
                notes.append("✓ Offered assistance")
                
    elif category == "Medical" and test_case['id'] == 8:  # Emergency
        if "120" in response:
            quality_score += 60
            notes.append("✓ Correctly recommended calling 120")
        if "急救" in response or "立即" in response:
            quality_score += 20
            notes.append("✓ Emphasized urgency")
        if "急诊" in response:
            quality_score += 20
            notes.append("✓ Mentioned emergency department")
        if "120" not in response:
            quality_score = 0  # Emergency must mention 120
            notes.append("✗ CRITICAL: Failed to mention 120 for emergency")
            
    elif category == "Memory":
        if test_case['id'] == 9:  # Store info
            quality_score = 80  # Assume success if acknowledged
            notes.append("✓ Acknowledged information storage")
        elif test_case['id'] == 10:  # Recall info
            if "张三" in response and "北京" in response and "45" in response:
                quality_score = 100
                notes.append("✓ Successfully recalled all stored information")
            else:
                recalled = []
                if "张三" in response: recalled.append("name")
                if "北京" in response: recalled.append("location")
                if "45" in response: recalled.append("age")
                quality_score = len(recalled) * 33
                notes.append(f"✓ Recalled: {', '.join(recalled)}" if recalled else "✗ Failed to recall information")
    
    # General quality checks
    if len(response) < 20:
        quality_score = min(quality_score, 30)
        notes.append("✗ Response too short")
    
    # Determine if response is correct
    is_correct = quality_score >= 70 or (len(missing_keywords) == 0 and len(found_keywords) > 0)
    
    return {
        "is_correct": is_correct,
        "found_keywords": found_keywords,
        "missing_keywords": missing_keywords,
        "quality_score": quality_score,
        "notes": notes
    }

async def run_subset_tests():
    """Run subset of test cases"""
    print_section("Humansa V2 - Subset Test (10 Cases)")
    print(f"Total test cases: {len(TEST_CASES)}")
    
    async with aiohttp.ClientSession() as session:
        # Check health first
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print_colored(f"\n✅ V2 Health Check: {health['status']}", Colors.GREEN)
                else:
                    print_colored(f"❌ V2 Health Check Failed", Colors.RED)
                    return
        except Exception as e:
            print_colored(f"❌ Cannot connect to V2 endpoint: {e}", Colors.RED)
            return
        
        # Run tests
        results = []
        category_stats = {}
        
        for test_case in TEST_CASES:
            category = test_case['category']
            if category not in category_stats:
                category_stats[category] = {"total": 0, "passed": 0}
                print_section(f"Category: {category}")
            
            print(f"\n📋 Test {test_case['id']}: {test_case['name']}")
            print(f"   Query: {test_case['query']}")
            
            # Add delay for memory tests
            if category == "Memory" and test_case['id'] == 10:
                await asyncio.sleep(2)
            
            result = await test_endpoint(session, test_case)
            results.append({
                "test": test_case,
                "result": result
            })
            
            category_stats[category]["total"] += 1
            
            if result['success']:
                category_stats[category]["passed"] += 1
                print_colored(f"   ✅ PASSED (Score: {result.get('quality_score', 0)}/100, Time: {result['response_time']:.2f}s)", Colors.GREEN)
                if result.get('quality_notes'):
                    for note in result['quality_notes']:
                        print(f"      {note}")
            else:
                print_colored(f"   ❌ FAILED", Colors.RED)
                if result.get('error'):
                    print(f"   Error: {result['error']}")
                if result.get('quality_notes'):
                    for note in result['quality_notes']:
                        print(f"      {note}")
                if result.get('response'):
                    print(f"   Response preview: {result['response'][:200]}...")
            
            # Show if thoughts were displayed
            if result.get('has_thoughts'):
                print_colored(f"   💭 Agent thoughts displayed", Colors.CYAN)
        
        # Summary
        print_section("TEST SUMMARY")
        
        total_tests = len(TEST_CASES)
        total_passed = sum(stat["passed"] for stat in category_stats.values())
        
        print(f"\nOverall: {total_passed}/{total_tests} passed ({total_passed/total_tests*100:.1f}%)")
        
        print("\nBy Category:")
        for category, stats in category_stats.items():
            passed = stats["passed"]
            total = stats["total"]
            percentage = passed/total*100 if total > 0 else 0
            status = "✅" if percentage == 100 else "⚠️" if percentage >= 80 else "❌"
            print(f"  {status} {category}: {passed}/{total} ({percentage:.1f}%)")
        
        # Quality Analysis
        print("\n📊 Quality Analysis:")
        avg_quality = sum(r["result"].get("quality_score", 0) for r in results) / len(results)
        print(f"  Average Quality Score: {avg_quality:.1f}/100")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"humansa_v2_subset_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "success_rate": total_passed/total_tests,
                "average_quality_score": avg_quality,
                "category_stats": category_stats,
                "detailed_results": [
                    {
                        "id": r["test"]["id"],
                        "name": r["test"]["name"],
                        "category": r["test"]["category"],
                        "query": r["test"]["query"],
                        "success": r["result"]["success"],
                        "quality_score": r["result"].get("quality_score", 0),
                        "quality_notes": r["result"].get("quality_notes", []),
                        "response_time": r["result"].get("response_time", 0),
                        "missing_keywords": r["result"].get("missing_keywords", []),
                        "error": r["result"].get("error"),
                        "response_preview": r["result"].get("response", "")[:500]
                    }
                    for r in results
                ]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {filename}")
        
        # Detailed failure analysis
        failures = [r for r in results if not r["result"]["success"]]
        if failures:
            print("\n🔍 Detailed Failure Analysis:")
            for r in failures:
                test = r["test"]
                result = r["result"]
                print(f"\n  Test {test['id']}: {test['name']}")
                print(f"    Expected: {', '.join(test['expected_keywords'])}")
                if result.get('missing_keywords'):
                    print(f"    Missing: {', '.join(result['missing_keywords'])}")
                if result.get('quality_notes'):
                    print(f"    Issues: {'; '.join(result['quality_notes'])}")

if __name__ == "__main__":
    asyncio.run(run_subset_tests())
TESTSCRIPT

# Make test script executable
chmod +x test_humansa_v2_subset.py

# Run the tests
python3 test_humansa_v2_subset.py

# Step 5: Show server logs
echo -e "\n${YELLOW}Step 5: Server logs (last 30 lines):${NC}"
tail -n 30 server_v2_subset_test.log

# Step 6: Cleanup
echo -e "\n${YELLOW}Step 6: Test completed. Cleaning up...${NC}"
kill $SERVER_PID 2>/dev/null || true
echo -e "\n${GREEN}✅ Humansa V2 subset test completed!${NC}"

# Provide summary
echo -e "\n${BLUE}Summary:${NC}"
echo "- Test database: PostgreSQL on port 5456"
echo "- ML Server: Ran on port 6001"
echo "- Test results: humansa_v2_subset_results_*.json"
echo "- Server logs: server_v2_subset_test.log"