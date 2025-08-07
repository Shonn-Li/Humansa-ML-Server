# Test File Cleanup Recommendations

## Active Test Files (KEEP)

These are the core test files that should be maintained:

1. **test_HUMANSA_v2_comprehensive_enhanced.py** - Core 30 tests for identity and memory
2. **test_HUMANSA_v2_70_cases_multiturn.py** - Comprehensive 70-test suite
3. **test_key_improvements.py** - Critical functionality verification
4. **test_response_agent_fix.py** - Response Agent validation
5. **test_tool_selection.py** - Tool selection logic verification

## Potentially Outdated (REVIEW/ARCHIVE)

These files were created during development and may be archived:

1. **test_quick_identity.py** - Quick identity check (functionality covered in comprehensive tests)
2. **test_response_agent_direct.py** - Direct response agent test (merged into test_response_agent_fix.py)
3. **test_final_summary.py** - Summary test (replaced by test_key_improvements.py)
4. **test_consolidated_tools.py** - Tool testing (covered by test_tool_selection.py)
5. **test_conversation_api.py** - API testing (may keep if actively used)
6. **test_responses_api.py** - Response API testing (may keep if actively used)
7. **test_long_conversation_suite.py** - Long conversation tests (covered in 70-case suite)
8. **test_response_forking_scenarios.py** - Forking scenarios (specialized, may archive)

## Documentation Files (CONSOLIDATE)

### Keep (Primary Documentation)
1. **HUMANSA_V2_COMPLETE_DOCUMENTATION.md** - Main technical documentation
2. **README_HUMANSA_V2_UNIFIED.md** - User-facing README
3. **TEST_ENVIRONMENT_GUIDE.md** - Testing guide
4. **HUMANSA_V2_FINAL_REPORT.md** - Implementation summary

### Archive (Historical/Redundant)
1. **HUMANSA_V2_FIX_SUMMARY.md** - Historical fix notes
2. **HUMANSA_V2_IMPROVEMENTS_SUMMARY.md** - Merged into final report
3. **RESPONSE_AGENT_IMPLEMENTATION_SUMMARY.md** - Merged into complete docs
4. **HUMANSA_V2_RESPONSE_API_FIX_REPORT.md** - Historical fix notes
5. **Multiple older MD files** - Various development notes

## Recommended Actions

```bash
# 1. Create archive directory
mkdir -p archive/test_files archive/docs

# 2. Move outdated test files
mv test_quick_identity.py archive/test_files/
mv test_response_agent_direct.py archive/test_files/
mv test_final_summary.py archive/test_files/
# ... etc

# 3. Move historical documentation
mv HUMANSA_*_FIX_*.md archive/docs/
mv HUMANSA_*_SUMMARY.md archive/docs/
# Keep only primary documentation

# 4. Update references
# Update any scripts or documentation that reference archived files
```

## Final Structure

```
├── tests/
│   ├── test_HUMANSA_v2_comprehensive_enhanced.py
│   ├── test_HUMANSA_v2_70_cases_multiturn.py
│   ├── test_key_improvements.py
│   ├── test_response_agent_fix.py
│   └── test_tool_selection.py
├── docs/
│   ├── HUMANSA_V2_COMPLETE_DOCUMENTATION.md
│   ├── README_HUMANSA_V2_UNIFIED.md
│   ├── TEST_ENVIRONMENT_GUIDE.md
│   └── HUMANSA_V2_FINAL_REPORT.md
└── archive/
    ├── test_files/
    └── docs/
```