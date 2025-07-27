# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Activate virtual environment
source youwo-ml-venv/bin/activate

# Start the server
python -m src.main

# Format code
make format  # Uses black and isort

# Run tests
python test_enhanced_api.py
python test_startup.py
python test_doctor_tools.py  # For Humansa agent testing

# Docker operations
./cleanup-docker.sh  # Clean up Docker resources
docker-compose -f docker-compose.local.yml up  # Local development

# Humansa V2 Testing with Enhanced Logging
./run_humansa_test_environment_v2_enhanced.sh  # Run V2 tests with full process visibility
```

## High-Level Architecture

This is the YouWoAI ML Server - an async web server providing OpenAI-compatible APIs with enhanced features.

### Core Components

1. **Main Entry**: `src/main.py` - Quart application on port 5001
2. **Multi-Agent System**: Located in `src/chat/agent/`
   - Router Agent: Determines which agents to invoke
   - RAG Agent: Retrieval-augmented generation
   - Web Search Agent: External information retrieval
   - Attachment Agent: File processing
   - Citation Agent: Source attribution
3. **Provider Abstraction**: `src/chat/provider/` - Unified interface for multiple LLMs
4. **Humansa Medical Agent**: `src/humansa/` - Specialized healthcare AI with tool calling

### Key API Endpoints

- `/v1/chat/completions` - OpenAI-compatible chat (streaming + citations)
- `/v1/multi-agent/response` - Multi-agent workflow endpoint
- `/v1-humansa/chat/completions` - Medical AI with tool calling
- `/analyze_link` - YouTube/Bilibili/web content analysis

### Database

PostgreSQL with pgvector extension for embeddings:
- Connection via `src/chat/postgres/`
- Stores user notes, embeddings, conversations
- Test environment uses port 5454

### Testing

Comprehensive test environment in `test_environment/`:
- Isolated PostgreSQL instance
- Pre-populated test data
- Integration tests for all major features

### Important Patterns

1. **Streaming**: All chat endpoints support SSE streaming via `src/chat/streaming/`
2. **Error Handling**: Consistent error responses with status codes
3. **Token Management**: Count tokens before processing (`src/chat/token/`)
4. **Async Operations**: Everything is async using Quart's async/await
5. **Citation System**: Automatic citation generation with position tracking

### Humansa V2 Enhanced Logging and Streaming

The V2 system now supports enhanced logging and true streaming to show:
- Complete thinking process of each agent (Thought → Action → Observation → Answer)
- Which agents are called and their execution order
- Each agent's reasoning and tool calls
- Mem0 integration status and loaded memory data
- Full untruncated responses

**Streaming Format**:
When streaming is enabled (`"stream": true`), the response includes:
- 🤔 正在思考... (Processing indicator)
- 💭 **思考**: (Agent's reasoning process)
- 🔧 **行动**: (Tool/agent being called)
- 📊 **观察结果**: (Results from tool calls)
- ✅ **最终回答**: (Final response to user)

Enable enhanced logging:
1. **Environment Variable**: `export HUMANSA_ENHANCED_LOGGING=true`
2. **Request Parameter**: Include `"debug": true` in API requests
3. **Test Script**: Use `./run_humansa_test_environment_v2_enhanced.sh`

**Important**: The streaming implementation uses LlamaIndex's native `stream_chat` method which provides the complete ReAct reasoning chain, NOT fake streaming.

### Environment Variables

Required:
- `OPENAI_API_KEY`
- Database credentials (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)

Optional:
- Additional LLM provider keys (`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, etc.)
- Web search keys (`SERPER_API_KEY`, `SERPAPI_API_KEY`)