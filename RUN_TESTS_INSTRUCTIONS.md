# How to Run the Comprehensive Test Suite

## Quick Start

Run this single command from anywhere:

```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server && source youwo-ml-venv/bin/activate && python test_comprehensive_with_logs.py
```

## What the Test Suite Does

1. **Runs 11 comprehensive test cases** including:
   - Simple RAG queries (notes, conversations, mixed)
   - Multi-agent workflows (RAG + Web, RAG + Code, etc.)
   - Complex queries requiring multiple agents
   - Citation-heavy tests
   - Edge cases

2. **Captures detailed logs** for each test:
   - Creates timestamped directory: `test_results_YYYYMMDD_HHMMSS/`
   - Saves ML server logs for each individual test
   - Saves all streaming events
   - Generates summary report

3. **Shows real-time progress**:
   - Live status updates as tests run
   - Agent execution sequence
   - Response length and citation count
   - Duration for each test

## Output Structure

After running, you'll find:

```
test_results_20240719_180000/
├── SUMMARY_REPORT.md           # Overall test summary
├── test_run.log               # Complete test execution log
├── RAG_Notes_Simple_result.json      # Individual test result
├── RAG_Notes_Simple_ml_server.log    # ML server logs for this test
├── RAG_Conversations_result.json
├── RAG_Conversations_ml_server.log
└── ... (files for each test)
```

## Understanding the Results

### Summary Report Shows:
- Success rate
- Agent usage statistics
- Multi-agent workflow analysis
- Citation analysis
- Failed test details
- Individual test breakdowns

### For Each Test:
- Query and expected agents
- Actual agents triggered (with sequence)
- Response preview
- Citations generated
- Full ML server logs

## Example Output

```
[1/11] Running: RAG Notes Simple
Status: ✅ success
Agents: router(1) → rag(5) → response(12) → citation(18)
Response length: 523 chars
Citations: 3
Duration: 2.34s
```

## Troubleshooting

If tests fail, check:
1. ML server is running: `lsof -i:5001`
2. Test database is running: `docker ps | grep youwoai_test_db`
3. Check individual test logs in the results directory

## Key Findings from Testing

1. **Citation Agent Issue**: Currently not implemented (has TODO)
2. **Attachment Agent**: Not triggering, router sends to code_interpreter
3. **RAG Agent**: Works for conversations but fails for some note queries
4. **Multi-Agent Workflows**: Limited - agents don't iteratively call each other

The comprehensive test suite will help debug these issues by providing detailed logs for each failure.