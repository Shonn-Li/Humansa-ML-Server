# Modular Test Framework Quick Reference

## 🚀 Quick Start

### 1. Create a Test Case
```python
from humansa_test_framework import TestCase, TestCategory, TestExpectation

test = TestCase(
    id="apt_001",
    name="Book appointment with Dr. Li",
    category=TestCategory.APPOINTMENT,
    query="我想预约李明医生明天上午9点看头痛",
    expectations=TestExpectation(
        keywords=["李明医生", "明天", "上午9点"],
        agents_touched=["FormCreator"],
        required_tools=["create_appointment_form"]
    )
)
```

### 2. Run Tests
```python
from humansa_test_framework import TestCaseManager, ParallelTestRunner

# Add tests
manager = TestCaseManager()
manager.add_test_case(test)

# Run in parallel
runner = ParallelTestRunner(max_workers=4)
results = await runner.run_tests(manager.get_all_tests())
```

### 3. Generate Reports
```python
from humansa_test_framework import TestReporter

reporter = TestReporter()
report = reporter.generate_report(results)
reporter.save_html_report(report, "test_results.html")
```

---

## 📋 Test Case Structure

### Required Fields
- `id`: Unique identifier (e.g., "apt_001")
- `name`: Human-readable name
- `category`: TestCategory enum value
- `query`: Input query to test
- `expectations`: TestExpectation object

### Optional Fields
- `user_context`: Dict with user data
- `previous_turns`: List of conversation turns
- `metadata`: Additional test metadata
- `priority`: 1-5 (default: 1)
- `tags`: List of tags for filtering

---

## 🎯 Test Expectations

### Available Validations
```python
TestExpectation(
    # Content validation
    keywords=["必须包含", "这些词"],
    forbidden_patterns=["不能包含", "这些词"],
    
    # Response validation
    min_response_length=50,
    max_response_length=500,
    response_time_max=5.0,  # seconds
    
    # Agent/tool validation
    agents_touched=["FormCreator", "DoctorSearch"],
    required_tools=["create_appointment_form"],
    
    # Reasoning validation
    thinking_flow_keywords=["analyzing", "searching"],
    
    # Emergency detection
    emergency_flags=["chest_pain", "urgent"]
)
```

---

## 🔄 Multi-Turn Conversations

```python
test = TestCase(
    id="multi_001",
    name="Progressive form filling",
    category=TestCategory.MULTI_TURN,
    query="我叫张三，电话13800138000",
    previous_turns=[
        {"role": "user", "content": "我想预约看头痛"},
        {"role": "assistant", "content": "请问您想预约哪位医生？"},
        {"role": "user", "content": "李明医生"},
        {"role": "assistant", "content": "好的，请提供您的姓名和联系方式"}
    ],
    expectations=TestExpectation(
        keywords=["张三", "13800138000"]
    )
)
```

---

## 📊 Test Categories

| Category | Use Case | Example |
|----------|----------|---------|
| `IDENTITY` | Brand identity | "你是谁？" |
| `MEDICAL_CONSULTATION` | Medical Q&A | "头痛怎么办？" |
| `APPOINTMENT` | Booking | "预约李医生" |
| `PRODUCT_RECOMMENDATION` | Products | "推荐保健品" |
| `EMERGENCY` | Urgent cases | "胸口剧痛" |
| `MULTI_TURN` | Conversations | Multi-step flows |
| `EDGE_CASE` | Error handling | Invalid inputs |
| `PERFORMANCE` | Speed tests | Response time |

---

## 🛠️ Advanced Features

### 1. Batch Testing from YAML
```yaml
# test_cases.yaml
test_cases:
  - id: apt_001
    name: Simple appointment
    category: appointment
    query: "预约李医生明天"
    expectations:
      keywords: ["李医生", "明天"]
```

```python
manager = TestCaseManager()
manager.load_from_yaml("test_cases.yaml")
```

### 2. Custom Validators
```python
async def validate_form_id(response: Dict, test_case: TestCase) -> bool:
    return "form_id" in response.get("metadata", {})

# Add to test
test.metadata["custom_validators"] = [validate_form_id]
```

### 3. Test Filtering
```python
# Run only appointment tests
appointment_tests = manager.get_tests_by_category(TestCategory.APPOINTMENT)

# Run high priority tests
priority_tests = manager.filter_tests(lambda t: t.priority >= 4)

# Run tests with specific tags
tagged_tests = manager.get_tests_by_tags(["form", "multi-turn"])
```

---

## 📈 Performance Optimization

### Parallel Execution
```python
# Adjust workers based on CPU cores
import multiprocessing
runner = ParallelTestRunner(max_workers=multiprocessing.cpu_count())

# Set batch size for better distribution
results = await runner.run_tests(tests, batch_size=10)
```

### Memory Management
```python
# Run tests in chunks for large test suites
chunk_size = 100
for i in range(0, len(all_tests), chunk_size):
    chunk = all_tests[i:i + chunk_size]
    results = await runner.run_tests(chunk)
    reporter.append_results(results)
```

---

## 🔍 Debugging

### Enable Debug Logging
```python
import logging
logging.getLogger("humansa_test_framework").setLevel(logging.DEBUG)
```

### Test Result Analysis
```python
# Get failed tests
failed = [r for r in results if not r.passed]

# Analyze validation failures
for result in failed:
    print(f"Test: {result.test_case.name}")
    print(f"Validations: {result.validation_results}")
    print(f"Error: {result.error}")
```

---

## 📝 Best Practices

1. **Unique IDs**: Use format `CATEGORY_###` (e.g., `APT_001`)
2. **Clear Names**: Be descriptive (e.g., "Book appointment with specific time")
3. **Comprehensive Expectations**: Test multiple aspects in one case
4. **Tag Appropriately**: Use tags for easy filtering
5. **Set Priorities**: Mark critical tests with priority 4-5
6. **Document Metadata**: Explain complex test logic in metadata

---

## 🚦 Running Tests

### Command Line
```bash
# Run all tests
python run_humansa_comprehensive_tests.py

# Run specific category
python run_humansa_comprehensive_tests.py --category appointment

# Run with monitoring
python run_humansa_comprehensive_tests.py --monitor

# Run specific test file
python test_appointment_forms_modular.py
```

### Programmatic
```python
# Simple run
results = await runner.run_tests(tests)

# With progress callback
async def progress_callback(completed, total):
    print(f"Progress: {completed}/{total}")

results = await runner.run_tests(tests, progress_callback=progress_callback)
```

---

## 📊 Reporting

### Available Formats
- **JSON**: Detailed results with all metadata
- **CSV**: Tabular format for analysis
- **HTML**: Interactive report with charts
- **Console**: Real-time progress output

### Custom Reports
```python
# Generate multiple formats
reporter.save_json_report(results, "results.json")
reporter.save_csv_report(results, "results.csv")
reporter.save_html_report(results, "results.html")

# Get summary statistics
summary = reporter.get_summary_stats(results)
print(f"Pass rate: {summary['pass_rate']:.1%}")
print(f"Avg response time: {summary['avg_response_time']:.2f}s")
```