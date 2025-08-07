"""
HUMANSA Comprehensive Test Framework
====================================

A modular, scalable test framework designed to handle 1000+ test cases
with parallel execution, standardized structure, and comprehensive reporting.
"""

import asyncio
import aiohttp
import json
import os
import time
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp
from pathlib import Path
import yaml
import pandas as pd
from collections import defaultdict
import hashlib

# Import test configuration
from test_environment.unified_test_config import (
    TEST_ML_SERVER, 
    setup_test_environment,
    TEST_USER_IDS
)

# Setup test environment
setup_test_environment()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestCategory(Enum):
    """Test case categories for organization"""
    IDENTITY = "identity"
    MEDICAL_CONSULTATION = "medical_consultation"
    APPOINTMENT = "appointment"
    PRODUCT_RECOMMENDATION = "product"
    EMERGENCY = "emergency"
    MULTI_TURN = "multi_turn"
    STRESS_TEST = "stress_test"
    EDGE_CASE = "edge_case"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"


class AgentType(Enum):
    """Agent types in Humansa system"""
    MAIN_ORCHESTRATOR = "main_orchestrator"
    MEDICAL_AGENT = "medical_agent"
    APPOINTMENT_AGENT = "appointment_agent"
    PRODUCT_AGENT = "product_agent"
    EMERGENCY_AGENT = "emergency_agent"
    MEMORY_AGENT = "memory_agent"


@dataclass
class TestExpectation:
    """Expected results for a test case"""
    keywords: List[str] = field(default_factory=list)
    agents_touched: List[str] = field(default_factory=list)
    emergency_flags: List[str] = field(default_factory=list)
    follow_up_actions: List[str] = field(default_factory=list)
    response_time_max: float = 30.0  # seconds
    min_response_length: int = 50
    max_response_length: int = 5000
    thinking_flow_keywords: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    """Modular test case structure"""
    id: str
    name: str
    category: TestCategory
    query: str
    expectations: TestExpectation
    user_context: Dict[str, Any] = field(default_factory=dict)
    previous_turns: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1-5, higher is more important
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = f"{self.category.value}_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['category'] = self.category.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create from dictionary"""
        data = data.copy()
        data['category'] = TestCategory(data['category'])
        data['expectations'] = TestExpectation(**data['expectations'])
        return cls(**data)


@dataclass
class TestResult:
    """Test execution result"""
    test_case_id: str
    success: bool
    response: str
    response_time: float
    agents_used: List[str]
    reasoning_chain: List[str]
    emergency_flags: List[str]
    follow_up_actions: List[str]
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def validate_expectations(self, expectations: TestExpectation) -> Tuple[bool, List[str]]:
        """Validate result against expectations"""
        failures = []
        
        # Check response time
        if self.response_time > expectations.response_time_max:
            failures.append(f"Response time {self.response_time:.2f}s exceeds max {expectations.response_time_max}s")
        
        # Check response length
        resp_len = len(self.response)
        if resp_len < expectations.min_response_length:
            failures.append(f"Response too short: {resp_len} < {expectations.min_response_length}")
        if resp_len > expectations.max_response_length:
            failures.append(f"Response too long: {resp_len} > {expectations.max_response_length}")
        
        # Check keywords
        response_lower = self.response.lower()
        missing_keywords = []
        for keyword in expectations.keywords:
            if keyword.lower() not in response_lower:
                missing_keywords.append(keyword)
        if missing_keywords:
            failures.append(f"Missing keywords: {missing_keywords}")
        
        # Check agents touched
        missing_agents = set(expectations.agents_touched) - set(self.agents_used)
        if missing_agents:
            failures.append(f"Missing expected agents: {missing_agents}")
        
        # Check forbidden patterns
        for pattern in expectations.forbidden_patterns:
            if pattern.lower() in response_lower:
                failures.append(f"Contains forbidden pattern: {pattern}")
        
        # Check thinking flow
        reasoning_text = ' '.join(self.reasoning_chain).lower()
        missing_thinking = []
        for keyword in expectations.thinking_flow_keywords:
            if keyword.lower() not in reasoning_text:
                missing_thinking.append(keyword)
        if missing_thinking:
            failures.append(f"Missing thinking keywords: {missing_thinking}")
        
        return len(failures) == 0, failures


class TestCaseManager:
    """Manages test case storage and retrieval"""
    
    def __init__(self, base_dir: str = "test_cases"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.test_cases: Dict[str, TestCase] = {}
        self.load_all_test_cases()
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case"""
        self.test_cases[test_case.id] = test_case
        self._save_test_case(test_case)
    
    def _save_test_case(self, test_case: TestCase) -> None:
        """Save test case to file"""
        category_dir = self.base_dir / test_case.category.value
        category_dir.mkdir(exist_ok=True)
        
        file_path = category_dir / f"{test_case.id}.yaml"
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_case.to_dict(), f, allow_unicode=True)
    
    def load_all_test_cases(self) -> None:
        """Load all test cases from disk"""
        for category_dir in self.base_dir.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.glob("*.yaml"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            test_case = TestCase.from_dict(data)
                            self.test_cases[test_case.id] = test_case
                    except Exception as e:
                        logger.error(f"Failed to load {file_path}: {e}")
    
    def get_test_cases(self, 
                      category: Optional[TestCategory] = None,
                      tags: Optional[List[str]] = None,
                      priority: Optional[int] = None) -> List[TestCase]:
        """Get filtered test cases"""
        cases = list(self.test_cases.values())
        
        if category:
            cases = [c for c in cases if c.category == category]
        
        if tags:
            tag_set = set(tags)
            cases = [c for c in cases if tag_set.intersection(set(c.tags))]
        
        if priority:
            cases = [c for c in cases if c.priority >= priority]
        
        return cases


class TestExecutor:
    """Executes test cases against Humansa API"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or TEST_ML_SERVER['base_url']
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_test_case(self, test_case: TestCase) -> TestResult:
        """Execute a single test case"""
        start_time = time.time()
        
        try:
            # Prepare request
            request_data = {
                "model": "gpt-4-turbo",
                "input": test_case.query,
                "user_id": test_case.user_context.get('user_id', TEST_USER_IDS['humansa_v2']),
                "metadata": {
                    "test_id": test_case.id,
                    "test_name": test_case.name,
                    "test_category": test_case.category.value,
                    "orchestrator": "pattern2"
                },
                "stream": True,
                "debug": True
            }
            
            # Add previous turns if multi-turn
            if test_case.previous_turns:
                # Execute previous turns first to build context
                for turn in test_case.previous_turns:
                    await self._execute_turn(turn['query'], request_data['user_id'])
            
            # Execute main query
            result = await self._execute_query(request_data)
            
            elapsed_time = time.time() - start_time
            
            return TestResult(
                test_case_id=test_case.id,
                success=True,
                response=result['response'],
                response_time=elapsed_time,
                agents_used=result.get('agents_used', []),
                reasoning_chain=result.get('reasoning_chain', []),
                emergency_flags=result.get('emergency_flags', []),
                follow_up_actions=result.get('follow_up_actions', []),
                metadata=result.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Test {test_case.id} failed: {e}")
            return TestResult(
                test_case_id=test_case.id,
                success=False,
                response="",
                response_time=time.time() - start_time,
                agents_used=[],
                reasoning_chain=[],
                emergency_flags=[],
                follow_up_actions=[],
                error=str(e)
            )
    
    async def _execute_turn(self, query: str, user_id: str) -> None:
        """Execute a conversation turn without returning result"""
        request_data = {
            "model": "gpt-4-turbo",
            "input": query,
            "user_id": user_id,
            "stream": False
        }
        await self._execute_query(request_data)
    
    async def _execute_query(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API query"""
        endpoint = "/v2/humansa/responses/stream" if request_data.get('stream') else "/v2/humansa/responses/create"
        
        async with self.session.post(f"{self.base_url}{endpoint}", json=request_data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"API error {resp.status}: {error_text}")
            
            if request_data.get('stream'):
                return await self._process_stream_response(resp)
            else:
                return await resp.json()
    
    async def _process_stream_response(self, response) -> Dict[str, Any]:
        """Process streaming response"""
        result = {
            'response': '',
            'agents_used': [],
            'reasoning_chain': [],
            'emergency_flags': [],
            'follow_up_actions': [],
            'metadata': {}
        }
        
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                data_str = line[6:]
                if data_str == '[DONE]':
                    break
                
                try:
                    event = json.loads(data_str)
                    
                    if event.get('type') == 'response.output_item.added':
                        item = event.get('item', {})
                        for content in item.get('content', []):
                            if content.get('type') == 'output_text':
                                result['response'] += content.get('text', '')
                    
                    elif event.get('type') == 'response.reasoning':
                        result['reasoning_chain'].extend(event.get('reasoning', []))
                    
                    elif event.get('type') == 'response.usage':
                        usage = event.get('usage', {})
                        result['agents_used'].extend(usage.get('agents_used', []))
                        result['emergency_flags'].extend(usage.get('emergency_flags', []))
                        result['follow_up_actions'].extend(usage.get('follow_up_actions', []))
                    
                except json.JSONDecodeError:
                    continue
        
        return result


class ParallelTestRunner:
    """Runs tests in parallel for scalability"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or mp.cpu_count()
        self.results: List[TestResult] = []
    
    async def run_tests(self, test_cases: List[TestCase], batch_size: int = 10) -> List[TestResult]:
        """Run tests in parallel batches"""
        results = []
        
        # Split into batches
        batches = [test_cases[i:i + batch_size] for i in range(0, len(test_cases), batch_size)]
        
        for i, batch in enumerate(batches):
            logger.info(f"Running batch {i+1}/{len(batches)} with {len(batch)} tests")
            
            # Run batch in parallel
            async with TestExecutor() as executor:
                batch_results = await asyncio.gather(
                    *[executor.execute_test_case(tc) for tc in batch],
                    return_exceptions=True
                )
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Test execution error: {result}")
                    else:
                        results.append(result)
            
            # Small delay between batches to avoid overwhelming the server
            if i < len(batches) - 1:
                await asyncio.sleep(1)
        
        return results


class TestReporter:
    """Generates test reports and analytics"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(self, 
                       test_cases: List[TestCase], 
                       results: List[TestResult],
                       report_name: str = None) -> str:
        """Generate comprehensive test report"""
        report_name = report_name or f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create result lookup
        result_map = {r.test_case_id: r for r in results}
        
        # Calculate statistics
        total_tests = len(test_cases)
        executed_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = executed_tests - passed_tests
        
        # Validate against expectations
        validation_results = []
        for test_case in test_cases:
            if test_case.id in result_map:
                result = result_map[test_case.id]
                passed, failures = result.validate_expectations(test_case.expectations)
                validation_results.append({
                    'test_id': test_case.id,
                    'test_name': test_case.name,
                    'category': test_case.category.value,
                    'execution_success': result.success,
                    'validation_success': passed,
                    'failures': failures,
                    'response_time': result.response_time,
                    'agents_used': result.agents_used
                })
        
        # Generate reports
        self._generate_summary_report(report_name, total_tests, executed_tests, 
                                    passed_tests, failed_tests, validation_results)
        self._generate_detailed_report(report_name, test_cases, results, validation_results)
        self._generate_analytics_report(report_name, test_cases, results, validation_results)
        
        return str(self.output_dir / f"{report_name}_summary.json")
    
    def _generate_summary_report(self, report_name: str, total: int, executed: int,
                               passed: int, failed: int, validations: List[Dict]) -> None:
        """Generate summary report"""
        validation_passed = sum(1 for v in validations if v['validation_success'])
        
        summary = {
            'report_name': report_name,
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_tests': total,
                'executed_tests': executed,
                'execution_passed': passed,
                'execution_failed': failed,
                'execution_success_rate': f"{(passed/executed*100):.2f}%" if executed > 0 else "0%",
                'validation_passed': validation_passed,
                'validation_failed': len(validations) - validation_passed,
                'validation_success_rate': f"{(validation_passed/len(validations)*100):.2f}%" if validations else "0%"
            },
            'by_category': self._calculate_category_stats(validations),
            'agent_usage': self._calculate_agent_stats(validations),
            'performance': self._calculate_performance_stats(validations)
        }
        
        # Save JSON
        with open(self.output_dir / f"{report_name}_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save human-readable summary
        with open(self.output_dir / f"{report_name}_summary.txt", 'w') as f:
            f.write(f"HUMANSA Test Report Summary\n")
            f.write(f"Generated: {summary['timestamp']}\n")
            f.write(f"{'='*60}\n\n")
            
            f.write(f"Overall Statistics:\n")
            f.write(f"  Total Tests: {total}\n")
            f.write(f"  Executed: {executed}\n")
            f.write(f"  Execution Success Rate: {summary['statistics']['execution_success_rate']}\n")
            f.write(f"  Validation Success Rate: {summary['statistics']['validation_success_rate']}\n\n")
            
            f.write(f"By Category:\n")
            for cat, stats in summary['by_category'].items():
                f.write(f"  {cat}: {stats['success_rate']} ({stats['passed']}/{stats['total']})\n")
    
    def _generate_detailed_report(self, report_name: str, test_cases: List[TestCase],
                                results: List[TestResult], validations: List[Dict]) -> None:
        """Generate detailed test results"""
        detailed_results = []
        result_map = {r.test_case_id: r for r in results}
        validation_map = {v['test_id']: v for v in validations}
        
        for test_case in test_cases:
            result = result_map.get(test_case.id)
            validation = validation_map.get(test_case.id)
            
            detailed_results.append({
                'test_case': test_case.to_dict(),
                'result': asdict(result) if result else None,
                'validation': validation
            })
        
        with open(self.output_dir / f"{report_name}_detailed.json", 'w') as f:
            json.dump(detailed_results, f, indent=2, default=str)
    
    def _generate_analytics_report(self, report_name: str, test_cases: List[TestCase],
                                 results: List[TestResult], validations: List[Dict]) -> None:
        """Generate analytics and insights"""
        # Create DataFrame for analysis
        df_data = []
        for v in validations:
            df_data.append({
                'test_id': v['test_id'],
                'category': v['category'],
                'success': v['validation_success'],
                'response_time': v['response_time'],
                'agent_count': len(v['agents_used']),
                'failure_count': len(v['failures'])
            })
        
        df = pd.DataFrame(df_data)
        
        # Generate insights
        insights = {
            'slowest_tests': df.nlargest(10, 'response_time')[['test_id', 'response_time']].to_dict('records'),
            'most_complex_tests': df.nlargest(10, 'agent_count')[['test_id', 'agent_count']].to_dict('records'),
            'category_performance': df.groupby('category').agg({
                'response_time': 'mean',
                'success': 'mean'
            }).to_dict('index'),
            'common_failures': self._analyze_common_failures(validations)
        }
        
        with open(self.output_dir / f"{report_name}_analytics.json", 'w') as f:
            json.dump(insights, f, indent=2)
    
    def _calculate_category_stats(self, validations: List[Dict]) -> Dict[str, Dict]:
        """Calculate statistics by category"""
        stats = defaultdict(lambda: {'total': 0, 'passed': 0})
        
        for v in validations:
            category = v['category']
            stats[category]['total'] += 1
            if v['validation_success']:
                stats[category]['passed'] += 1
        
        # Calculate success rates
        for cat in stats:
            total = stats[cat]['total']
            passed = stats[cat]['passed']
            stats[cat]['success_rate'] = f"{(passed/total*100):.2f}%" if total > 0 else "0%"
        
        return dict(stats)
    
    def _calculate_agent_stats(self, validations: List[Dict]) -> Dict[str, int]:
        """Calculate agent usage statistics"""
        agent_counts = defaultdict(int)
        
        for v in validations:
            for agent in v['agents_used']:
                agent_counts[agent] += 1
        
        return dict(agent_counts)
    
    def _calculate_performance_stats(self, validations: List[Dict]) -> Dict[str, float]:
        """Calculate performance statistics"""
        response_times = [v['response_time'] for v in validations]
        
        if not response_times:
            return {}
        
        return {
            'avg_response_time': sum(response_times) / len(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p50_response_time': sorted(response_times)[len(response_times)//2],
            'p95_response_time': sorted(response_times)[int(len(response_times)*0.95)]
        }
    
    def _analyze_common_failures(self, validations: List[Dict]) -> List[Dict]:
        """Analyze common failure patterns"""
        failure_counts = defaultdict(int)
        
        for v in validations:
            for failure in v.get('failures', []):
                # Extract failure type
                if 'Missing keywords:' in failure:
                    failure_counts['missing_keywords'] += 1
                elif 'Response time' in failure:
                    failure_counts['slow_response'] += 1
                elif 'Missing expected agents:' in failure:
                    failure_counts['missing_agents'] += 1
                elif 'too short:' in failure:
                    failure_counts['response_too_short'] += 1
                elif 'too long:' in failure:
                    failure_counts['response_too_long'] += 1
        
        return [{'type': k, 'count': v} for k, v in failure_counts.items()]


class TestCaseGenerator:
    """Generates test cases programmatically"""
    
    def __init__(self, manager: TestCaseManager):
        self.manager = manager
    
    def generate_medical_consultation_tests(self, count: int = 100) -> List[TestCase]:
        """Generate medical consultation test cases"""
        symptoms = [
            "头痛", "发烧", "咳嗽", "胸痛", "腹痛", "头晕", "恶心", 
            "疲劳", "关节痛", "皮疹", "呼吸困难", "心悸", "失眠"
        ]
        
        conditions = [
            "高血压", "糖尿病", "哮喘", "过敏", "偏头痛", "胃炎",
            "关节炎", "心脏病", "肾病", "肝病"
        ]
        
        test_cases = []
        
        for i in range(count):
            symptom = symptoms[i % len(symptoms)]
            condition = conditions[i % len(conditions)] if i % 3 == 0 else None
            
            query = f"我最近{symptom}"
            if condition:
                query += f"，我有{condition}病史"
            query += "，请问需要看医生吗？"
            
            test_case = TestCase(
                id=f"med_consult_{i+1}",
                name=f"Medical Consultation - {symptom}",
                category=TestCategory.MEDICAL_CONSULTATION,
                query=query,
                expectations=TestExpectation(
                    keywords=[symptom, "医生", "建议"],
                    agents_touched=["medical_agent"],
                    thinking_flow_keywords=["分析症状", "评估严重程度"],
                    min_response_length=100
                ),
                priority=2,
                tags=["symptom", "consultation"]
            )
            
            test_cases.append(test_case)
            self.manager.add_test_case(test_case)
        
        return test_cases
    
    def generate_appointment_tests(self, count: int = 100) -> List[TestCase]:
        """Generate appointment booking test cases"""
        specialties = [
            "内科", "外科", "儿科", "妇科", "眼科", "牙科",
            "皮肤科", "骨科", "心脏科", "神经科"
        ]
        
        times = [
            "明天上午", "这周五下午", "下周一", "最近的时间",
            "周末", "晚上6点后", "早上9点前"
        ]
        
        test_cases = []
        
        for i in range(count):
            specialty = specialties[i % len(specialties)]
            time_pref = times[i % len(times)]
            
            query = f"我想预约{specialty}医生，{time_pref}有空吗？"
            
            test_case = TestCase(
                id=f"appointment_{i+1}",
                name=f"Appointment Booking - {specialty}",
                category=TestCategory.APPOINTMENT,
                query=query,
                expectations=TestExpectation(
                    keywords=[specialty, "预约", "医生"],
                    agents_touched=["appointment_agent"],
                    required_tools=["get_available_doctors", "check_appointment_slots"],
                    thinking_flow_keywords=["查询医生", "检查时间"],
                    min_response_length=150
                ),
                priority=3,
                tags=["appointment", specialty]
            )
            
            test_cases.append(test_case)
            self.manager.add_test_case(test_case)
        
        return test_cases
    
    def generate_product_recommendation_tests(self, count: int = 50) -> List[TestCase]:
        """Generate product recommendation test cases"""
        products = [
            "维生素C", "钙片", "益生菌", "鱼油", "蛋白粉",
            "感冒药", "止痛药", "胃药", "眼药水", "创可贴"
        ]
        
        purposes = [
            "增强免疫力", "补充营养", "改善睡眠", "缓解疲劳",
            "促进消化", "保护关节", "美容养颜"
        ]
        
        test_cases = []
        
        for i in range(count):
            product = products[i % len(products)]
            purpose = purposes[i % len(purposes)]
            
            query = f"我想买{product}，主要是为了{purpose}，有什么推荐吗？"
            
            test_case = TestCase(
                id=f"product_{i+1}",
                name=f"Product Recommendation - {product}",
                category=TestCategory.PRODUCT_RECOMMENDATION,
                query=query,
                expectations=TestExpectation(
                    keywords=[product, "推荐", "产品"],
                    agents_touched=["product_agent"],
                    thinking_flow_keywords=["搜索产品", "分析需求"],
                    min_response_length=200
                ),
                priority=2,
                tags=["product", product]
            )
            
            test_cases.append(test_case)
            self.manager.add_test_case(test_case)
        
        return test_cases
    
    def generate_multi_turn_tests(self, count: int = 50) -> List[TestCase]:
        """Generate multi-turn conversation tests"""
        scenarios = [
            {
                "name": "症状咨询后预约",
                "turns": [
                    "我最近总是头痛，已经持续一周了",
                    "好的，那我想预约神经科医生检查一下"
                ]
            },
            {
                "name": "产品咨询后购买",
                "turns": [
                    "我想了解一下你们的维生素C产品",
                    "这个产品的价格是多少？有优惠吗？"
                ]
            },
            {
                "name": "复诊预约",
                "turns": [
                    "我上次看的是李医生，想再预约复诊",
                    "下周三下午可以吗？"
                ]
            }
        ]
        
        test_cases = []
        
        for i in range(count):
            scenario = scenarios[i % len(scenarios)]
            
            test_case = TestCase(
                id=f"multi_turn_{i+1}",
                name=f"Multi-turn - {scenario['name']}",
                category=TestCategory.MULTI_TURN,
                query=scenario['turns'][-1],
                expectations=TestExpectation(
                    keywords=["记得", "之前", "刚才"],
                    agents_touched=["memory_agent"],
                    thinking_flow_keywords=["获取历史", "上下文"],
                    min_response_length=100
                ),
                previous_turns=[{"query": turn} for turn in scenario['turns'][:-1]],
                priority=4,
                tags=["multi_turn", "context"]
            )
            
            test_cases.append(test_case)
            self.manager.add_test_case(test_case)
        
        return test_cases
    
    def generate_edge_cases(self, count: int = 50) -> List[TestCase]:
        """Generate edge case tests"""
        edge_cases = [
            {
                "query": "alksjdflkasjdf",
                "name": "Gibberish Input",
                "expectations": {
                    "keywords": ["不明白", "理解", "请"],
                    "max_response_length": 500
                }
            },
            {
                "query": "我要买1000000个维生素C",
                "name": "Unrealistic Quantity",
                "expectations": {
                    "keywords": ["数量", "确认", "批量"],
                    "thinking_flow_keywords": ["异常", "数量检查"]
                }
            },
            {
                "query": "我想预约100年后的医生",
                "name": "Invalid Time Request",
                "expectations": {
                    "keywords": ["时间", "无法", "合理"],
                    "forbidden_patterns": ["已预约", "成功"]
                }
            },
            {
                "query": "😀🎉🏥💊",
                "name": "Emoji Only Input",
                "expectations": {
                    "keywords": ["请", "文字", "描述"],
                    "max_response_length": 300
                }
            },
            {
                "query": "我" * 500,
                "name": "Repetitive Input",
                "expectations": {
                    "keywords": ["请", "问题", "清楚"],
                    "response_time_max": 10.0
                }
            }
        ]
        
        test_cases = []
        
        for i in range(count):
            edge = edge_cases[i % len(edge_cases)]
            
            test_case = TestCase(
                id=f"edge_{i+1}",
                name=f"Edge Case - {edge['name']}",
                category=TestCategory.EDGE_CASE,
                query=edge['query'],
                expectations=TestExpectation(**edge['expectations']),
                priority=1,
                tags=["edge_case", "robustness"]
            )
            
            test_cases.append(test_case)
            self.manager.add_test_case(test_case)
        
        return test_cases
    
    def generate_stress_tests(self, count: int = 50) -> List[TestCase]:
        """Generate stress test cases"""
        test_cases = []
        
        for i in range(count):
            # Generate increasingly complex queries
            complexity = (i % 5) + 1
            
            parts = []
            if complexity >= 1:
                parts.append("我想了解一下高血压的症状")
            if complexity >= 2:
                parts.append("顺便预约心脏科医生")
            if complexity >= 3:
                parts.append("还想买一些降压药")
            if complexity >= 4:
                parts.append("我的家族有心脏病史")
            if complexity >= 5:
                parts.append("请给我一个完整的治疗方案")
            
            query = "，".join(parts) + "。"
            
            test_case = TestCase(
                id=f"stress_{i+1}",
                name=f"Stress Test - Complexity {complexity}",
                category=TestCategory.STRESS_TEST,
                query=query,
                expectations=TestExpectation(
                    agents_touched=["medical_agent", "appointment_agent", "product_agent"][:complexity],
                    response_time_max=30.0 + (complexity * 5),
                    min_response_length=200 * complexity
                ),
                priority=1,
                tags=["stress", f"complexity_{complexity}"]
            )
            
            test_cases.append(test_case)
            self.manager.add_test_case(test_case)
        
        return test_cases
    
    def generate_all_test_cases(self, target_count: int = 1000) -> List[TestCase]:
        """Generate comprehensive test suite"""
        all_tests = []
        
        # Calculate distribution
        distributions = {
            'medical': int(target_count * 0.3),
            'appointment': int(target_count * 0.25),
            'product': int(target_count * 0.15),
            'multi_turn': int(target_count * 0.15),
            'edge_cases': int(target_count * 0.1),
            'stress': int(target_count * 0.05)
        }
        
        # Generate tests
        all_tests.extend(self.generate_medical_consultation_tests(distributions['medical']))
        all_tests.extend(self.generate_appointment_tests(distributions['appointment']))
        all_tests.extend(self.generate_product_recommendation_tests(distributions['product']))
        all_tests.extend(self.generate_multi_turn_tests(distributions['multi_turn']))
        all_tests.extend(self.generate_edge_cases(distributions['edge_cases']))
        all_tests.extend(self.generate_stress_tests(distributions['stress']))
        
        logger.info(f"Generated {len(all_tests)} test cases")
        return all_tests


async def main():
    """Main test execution function"""
    # Initialize components
    manager = TestCaseManager()
    generator = TestCaseGenerator(manager)
    runner = ParallelTestRunner()
    reporter = TestReporter()
    
    # Generate test cases if needed
    if len(manager.test_cases) < 1000:
        logger.info("Generating test cases...")
        generator.generate_all_test_cases(1000)
    
    # Get test cases to run
    test_cases = manager.get_test_cases()
    logger.info(f"Found {len(test_cases)} test cases")
    
    # Run tests
    logger.info("Starting test execution...")
    results = await runner.run_tests(test_cases, batch_size=20)
    
    # Generate report
    logger.info("Generating test report...")
    report_path = reporter.generate_report(test_cases, results)
    logger.info(f"Test report generated: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())