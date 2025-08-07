# Test Priority Explanation

## Priority Levels

The Test Management Dashboard uses a priority ranking system (1-5) to help organize and execute tests:

### Priority Scale
- **5 (Highest)**: Critical tests that must pass
  - Core functionality tests
  - Security-related tests
  - Data integrity tests
  - Tests that block other features

- **4 (High)**: Important tests for major features
  - Primary user workflows
  - Integration tests
  - Performance-critical paths

- **3 (Medium)**: Standard functionality tests
  - Regular feature tests
  - UI/UX tests
  - Non-critical workflows

- **2 (Low)**: Nice-to-have tests
  - Edge cases
  - Minor features
  - Cosmetic issues

- **1 (Lowest)**: Optional tests
  - Experimental features
  - Future functionality
  - Deprecated feature tests

## Usage in Dashboard

1. **Test Execution Order**: Higher priority tests can be run first
2. **Filtering**: Filter tests by priority level
3. **Batch Jobs**: Create jobs with only high-priority tests
4. **CI/CD Integration**: Run different priority levels in different stages

## Examples from Your Tests

- **Priority 5**: Identity queries, appointment booking core flow
- **Priority 4**: Multi-turn conversations, doctor search
- **Priority 3**: Standard appointment tests (APT_001-APT_100)
- **Priority 2**: Edge case handling (gibberish input, emoji-only)
- **Priority 1**: (Currently no tests at this level)