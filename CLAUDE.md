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

# TEST ENVIRONMENT (CRITICAL - READ CAREFULLY!)
#
# ⚠️ UNIFIED TEST ENVIRONMENT - ACTUAL CONFIGURATION ⚠️
# The ACTUAL running test environment (verified on 2025-08-01):
#    - Container Name: youwoai_test_db (NOT humansa_test_postgres)
#    - ML Server: Port 6001 (test instance) - ALL TESTS MUST RUN ON THIS PORT!
#    - PostgreSQL: Port 5454 (Docker container)
#    - Database: test4 (primary), youwoai_test (also available)
#    - Password: 12931 (NOT 031203 from docker-compose.yml!)
#    - User: postgres
#
# 🚨 IMPORTANT: NEVER run tests on port 5001 (production/dev server)!
# All test scripts MUST use port 6001 for the test environment.
#
# 🚨 LAUNCHING TEST ENVIRONMENT:
# The test server MUST be launched using test environment scripts, NOT main.py directly!
# Use: ./run_HUMANSA_test_environment_v2_enhanced.sh
# This script properly sets up:
#   - Environment variables (ENVIRONMENT=test, ML_SERVER_PORT=6001)
#   - Database connection to test database
#   - Correct server startup with --port 6001 argument
#
# DO NOT use: python -m src.main (this will use port 5001)
# DO use: python3 -m src.main --port 6001 (with proper env vars)
#
# 🚨 IMPORTANT DISCREPANCIES:
# - docker-compose.yml shows password "031203" but actual is "12931"
# - Some scripts expect port 5456 but actual is 5454
# - Configuration is defined in: test_environment/unified_test_config.py
#
# To verify test database:
# PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "SELECT 1;"
#
# To check running container:
# docker ps | grep youwoai_test_db
#
# Run tests with:
# DIGIT=2 ./run_final_tests.sh  # Uses correct configuration (DIGIT=2 for new branch)

# HUMANSA V2 Testing with Enhanced Logging
./run_HUMANSA_test_environment_v2_enhanced.sh  # Run V2 tests with full process visibility
./run_HUMANSA_v2_test_40_cases_enhanced.sh     # Run 40 comprehensive test cases

# HUMANSA V2 Workflow Orchestrator (NEW - Streaming Reasoning)
export HUMANSA_USE_WORKFLOW_ORCHESTRATOR=true  # Enable AgentWorkflow with reasoning visibility
python -m src.main                              # Start server with workflow orchestrator
python test_workflow_integration.py            # Test reasoning stream integration

# HUMANSA V2 Pattern 2 Orchestrator (LlamaIndex FunctionAgent Pattern)
export HUMANSA_USE_PATTERN2=true               # Enable Pattern 2 with FunctionAgent
export HUMANSA_ENHANCED_LOGGING=true           # Enable detailed logging
python -m src.main                             # Start server with Pattern 2
# Pattern 2 provides:
# - FunctionAgent as main orchestrator
# - Sub-agents exposed as context-aware tools
# - Shared LlamaIndex Context across all tool calls
# - Full reasoning chain visibility in streaming
# - Hybrid memory: LlamaIndex Context + UnifiedContext + Mem0
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

Comprehensive test environment with UNIFIED configuration:

**Test Database (ACTUAL)**:
- **Container**: youwoai_test_db (running on port 5454)
- **Password**: 12931 (NOT 031203 as docker-compose suggests!)
- **Databases**: test4 (primary), youwoai_test (secondary)
- **Configuration**: See `test_environment/unified_test_config.py`

**Test ML Server**:
- **Port**: 6001 (dedicated test instance)
- **Environment**: ENVIRONMENT=test

**Important Notes**:
- The actual password differs from docker-compose.yml
- All test scripts should use unified_test_config.py
- User IDs must be strings (e.g., "test_user_10001")

To verify test environment:
```bash
# Check if test database is running
docker ps | grep youwoai_test_db

# Test database connection
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "SELECT 1;"

# Run all tests with correct configuration
./run_final_tests.sh
```

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