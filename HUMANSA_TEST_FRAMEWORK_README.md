# HUMANSA Comprehensive Test Framework

A modular, scalable test framework designed to handle 1000+ test cases for the Humansa medical AI system with parallel execution, standardized structure, and comprehensive reporting.

## Overview

This framework provides:
- **Modular Test Case Structure**: Standardized test case format with expectations, metadata, and validation
- **Parallel Execution**: Run tests concurrently for faster execution
- **Comprehensive Test Coverage**: 1000+ test cases across multiple categories
- **Real-time Monitoring**: Live dashboard to track test execution
- **Detailed Reporting**: JSON and human-readable reports with analytics
- **Automatic Test Generation**: Programmatic generation of diverse test scenarios

## Architecture

```
┌─────────────────────┐
│   Test Case Manager │ ← Stores and retrieves test cases
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Test Case Generator│ ← Generates 1000+ test cases
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   Test Executor     │ ← Executes tests against API
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Parallel Test Runner│ ← Runs tests in parallel batches
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   Test Reporter     │ ← Generates reports and analytics
└─────────────────────┘
```

## Test Case Structure

Each test case includes:
- **ID**: Unique identifier
- **Name**: Descriptive name
- **Category**: Test category (medical, appointment, product, etc.)
- **Query**: User input to test
- **Expectations**: 
  - Expected keywords in response
  - Expected agents to be triggered
  - Response time limits
  - Response length constraints
  - Thinking flow keywords
  - Required tools
  - Forbidden patterns
- **User Context**: User information and session data
- **Previous Turns**: For multi-turn conversations
- **Metadata**: Additional test information
- **Priority**: 1-5 scale for test importance
- **Tags**: For filtering and organization

## Test Categories

1. **Medical Consultation** (30%)
   - Symptom inquiries
   - Medical history considerations
   - Treatment recommendations

2. **Appointment** (25%)
   - Doctor booking
   - Time slot queries
   - Specialty requests

3. **Product Recommendation** (15%)
   - Medicine queries
   - Health product searches
   - Dosage questions

4. **Multi-turn Conversations** (15%)
   - Context retention
   - Follow-up questions
   - Conversation flow

5. **Edge Cases** (10%)
   - Invalid inputs
   - Boundary conditions
   - Error handling

6. **Stress Tests** (5%)
   - Complex queries
   - Performance under load
   - Resource usage

## Usage

### Quick Test (20 test cases)
```bash
python run_humansa_comprehensive_tests.py --mode quick
```

### Category-specific Test
```bash
python run_humansa_comprehensive_tests.py --mode category --category medical_consultation --count 100
```

### Full Test Suite (1000 test cases)
```bash
python run_humansa_comprehensive_tests.py --mode full --count 1000
```

### Stress Test (Parallel users)
```bash
python run_humansa_comprehensive_tests.py --mode stress --concurrent-users 20 --requests-per-user 50
```

### Real-time Monitoring
```bash
# In one terminal - run tests
python run_humansa_comprehensive_tests.py --mode full

# In another terminal - monitor progress
python humansa_test_monitor.py demo
```

### Analyze Test Results
```bash
python humansa_test_monitor.py
```

## Test Execution Flow

1. **Test Case Loading/Generation**
   - Load existing test cases from disk
   - Generate new test cases if needed
   - Organize by category and priority

2. **Parallel Execution**
   - Split test cases into batches
   - Execute batches concurrently
   - Handle API rate limiting

3. **Result Validation**
   - Check response against expectations
   - Validate agent usage
   - Measure performance metrics

4. **Report Generation**
   - Summary statistics
   - Detailed results
   - Performance analytics
   - Actionable recommendations

## Output Structure

```
test_cases/
├── medical_consultation/
│   ├── med_consult_1.yaml
│   └── ...
├── appointment/
│   ├── appointment_1.yaml
│   └── ...
└── ...

test_reports/
├── full_test_summary.json
├── full_test_detailed.json
├── full_test_analytics.json
└── full_test_summary.txt
```

## Report Contents

### Summary Report
- Overall statistics (pass/fail rates)
- Category breakdown
- Agent usage statistics
- Performance metrics

### Detailed Report
- Individual test results
- Validation outcomes
- Response content
- Error messages

### Analytics Report
- Slowest tests
- Most complex tests
- Common failure patterns
- Performance by category

## Key Features

### 1. Modular Design
- Easy to add new test categories
- Extensible validation logic
- Pluggable report generators

### 2. Scalability
- Handles 1000+ test cases efficiently
- Parallel execution support
- Batch processing for API limits

### 3. Comprehensive Validation
- Multiple validation criteria
- Flexible expectation matching
- Detailed failure reporting

### 4. Real-time Monitoring
- Live test execution tracking
- Progress visualization
- Performance metrics

### 5. Actionable Insights
- Automated issue detection
- Performance bottleneck identification
- Improvement recommendations

## Example Test Case

```yaml
id: med_consult_42
name: Medical Consultation - 头痛
category: medical_consultation
query: 我最近头痛，我有高血压病史，请问需要看医生吗？
expectations:
  keywords:
    - 头痛
    - 医生
    - 建议
    - 高血压
  agents_touched:
    - medical_agent
  thinking_flow_keywords:
    - 分析症状
    - 评估严重程度
    - 考虑病史
  min_response_length: 100
  response_time_max: 30.0
priority: 3
tags:
  - symptom
  - consultation
  - chronic_condition
```

## Integration with CI/CD

The framework can be integrated into CI/CD pipelines:

```bash
# Run quick tests on every commit
python run_humansa_comprehensive_tests.py --mode quick --count 50

# Run full tests nightly
python run_humansa_comprehensive_tests.py --mode full

# Check test results
if [ $? -ne 0 ]; then
    echo "Tests failed"
    exit 1
fi
```

## Performance Considerations

- **Batch Size**: Adjust based on API rate limits
- **Parallel Workers**: Set based on server capacity
- **Test Distribution**: Balance across categories
- **Response Caching**: Avoid duplicate API calls

## Future Enhancements

1. **Machine Learning Integration**
   - Automatic test case generation from logs
   - Failure prediction
   - Performance optimization

2. **Advanced Analytics**
   - Trend analysis over time
   - Regression detection
   - A/B testing support

3. **Enhanced Monitoring**
   - Web-based dashboard
   - Alert notifications
   - Historical comparisons

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Ensure ML server is running on port 6001
   - Check database connectivity

2. **Slow Test Execution**
   - Reduce batch size
   - Increase parallel workers
   - Check server performance

3. **High Failure Rate**
   - Review test expectations
   - Check API changes
   - Verify test data

## Contributing

To add new test cases:
1. Define test case structure in appropriate category
2. Update generator methods
3. Add validation logic
4. Test with small batch first

## License

Internal use only - YouWoAI