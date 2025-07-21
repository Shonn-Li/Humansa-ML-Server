# YouWoAI ML Server - Complete Feature Verification Tests

## Prerequisites

1. Make sure the ML server is running:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python src/main.py --port 5002
```

2. In a new terminal, navigate to the ML server directory:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
```

## Test Suite

### 1. Complete Citation System Verification
This test verifies that citations are actually used with real positions, URLs, and proper formatting.

```bash
python tests/test_complete_verification.py
```

**What it tests:**
- Citations appear in text as [1], [2], etc.
- Each citation has an annotation with correct start/end positions
- Annotation positions match actual text locations
- Citations have real URLs and titles
- All citations in text have corresponding annotations
- Sources section is included with proper references

### 2. Attachment Processing Verification
This test verifies that attachments are properly processed and content is extracted.

```bash
python tests/test_attachment_verification.py
```

**What it tests:**
- PDF attachments are processed and content extracted
- Multiple attachments are handled correctly
- Attachment agent is triggered when attachments are present
- Empty attachment arrays don't trigger the attachment agent
- Attachments work with other agents (web search, citations)

### 3. Iterative Refinement Verification
This test verifies that the iterative refinement system works and improves responses.

```bash
python tests/test_iteration_verification.py
```

**What it tests:**
- Complex queries trigger iterations
- Simple queries don't waste time on iterations
- Iterations work in both streaming and non-streaming modes
- Iterated responses are more comprehensive
- Response quality improves with iterations

### 4. Individual Feature Tests

#### Citation Format Test
```bash
python tests/test_citation_format.py
```
- Verifies [1] format is used, not markdown links

#### Citation Streaming Test
```bash
python tests/test_citation_streaming.py
```
- Verifies citation annotations stream with positions

#### Comprehensive Streaming Flow Test
```bash
python tests/test_comprehensive_streaming_flow.py
```
- Shows complete event flow for debugging

#### All Features Summary Test
```bash
python tests/test_all_features_summary.py
```
- Quick check of all major features

## Expected Results

### ✅ Working Features:
1. **Citation Format**: Uses [1], [2] format in both streaming and non-streaming
2. **Citation Position Tracking**: Accurate start/end positions with real URLs
3. **Streaming Events**: Full OpenAI Response API compliance
4. **Attachment Processing**: Extracts content from PDFs and other files
5. **Iterative Refinement**: Improves complex responses through multiple passes

### 📊 Success Criteria:
- All citations have matching annotations with correct positions
- Attachment content appears in responses when files are provided
- Complex queries trigger 1-3 iterations for better quality
- Streaming includes all required events (created, delta, completed, done)
- Citation annotations include URLs and titles from sources

## Troubleshooting

If tests fail:

1. Check server is running: `curl http://localhost:5002/health`
2. Check logs: `tail -f ml_server.log`
3. Verify database connection (PostgreSQL on port 5454)
4. Ensure virtual environment is activated
5. Check API keys are set in environment

## Example Output

When everything works correctly, you should see:
- Citations like: "Machine learning is a subset of AI [1] that enables..."
- Annotations with positions: `Citation: [1], Position: 204-207, URL: https://...`
- Attachment responses mentioning actual file content
- Iteration counts > 0 for complex queries
- All verification checks showing ✅