# Complete Test Cases Overview

## Test Suite Organization

### 1. Clean Output Tests (`test_clean_output.py`)
Simple, human-readable test output showing query → agents → response

| Test Name | Query | Attachments | Expected Agents |
|-----------|-------|-------------|-----------------|
| RAG: Note Query | "What information do I have about the PARL paper?" | None | router → rag → response |
| RAG: Conversation Query | "What did we discuss about reinforcement learning?" | None | router → rag → response |
| Web Search: Current Events | "What are the latest AI developments today?" | None | router → web_search → response |
| Code: Simple Calculation | "Calculate the fibonacci sequence up to 10 terms" | None | router → code_interpreter → response |
| Code: Data Visualization | "Create a bar chart showing note types..." | None | router → code_interpreter → response |
| Attachment: PDF Analysis | "Summarize this paper" | arxiv.org/pdf/2505.18499.pdf | router → attachment → rag → response → citation |
| Attachment: Image Analysis | "What's shown in this diagram?" | arxiv.org/.../x1.png | router → attachment → response |
| Mixed: Note + Code | "Analyze metrics in G1 paper and visualize" | None | router → rag → code_interpreter → response |
| Mixed: Note + Web | "Compare startup notes to current trends" | None | router → rag → web_search → response |

### 2. Detailed Logging Tests (`test_with_detailed_logging.py`)
Comprehensive tests with structured JSON/text logs per test case

#### Basic Tests
| Test Name | Stream | Purpose |
|-----------|--------|---------|
| Simple Query | Yes/No | Baseline test for simple responses |
| Simple Query Non-Stream | No | Compare streaming vs non-streaming |

#### RAG Tests
| Test Name | Stream | Expected Behavior |
|-----------|--------|-------------------|
| RAG: Note Query Stream | Yes | Should trigger RAG agent |
| RAG: Note Query Non-Stream | No | Compare streaming behavior |
| RAG with Citations | Yes | Must include [1], [2] citations |

#### Web Search Tests
| Test Name | Stream | Expected Behavior |
|-----------|--------|-------------------|
| Web Search Stream | Yes | Should search internet |
| Web Search Non-Stream | No | Compare formats |
| Web Search with Citations | Yes | Must cite sources |

#### Attachment Tests (Critical)
| Test Name | Stream | Attachments | Expected Behavior |
|-----------|--------|-------------|-------------------|
| Single PDF Stream | Yes | 1 PDF | attachment → rag → response → citation |
| Single PDF Non-Stream | No | 1 PDF | Compare streaming |
| Multiple Attachments | Yes | 2 PDFs | Process both files |
| Image Attachment | Yes | 1 PNG | Image analysis |

#### Mixed Agent Tests
| Test Name | Purpose |
|-----------|---------|
| RAG + Web Search | Combine knowledge base with internet |
| Attachment + Citation | Ensure citations for attached content |

#### Citation Tests
| Test Name | Stream | Expected |
|-----------|--------|----------|
| Force Citations Stream | Yes | Must have [1], [2] markers |
| Force Citations Non-Stream | No | Compare citation format |

### 3. Iterative Test Runner (`tests/iterative/test_runner.py`)
Automated testing with 3-attempt validation

#### Critical User-Facing (Priority 10)
1. **Streaming Citations** - Validates citation format in streaming
2. **Attachment Priority** - Ensures files take precedence
3. **RAG with Citations** - Knowledge base + citations

#### Multi-Agent Integration (Priority 7)
1. **Multiple Attachments** - 2+ files simultaneously
2. **Complex Query Iteration** - Multi-pass refinement

#### Edge Cases (Priority 5) - Auto-generated
- Empty inputs (empty messages, attachments)
- Malformed data (invalid roles, bad URLs)
- Boundary values (10k char messages, 100 message history)
- Injection attacks (prompt injection, fake citations)
- Concurrent scenarios (5 simultaneous requests)
- Timeout scenarios (slow attachments, web search)
- Resource exhaustion (memory, token limits)
- Partial failures (some agents fail)

### 4. Validation Tests

#### Attachment Validation (`validate_attachment_logging.py`)
Specifically validates attachment agent logging:
1. Non-streaming with attachment
2. Streaming with attachment  
3. No attachment (control test)

## Running Tests

### Quick Commands
```bash
# Basic clean output
python test_clean_output.py

# Detailed logging suite
python tests/test_with_detailed_logging.py

# Iterative test runner
python -m tests.iterative.test_runner

# Attachment validation only
python tests/validate_attachment_logging.py

# Single test example
python tests/quick_test_single.py
```

### Test Output Locations
```
test_logs/
└── YYYYMMDD_HHMMSS/
    ├── Test_Name.json              # Raw event data
    ├── Test_Name_readable.txt      # Human-readable format
    └── output_item_analysis.json   # Event type analysis
```

## Expected Agent Combinations

### Single Agent
- Simple queries: `router → response`

### Two Agents
- Web search: `router → web_search → response`
- RAG query: `router → rag → response`

### Three Agents with Citation
- Web + cite: `router → web_search → response → citation`
- RAG + cite: `router → rag → response → citation`

### Four+ Agents
- Attachment: `router → attachment → rag → response → citation`
- Complex: `router → rag → web_search → response → citation`
- Iterative: Multiple passes through agents with quality checks

## Success Criteria

### ✅ Test Passes If:
1. Expected agents are triggered
2. Citations present when requested ([1], [2] format)
3. Response generated successfully
4. No errors in processing
5. Attachments processed when provided

### ❌ Test Fails If:
1. Missing expected agents
2. No citations when requested
3. Empty response
4. Processing errors
5. Attachments ignored when provided

## Debugging Failed Tests

1. Check server is running: `curl http://localhost:5001/health`
2. Verify test database: `docker ps | grep postgres`
3. Check environment: `.env` has all API keys
4. View server logs: `tail -f ml_server.log`
5. Check specific test log: `cat test_logs/*/Test_Name_readable.txt`