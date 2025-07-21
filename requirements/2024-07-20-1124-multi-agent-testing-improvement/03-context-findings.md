# Codebase Analysis Findings

## Multi-Agent System Architecture

### Agents Identified (7 total)
1. **RouterAgent** - Query routing and intent classification
2. **RAGAgent** - Knowledge base retrieval (notes/conversations)
3. **WebSearchAgent** - Real-time web information retrieval
4. **AttachmentAgent** - File attachment processing
5. **ResponseAgent** - Response synthesis and generation
6. **CitationAgent** - Citation formatting and reference mapping
7. **CodeInterpreterAgent** - Python code execution

### Streaming Format (OpenAI-Compatible SSE)
- Lifecycle events: created, in_progress, completed, failed
- Output events: output_item.added/done
- Content streaming: reasoning_text.delta, output_text.delta
- Tool-specific events: web_search_call.*, file_search_call.*
- Custom events: citations, title_generated, usage

### Current Test Coverage
- Individual agent tests exist
- Basic streaming tests implemented
- Mock integration tests available
- Missing: comprehensive edge cases, iterative workflow tests

### Key Implementation Details
- Parallel agent execution for context gathering
- Priority system: Attachments > RAG > Web Search
- Iterative refinement with IterativeOrchestrator
- Citation engine with LLM-based rewriting
- Full OpenAI API compatibility

### Areas Needing Testing
1. Complex multi-agent interactions
2. Edge cases in streaming format
3. Citation accuracy and format compliance
4. Iterative workflow effectiveness
5. Error recovery and resilience
6. Performance under load
7. Niche scenarios (empty results, timeouts, etc.)