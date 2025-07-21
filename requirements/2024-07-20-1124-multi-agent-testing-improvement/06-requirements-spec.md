# Multi-Agent Testing and Improvement System Requirements Specification

## Problem Statement
The current multi-agent system lacks comprehensive testing coverage, particularly for edge cases, streaming format compliance, and iterative improvements. The system needs an automated testing framework that continuously validates and improves all agents while ensuring OpenAI API compatibility.

## Solution Overview
Build an intelligent, iterative testing system that:
- Automatically runs continuous tests with self-healing capabilities
- Validates OpenAI streaming format compliance
- Tests all agents with real LLM calls (3-attempt validation)
- Generates edge cases automatically
- Tracks performance metrics and improvements
- Uses git for version control and rollback

## Functional Requirements

### FR1: Continuous Automated Testing Loop
- **Description**: System runs tests continuously, detecting and fixing issues automatically
- **Implementation**: 
  - Create `IterativeTestRunner` class that loops through test suites
  - Auto-detect failures and attempt fixes
  - Git commit after each successful fix
  - Rollback on test regression

### FR2: Performance Metrics and Benchmarking
- **Description**: Track detailed performance metrics for each agent
- **Implementation**:
  - Measure response times, token usage, accuracy
  - Store metrics in JSON format with timestamps
  - Generate trend reports showing improvements/regressions
  - No visual dashboards - CLI/JSON output only

### FR3: User-Facing Feature Priority
- **Description**: Prioritize testing of streaming responses and citations
- **Implementation**:
  - Test streaming format compliance first
  - Validate citation formatting and accuracy
  - Ensure proper event lifecycle
  - Test user-visible features before internals

### FR4: Git-Based Version Control
- **Description**: Use git commits for test history and rollback
- **Implementation**:
  - Commit after each test improvement
  - Tag successful test runs
  - Auto-rollback on test failures
  - Maintain test result history in git

### FR5: LLM-Based Testing with Fallback
- **Description**: Use real LLM calls with 3-attempt validation
- **Implementation**:
  - Use gpt-4o-mini for all test validations
  - Retry failed tests 3 times before marking as failure
  - Fall back to deterministic tests only after 3 failures
  - Track LLM response variations

## Technical Requirements

### TR1: Isolated Test Instances
- **Requirement**: Create isolated IterativeOrchestrator instances per test
- **Files to Modify**: 
  - `src/chat/endpoints/multi_agent_endpoint_v2.py`
  - Create factory pattern for orchestrator instances
- **Rationale**: Prevents state pollution between concurrent tests

### TR2: OpenAI Streaming Format Validation
- **Requirement**: Validate complete event lifecycle compliance
- **Implementation**:
  - Create `StreamingValidator` class
  - Track all event pairs (start/done)
  - Validate against OpenAI Response API spec
  - Test event ordering and completeness
- **Reference**: Research OpenAI documentation for exact format

### TR3: Timeout Testing Infrastructure
- **Requirement**: Test timeout behavior for each agent
- **Implementation**:
  - Configurable timeouts per agent type
  - Test graceful degradation
  - Validate error event generation
  - Test resource cleanup on timeout

### TR4: Automatic Edge Case Generation
- **Requirement**: Generate test cases from code analysis
- **Implementation**:
  - Static analysis of agent code
  - Generate tests for:
    - Empty inputs/outputs
    - Malformed data
    - Partial failures
    - Concurrent requests
    - Resource exhaustion

### TR5: Test Organization Structure
```
tests/
├── iterative/
│   ├── test_runner.py          # Main iterative test loop
│   ├── validators/
│   │   ├── streaming_validator.py
│   │   ├── citation_validator.py
│   │   └── agent_validator.py
│   ├── generators/
│   │   ├── edge_case_generator.py
│   │   └── test_scenario_builder.py
│   └── metrics/
│       ├── performance_tracker.py
│       └── improvement_analyzer.py
├── scenarios/
│   ├── critical/               # User-facing features
│   ├── edge_cases/            # Generated edge cases
│   └── integration/           # Multi-agent workflows
└── fixtures/
    └── test_data/
```

## Implementation Patterns

### Pattern 1: Three-Attempt Validation
```python
async def validate_agent_behavior(agent, test_case, expected_behavior):
    for attempt in range(3):
        result = await agent.run(test_case)
        if matches_expected(result, expected_behavior):
            return True
    # After 3 failures, flag for investigation
    return False
```

### Pattern 2: Streaming Event Validation
```python
class StreamingValidator:
    def __init__(self):
        self.event_pairs = {}
        
    def track_event(self, event):
        if event.type.endswith('.added'):
            self.event_pairs[event.id] = {'start': event}
        elif event.type.endswith('.done'):
            if event.id in self.event_pairs:
                self.event_pairs[event.id]['end'] = event
```

### Pattern 3: Automatic Fix Application
```python
class AutoFixer:
    async def apply_fix(self, test_failure):
        # Analyze failure
        root_cause = await self.analyze_failure(test_failure)
        
        # Generate fix
        fix_code = await self.generate_fix(root_cause)
        
        # Apply and test
        self.apply_code_change(fix_code)
        
        # Validate fix
        if await self.validate_fix(test_failure):
            self.git_commit(f"Fix: {test_failure.description}")
        else:
            self.git_rollback()
```

## Acceptance Criteria

### AC1: Streaming Compliance
- [ ] All streaming events follow OpenAI Response API format
- [ ] Every start event has corresponding completion event
- [ ] Event ordering is consistent and correct
- [ ] No malformed events in any scenario

### AC2: Agent Coverage
- [ ] All 7 agents have comprehensive test suites
- [ ] Each agent tested with normal, edge, and error cases
- [ ] Timeout behavior validated for each agent
- [ ] Concurrent request handling tested

### AC3: Citation Accuracy
- [ ] Citations match source content
- [ ] Citation numbering is sequential and correct
- [ ] Sources section properly formatted
- [ ] Multi-language citations handled correctly

### AC4: Iterative Improvement
- [ ] System runs continuously without manual intervention
- [ ] Automatically detects and fixes common issues
- [ ] Performance improves over iterations
- [ ] Git history shows improvement trajectory

### AC5: Test Reliability
- [ ] 3-attempt validation reduces false positives
- [ ] Edge cases automatically discovered and tested
- [ ] Test isolation prevents cross-contamination
- [ ] Metrics accurately track system health

## Success Metrics
- 100% streaming format compliance
- <1% false positive rate in tests
- All agents achieve >95% success rate
- Automatic fix success rate >80%
- Test execution time <5 minutes for full suite

## Next Steps
1. Implement StreamingValidator with OpenAI format compliance
2. Create IterativeTestRunner with git integration
3. Build edge case generator from code analysis
4. Set up performance metrics tracking
5. Implement 3-attempt validation pattern
6. Create continuous improvement loop