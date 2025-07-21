# Available Test Cases for YouWoAI Multi-Agent System

## 1. Clean Test Output (`test_clean_output.py`)

Run with: `source youwo-ml-venv/bin/activate && python test_clean_output.py`

### Test Cases:
1. **RAG Tests**
   - `RAG: Note Query` - "What information do I have about the PARL paper?"
   - `RAG: Conversation Query` - "What did we discuss about reinforcement learning?"

2. **Web Search Tests**
   - `Web Search: Current Events` - "What are the latest AI developments today?"

3. **Code Interpreter Tests**
   - `Code: Simple Calculation` - "Calculate the fibonacci sequence up to 10 terms"
   - `Code: Data Visualization` - "Create a bar chart showing note types: PDF=3, YouTube=4, Document=1, Audio=1"

4. **Attachment Tests**
   - `Attachment: PDF Analysis` - "Summarize this paper" + [https://arxiv.org/pdf/2505.18499.pdf]
   - `Attachment: Image Analysis` - "What's shown in this diagram?" + [https://arxiv.org/html/2407.09124v1/x1.png]

5. **Mixed Tests**
   - `Mixed: Note + Code` - "Analyze the metrics in my G1 paper note and create a visualization"
   - `Mixed: Note + Web` - "How do my startup notes compare to current AI startup trends?"

### Output Format:
- Shows query, agents triggered, status, response preview, and citations
- Provides summary statistics and agent usage breakdown

## 2. Iterative Test Runner (`tests/iterative/test_runner.py`)

Run with: `source youwo-ml-venv/bin/activate && python -m tests.iterative.test_runner`

### Test Suites:

#### Critical User-Facing Features (Priority 10)
1. **Streaming Citations**
   - Tests streaming response with citation formatting
   - Expects: router → web_search → response → citation
   - Validates: Citation markers [1], [2], etc.

2. **Attachment Priority**
   - Tests that attachments always take precedence
   - Query: "Analyze this document" + PDF attachment
   - Expects: router → attachment → rag → response → citation

3. **RAG with Citations**
   - Tests knowledge base search with citations
   - Query: "What do my notes say about PARL? Include citations."
   - Expects: router → rag → response → citation

#### Multi-Agent Integration (Priority 7)
1. **Multiple Attachments**
   - Tests handling multiple PDF files
   - Query: "Compare these papers" + 2 PDFs
   - Expects: router → attachment → response → citation

2. **Complex Query Iteration**
   - Tests iterative processing for comprehensive responses
   - Long query about reinforcement learning with 5 requirements
   - Expects: router → rag → web_search → response → citation

#### Edge Cases (Priority 5)
Generated dynamically by EdgeCaseGenerator:

1. **Empty Inputs**
   - Empty messages array
   - Empty user message
   - Empty attachments array

2. **Malformed Data**
   - Invalid message role
   - Missing message content
   - Invalid attachment URLs

3. **Boundary Values**
   - Very long message (10k characters)
   - Maximum attachments (10 files)
   - Maximum conversation history (100 messages)

4. **Injection Attacks**
   - Prompt injection attempts
   - Citation injection with fake markers

5. **Concurrent Scenarios**
   - 5 identical requests simultaneously
   - Different users concurrently

6. **Timeout Scenarios**
   - Web search timeout handling
   - Large attachment processing timeout

7. **Resource Exhaustion**
   - Large context memory test
   - Token limit exhaustion

8. **Partial Failures**
   - RAG fails but web search succeeds
   - Multiple attachments with some failures
   - Citation with missing sources

### Features:
- 3-attempt validation with gpt-4o-mini
- Git integration for version control
- Performance metrics tracking
- OpenAI Response API format validation
- Automatic edge case generation

## 3. Running Specific Test Categories

### Quick Agent Test
```python
# Test specific agent combination
import asyncio
from tests.iterative.test_runner import IterativeTestRunner

async def test_specific():
    async with IterativeTestRunner() as runner:
        test_case = {
            'name': 'Your Test Name',
            'endpoint': '/v1/multi-agent/response',
            'stream': True,  # or False
            'request': {
                'messages': [{'role': 'user', 'content': 'Your query here'}],
                'attachments': []  # Optional
            },
            'expected': {
                'expected_agents': ['router', 'web_search', 'response'],
                'content_checks': [
                    {'type': 'contains', 'value': 'expected text'},
                    {'type': 'citations', 'value': None}
                ]
            }
        }
        result = await runner.validate_with_retries(test_case, test_case['expected'])
        print(f"Result: {'PASS' if result.success else 'FAIL'}")

asyncio.run(test_specific())
```

## 4. Test Database Setup

Before running tests:
```bash
# Start Docker with test database
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
docker-compose -f docker-compose.test.yml up -d

# Verify test database is running on port 5454
docker ps | grep postgres

# Run migrations on test database
pnpm run migrate:test
```

## 5. Key Test Validations

### Agent Detection
- Tracks which agents were triggered
- Validates expected agent combinations
- Ensures attachment priority routing

### Citation Validation
- Checks for [1], [2] style markers
- Validates source/reference sections
- Ensures proper citation formatting

### Streaming Validation
- OpenAI Response API format compliance
- Event pair tracking (start/done)
- Proper event ordering

### Performance Metrics
- Workflow completion time
- Token usage
- Number of iterations
- Success rate per attempt

## 6. Common Test Commands

```bash
# Run all tests with clean output
python test_clean_output.py

# Run iterative test suite
python -m tests.iterative.test_runner

# Run specific test file
python -m pytest tests/specific_test.py -v

# Run with coverage
python -m pytest --cov=src tests/

# Run only edge cases
python -c "from tests.iterative.generators.edge_case_generator import EdgeCaseGenerator; import asyncio; gen = EdgeCaseGenerator(); cases = asyncio.run(gen.generate_edge_cases()); print(f'Generated {len(cases)} edge cases')"
```

## 7. Expected Agent Combinations

### Common Patterns:
- **Simple Query**: router → response
- **Web Search**: router → web_search → response → citation
- **RAG Query**: router → rag → response → citation
- **Attachment**: router → attachment → rag → response → citation
- **Complex**: router → rag → web_search → response → citation
- **Code**: router → code_interpreter → response

### With Iterative Processing:
- Multiple passes through agents
- Quality evaluation between iterations
- Refinement based on feedback