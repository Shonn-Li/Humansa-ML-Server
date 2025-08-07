# CLAUDE.md - YouWoAI ML Server

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with the YouWoAI ML Server codebase.

## Project Overview

YouWoAI ML Server is the AI backbone of the YouWoAI platform, providing:
- **Multi-Agent AI System**: Autonomous agents for different tasks (routing, RAG, web search, citations)
- **Chat Completions**: OpenAI-compatible API with streaming support
- **Embeddings System**: Note and conversation embeddings with pgvector
- **Humansa AI-Agent**: Tool-calling AI agent system for specialized tasks
- **Document Processing**: File analysis and conversion capabilities

## Key Points Summary

1. **Two Main Endpoints with Different Formats**:
   - `/v1/chat/completions` - Uses OpenAI Chat Completion API format (simple text responses)
   - `/v1/multi-agent/response` - Uses OpenAI Response API format (structured output items)
   - Multi-agent is the upgraded version with reasoning traces, web search results, and function calls

2. **Test Environment**:
   - Test Server: Port **5002** (NOT 5001 or 5200)
   - Test Database: Port **5454** with database `youwoai_test`
   - Complete isolated environment with pre-seeded test data

3. **Agent Architecture**:
   - All agents inherit from `BaseAgent` and are modular
   - Agents share infrastructure modules but operate independently
   - Router agent decides which agents to activate based on query analysis

4. **Critical Practices**:
   - ALWAYS activate virtual environment before any Python work
   - ALWAYS update requirements.txt after pip install
   - ALWAYS use port 5002 for testing

## Architecture Overview

The ML Server uses a modular architecture with two main systems:

### 1. Main YouWoAI System (`src/chat/`)
- **Multi-agent workflow** with specialized agents
- **RAG (Retrieval-Augmented Generation)** with citations
- **Embedding management** for notes and conversations
- **Web search integration**
- **Streaming response generation**

### 2. Humansa AI-Agent System (`src/humansa/`)
- **Tool-calling agents** for healthcare/appointment scenarios
- **OpenAI function calling** integration
- **Separate database schema** for Humansa-specific data

## API Format Differences

### 1. Chat Completions (`/v1/chat/completions`)
- Uses **OpenAI Chat Completion API format**
- Standard request/response structure
- Supports streaming with SSE (Server-Sent Events)
- Simple text-based responses with citations

### 2. Multi-Agent Response (`/v1/multi-agent/response`)
- Uses **OpenAI Response API format** with output items
- Enhanced structured output with multiple item types
- Supports reasoning traces, web search results, function calls
- **Upgraded version** of chat completions with more capabilities
- Each output item follows the envelope pattern: `added` → `streaming` → `done`

## Critical Development Practices

### 1. Virtual Environment (MANDATORY)

**ALWAYS activate the virtual environment before ANY Python work:**

```bash
source youwo-ml-venv/bin/activate  # On Windows: youwo-ml-venv\Scripts\activate
which python  # Verify activation - should show path inside youwo-ml-venv
```

**WARNING**: Running without venv will use system Python and cause import errors!

### 2. Package Management (CRITICAL)

When installing new packages:

```bash
# 1. ALWAYS activate venv first
source youwo-ml-venv/bin/activate

# 2. Install package
pip install <package>

# 3. IMMEDIATELY update requirements.txt
pip freeze > requirements.txt

# 4. Commit the updated requirements.txt
git add requirements.txt
git commit -m "chore: add <package> to requirements"
```

**CRITICAL**: Docker builds WILL FAIL if requirements.txt is outdated!

### 3. Port Configuration (DIGIT System)

The ML Server uses DIGIT-based port configuration:

```bash
# In .env.local
DIGIT=5
ML_SERVER_PORT=5005  # Port 500X where X is your DIGIT
DB_ACTIVE_DATABASE=test5  # Database testX where X is your DIGIT
```

**IMPORTANT - Test Environment**:
- **Test Server Port**: 5002 (NOT 5001 or 5200)
- **Test Database Port**: 5454 (NOT production 5432)
- **Test Database Name**: youwoai_test
- **Test Database Password**: 031203

### 4. Logging Best Practices

**Configure logging levels to reduce noise:**

```python
import logging

# Reduce Azure SDK verbosity
azure_loggers = [
    'azure.core.pipeline.policies.http_logging_policy',
    'azure.ai.inference',
    'azure.core.pipeline',
    'azure.identity',
    'azure.core'
]
for logger_name in azure_loggers:
    azure_logger = logging.getLogger(logger_name)
    azure_logger.setLevel(logging.WARNING)

# Your module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

## Comprehensive Directory Structure

```
YouWoAI-ML-Server/
├── src/
│   ├── main.py                    # Entry point - serves both YouWoAI and Humansa systems
│   ├── main_production.py         # Production-specific entry point
│   │
│   ├── chat/                      # Main YouWoAI AI System (Multi-Agent Architecture)
│   │   ├── agent/                 # Multi-agent implementations
│   │   │   ├── base.py           # Abstract base class for all agents
│   │   │   ├── router_agent.py   # Analyzes queries and routes to appropriate agents
│   │   │   ├── context_search_agent.py  # RAG search for notes/conversations (replaces rag_agent.py)
│   │   │   ├── websearch_agent.py       # Web search via search engines
│   │   │   ├── attachment_agent.py      # Process file attachments (PDFs, docs, images)
│   │   │   ├── response_agent.py        # Generate final response with citations
│   │   │   ├── citation_agent.py        # Citation generation and formatting
│   │   │   ├── code_interpreter_agent.py # Execute Python code
│   │   │   ├── python_tool_agent.py     # Python-specific tools
│   │   │   └── agentic_rag_processor.py # Advanced RAG processing
│   │   │
│   │   ├── attachment/            # File attachment handling
│   │   │   ├── file_attachment_manager.py # Central attachment processor
│   │   │   ├── url_embeddings_v2.py      # URL content embedding
│   │   │   └── README.md
│   │   │
│   │   ├── citation/              # Citation system
│   │   │   ├── citation_engine.py        # Core citation logic
│   │   │   ├── citation_position_tracker.py # Track citation positions
│   │   │   └── streaming_citation_engine.py # Streaming citation support
│   │   │
│   │   ├── config/                # Configuration
│   │   │   └── system_prompts.py # System prompts for different models
│   │   │
│   │   ├── embedding/             # Embedding management system
│   │   │   ├── embedding_manager.py      # Central embedding coordinator
│   │   │   ├── embedding_provider_selector.py # Provider abstraction (OpenAI/Azure)
│   │   │   ├── note_embedder.py          # Note-specific embedding logic
│   │   │   ├── conversation_embedder.py  # Conversation embedding logic
│   │   │   ├── text_processing.py        # Text chunking and processing
│   │   │   ├── openai_embeddings.py      # OpenAI embedding provider
│   │   │   ├── azure_embeddings.py       # Azure embedding provider
│   │   │   └── admin_embedding_endpoint.py # Admin controls
│   │   │
│   │   ├── endpoints/             # API endpoints
│   │   │   ├── modular_chat_endpoint.py  # /v1/chat/completions handler
│   │   │   ├── multi_agent_endpoint_v2.py # /v1/multi-agent/response handler
│   │   │   ├── url_embeddings_endpoint.py # URL embedding endpoints
│   │   │   ├── admin_embedding_endpoints.py # Admin embedding controls
│   │   │   ├── conversation_title_endpoint.py # Title generation
│   │   │   ├── file_analyzer_endpoint.py # File analysis API
│   │   │   └── document_converter_endpoint.py # Document conversion API
│   │   │
│   │   ├── postgres/              # Database operations
│   │   │   ├── db_manager.py     # Connection pooling and management
│   │   │   ├── embedding_operations.py   # Embedding CRUD operations
│   │   │   ├── conversation_operations.py # Conversation CRUD
│   │   │   └── url_embedding_operations.py # URL embedding storage
│   │   │
│   │   ├── prompt/                # System prompts
│   │   │   ├── youwoai-en.md    # English system prompt
│   │   │   └── youwoai-zh.md    # Chinese system prompt
│   │   │
│   │   ├── provider/              # LLM providers
│   │   │   ├── llm_provider.py   # Provider selection and management
│   │   │   ├── o3_model_wrapper.py # O3 model integration
│   │   │   ├── o3_direct_client.py # Direct O3 API client
│   │   │   └── README.md
│   │   │
│   │   ├── query/                 # Query processing
│   │   │   ├── query_transformer.py     # Query enhancement
│   │   │   └── query_transformer_new.py # Enhanced query transformer
│   │   │
│   │   ├── rag/                   # RAG (Retrieval-Augmented Generation)
│   │   │   └── rag_processor.py  # Core RAG processing logic
│   │   │
│   │   ├── router/                # Intelligent routing
│   │   │   ├── intelligent_router.py    # Main router logic
│   │   │   ├── intelligent_router_retriever.py
│   │   │   └── intelligent_router_retriever_fixed.py
│   │   │
│   │   ├── search/                # Search functionality
│   │   │   └── hybrid_search.py  # Hybrid search implementation
│   │   │
│   │   ├── streaming/             # Streaming infrastructure
│   │   │   ├── streaming_response_generator.py # SSE streaming
│   │   │   └── streaming_response_generator_new.py # Enhanced streaming
│   │   │
│   │   ├── title/                 # Title generation
│   │   │   ├── title_generator.py # Core title generation
│   │   │   ├── title_endpoints.py # Title API endpoints
│   │   │   └── conversation_title_service.py # Title service logic
│   │   │
│   │   ├── token/                 # Token management
│   │   │   ├── token_counter.py  # Count tokens for different models
│   │   │   ├── text_truncator.py # Truncate text to fit token limits
│   │   │   └── usage_examples.py
│   │   │
│   │   ├── utils/                 # Utilities
│   │   │   ├── document_converter.py # Convert documents to text
│   │   │   ├── reasoning_handler.py  # Handle reasoning traces
│   │   │   └── think_block_parser.py # Parse thinking blocks
│   │   │
│   │   └── websearch/             # Web search
│   │       └── web_search_processor.py # Web search implementation
│   │
│   ├── humansa/                   # Humansa AI-Agent System
│   │   ├── agent/
│   │   │   └── humansa_agent.py  # Main Humansa agent logic
│   │   ├── endpoints/
│   │   │   ├── humansa_chat_endpoint.py # /v1-humansa/chat/completions
│   │   │   └── o3_demo_endpoint.py      # /o3-demo endpoint
│   │   ├── openai/                # OpenAI integration
│   │   │   ├── openai_integration.py    # Function calling support
│   │   │   ├── openai_response_streaming_handler.py
│   │   │   ├── tool_converter.py
│   │   │   └── utils.py
│   │   ├── postgres/
│   │   │   └── database.py       # Humansa-specific DB operations
│   │   ├── prompts/
│   │   │   ├── humansa_system_prompt.py
│   │   │   ├── humansa_react_system_header.py
│   │   │   ├── appointment_booking_prompt.py
│   │   │   └── intelligent_prompt_selector.py
│   │   ├── streaming/
│   │   │   └── comprehensive_response_streaming_handler_fixed.py
│   │   ├── tools/
│   │   │   ├── humansa_tools.py # Tool implementations
│   │   │   └── enhanced_web_search.py
│   │   └── README.md
│   │
│   ├── file_analyzer/             # File analysis utilities
│   │   └── file_text_extractor.py
│   │
│   ├── link/                      # Link analysis
│   │   └── link_analyzer.py      # Analyze URLs and extract content
│   │
│   └── utils/                     # Global utilities
│       └── azure_session_manager.py
│
├── test/                          # Comprehensive Test Suite
│   ├── core/                      # Core test infrastructure
│   │   ├── test_server.py        # Test server (runs on port 5002)
│   │   ├── validate.py           # Quick validation tests
│   │   └── test_comprehensive_detailed.py # Full test suite
│   │
│   ├── multi_agent/               # Multi-agent specific tests
│   │   ├── test_multi_agent_comprehensive.py # 30+ test scenarios
│   │   ├── test_multi_agent_quick.py        # Critical tests only
│   │   └── test_multi_agent.py              # Additional tests
│   │
│   ├── integration/               # Integration tests
│   │   ├── test_context_search.py
│   │   ├── test_direct_endpoint.py
│   │   ├── test_environment_validation.py
│   │   └── test_environment_working.py
│   │
│   ├── unit/                      # Unit tests
│   │
│   ├── utilities/                 # Test utilities
│   │
│   └── README.md                  # Test documentation
│
├── test_environment/              # Isolated Test Environment
│   ├── docker-compose.yml        # PostgreSQL on port 5454
│   ├── sql/                      # Database initialization
│   │   ├── 01_extensions.sql    # pgvector and pg_trgm
│   │   ├── 02_create_tables.sql # All table schemas
│   │   ├── 03_test_data.sql     # Test users, notes, folders
│   │   ├── 04_embeddings.sql    # 190 pre-generated embeddings
│   │   └── 05_test_conversations.sql # Test conversations
│   ├── scripts/
│   │   ├── setup.sh             # One-command setup
│   │   ├── export_embeddings.py # Export embeddings from prod
│   │   └── verify_setup.py      # Verify test environment
│   └── README.md
│
├── documentation/                 # Additional Documentation
│   ├── STREAMING_OUTPUT_FORMAT_DOCUMENTATION.md # Comprehensive streaming spec
│   ├── TEST_ENVIRONMENT.md
│   ├── instruction.md
│   └── agent/
│       ├── YouWoAI_Multi_Agent_Modular_Flow_Diagram.md
│       └── YouWoAI_Multi_Agent_Streaming_V2_Diagram.md
│
├── requirements.txt              # Python dependencies (CRITICAL - keep updated!)
├── Dockerfile                    # Production container
├── docker-compose.local.yml      # Local development
├── test.sh                       # Test runner script
└── youwo-ml-venv/               # Virtual environment (DO NOT COMMIT)
```

## Complete API Endpoint Documentation

### Health & Status Endpoints

```
GET  /health                        # ALB/Docker health check
GET  /ping                         # Basic connectivity test
GET  /debug/info                   # Debug information
```

### Main YouWoAI Endpoints

#### 1. Chat Completions (OpenAI Chat Completion Format)
```
POST /v1/chat/completions
```
**Purpose**: Standard OpenAI-compatible chat API with RAG and citations
**Handler**: `modular_chat_endpoint.py`
**Features**:
- Streaming and non-streaming responses
- RAG integration for user context
- Citation generation
- File attachment support

**Request Format**:
```json
{
  "messages": [{"role": "user", "content": "Hello"}],
  "model": "gpt-4.1-nano",
  "stream": false,
  "user_id": 10001,
  "attachments": [],
  "enable_citations": true,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

#### 2. Multi-Agent Response (OpenAI Response API Format)
```
POST /v1/multi-agent/response
```
**Purpose**: Enhanced multi-agent workflow with structured output items
**Handler**: `multi_agent_endpoint_v2.py`
**Features**:
- Autonomous agent collaboration
- Structured output items (reasoning, web search, function calls)
- Full streaming support with SSE
- Output item envelope pattern: `added` → `streaming` → `done`

**Request Format**:
```json
{
  "messages": [{"role": "user", "content": "Search the web for AI news"}],
  "model": "gpt-4.1-nano",
  "stream": true,
  "user_id": 10001,
  "enable_citations": true,
  "attachments": []
}
```

**Streaming Events**:
- `response.created`
- `response.output_item.added`
- `response.reasoning_text.delta`
- `response.web_search_call.searching`
- `response.output_text.delta`
- `response.output_item.done`
- `response.completed`

#### 3. Embedding Management Endpoints

```
POST /v1/embeddings/conversation   # Embed conversations (incremental support)
POST /v1/embeddings/url            # Create URL embeddings
POST /v1/embeddings/url/check      # Check if URL is already embedded
POST /v1/embeddings/url/search     # Search URL embeddings
GET  /v1/embeddings/url/status     # Get URL embedding status

POST /notes/create-embeddings      # Embed multiple notes
POST /notes/embed-summary          # Embed note AI summaries only
```

#### 4. Admin Endpoints

```
POST /admin/embedding/notes        # Start embedding missing notes
POST /admin/embedding/conversations # Start embedding missing conversations
POST /admin/embedding/all          # Embed all missing content
GET  /admin/embedding/status       # Check embedding progress
POST /admin/embedding/stop         # Stop embedding process
```

#### 5. Utility Endpoints

```
POST /analyze_link                 # Analyze and extract link content
GET  /note_text/<note_id>         # Get note text by ID
GET  /note_title/<note_id>        # Get note title by ID
```

#### 6. Title Generation Endpoints

```
POST /v1/conversation/title        # Generate single conversation title
POST /v1/conversation/titles/batch # Batch title generation
POST /v1/conversation/titles/migrate # Migrate all titles
GET  /v1/conversation/title/health # Title service health check
```

#### 7. File Processing Endpoints

```
POST /v1/file/analyze             # Analyze file content
POST /v1/document/convert         # Convert documents to text
```

### Humansa AI-Agent Endpoints

```
POST /v1-humansa/chat/completions # Humansa chat with tool calling
POST /humansa/response            # Backend proxy endpoint for Humansa
POST /o3-demo                     # O3 reasoning demonstration
```

**Humansa Features**:
- OpenAI function calling support
- Healthcare/appointment-specific tools
- Comprehensive streaming format
- Separate database schema

**Note**: Humansa system is being redesigned. Current tests are deprecated and a better implementation is coming soon.

### Request/Response Format Differences

#### Chat Completions Response (Simple):
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Here's my response..."
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 10, "completion_tokens": 20}
}
```

#### Multi-Agent Response (Structured):
```json
{
  "id": "resp-xyz789",
  "object": "response",
  "output_items": [
    {
      "id": "reasoning_123",
      "type": "reasoning",
      "content": [{"type": "reasoning_text", "text": "I need to search..."}]
    },
    {
      "id": "search_456",
      "type": "web_search_call",
      "action": {"query": "AI news", "search_engine": "serper"},
      "results": [...]
    },
    {
      "id": "msg_789",
      "type": "message",
      "role": "assistant",
      "content": [{"type": "output_text", "text": "Based on my search..."}]
    }
  ]
}
```

## Testing Guidelines

### 1. Complete Test Environment Setup

The ML Server uses a **fully isolated test environment** with its own database:

#### Test Infrastructure:
- **Test Server Port**: 5002 (runs test version of main.py)
- **Test Database**: PostgreSQL with pgvector on port 5454
- **Database Name**: youwoai_test
- **Test Data**: Pre-seeded with users, notes, embeddings, and conversations

#### Starting the Test Environment:

```bash
# 1. Start the test database (Docker required)
cd test_environment
docker-compose up -d

# 2. Verify database is running
PGPASSWORD=031203 psql -h localhost -p 5454 -U postgres -d youwoai_test

# 3. Start the test server (Terminal 1)
python test/core/test_server.py  # Runs on port 5002

# 4. Run tests (Terminal 2)
python test/multi_agent/test_multi_agent_comprehensive.py
```

### 2. Test Database Content

The test environment includes:
- **3 Test Users**: IDs 10001-10003
- **9 Test Notes**: Including ML papers, YouTube videos, documents
- **190 Embeddings**: Pre-generated for testing RAG functionality
- **9 Conversations**: Rich test conversations with proper titles
- **2 Folders**: June-ML and Startup categories

### 3. Running Different Test Suites

```bash
# Quick validation tests
./test.sh         # Runs validate.py

# Comprehensive test suite
./test.sh full    # Runs test_comprehensive_detailed.py

# Multi-agent specific tests
python test/multi_agent/test_multi_agent_comprehensive.py  # 30+ test cases
python test/multi_agent/test_multi_agent_quick.py         # Critical tests only
```

### 4. Model Selection for Testing

**IMPORTANT - Model Usage:**
- Use `gpt-4.1-nano` or O3 series for general testing
- `gpt-4` is DEPRECATED - do NOT use
- `gpt-4o-mini` is ONLY for image recognition tasks
- Default test model: `gpt-4.1-nano`

## Common Development Workflows

### Adding a New Agent

1. Create agent class in `src/chat/agent/`:
```python
from chat.agent.base import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, query: str, context: Dict) -> Dict:
        # Agent logic here
        return {"status": "success", "data": {...}}
```

2. Register in multi-agent workflow (`multi_agent_endpoint_v2.py`)

3. Add tests in `test/multi_agent/`

### Adding a New Endpoint

1. Create endpoint file in `src/chat/endpoints/`
2. Register in `main.py` under appropriate function:
   - `register_chat_endpoints()` for chat-related
   - `register_embedding_endpoints()` for embeddings
   - `register_humansa_endpoints()` for Humansa

3. Update API documentation

### Modifying Embeddings

1. Work with files in `src/chat/embedding/`
2. Use `EmbeddingProviderSelector` for provider abstraction
3. Always handle incremental updates for conversations
4. Test with `test_environment/` data

## Environment Variables

### Required in `.env.local`:
```bash
DIGIT=5                          # Your personal digit (0-9)
ML_SERVER_PORT=5005              # Port 500X
DB_ACTIVE_DATABASE=test5         # Database testX

# Optional overrides
OPENAI_API_KEY=sk-...            # If different from .env
AZURE_OPENAI_ENDPOINT=...        # For Azure models
```

### Model Configuration:
```bash
# In .env (shared test configuration)
OPENAI_API_KEY=sk-test-key
ANTHROPIC_API_KEY=test-key
GEMINI_API_KEY=test-key
```

## Debugging Tips

### 1. Enable Detailed Logging
```python
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 2. Check Database Connection
```bash
# Verify your DIGIT database exists
PGPASSWORD=password psql -h localhost -p 5432 -U postgres -d test5
```

### 3. Common Issues

**Import Errors**: Always check venv is activated
```bash
which python  # Should show path inside youwo-ml-venv
```

**Port Conflicts**: Ensure correct DIGIT configuration
```bash
lsof -i :5005  # Check if port is in use
```

**Streaming Issues**: Check for proper async/await usage
```python
# Correct
async for chunk in stream_generator():
    yield f"data: {json.dumps(chunk)}\n\n"

# Incorrect (missing async)
for chunk in stream_generator():  # Will fail!
    yield f"data: {json.dumps(chunk)}\n\n"
```

## Performance Optimization

### 1. Embedding Batch Sizes
```python
# In embedding operations
embeddings = await embedder.get_embeddings_with_retry(
    texts,
    max_retries=3,
    batch_size=50  # Optimal for OpenAI
)
```

### 2. Database Connection Pooling
```python
# Use connection pooling for PostgreSQL
from chat.postgres.db_manager import get_db_connection

# Connection is automatically pooled
with get_db_connection() as conn:
    # Your queries
```

### 3. Async Best Practices
- Use `asyncio.gather()` for parallel operations
- Avoid blocking operations in async functions
- Use `asyncio.to_thread()` for CPU-bound tasks

## Security Considerations

1. **Never commit real API keys** - Use test keys in .env
2. **Validate user inputs** - Especially user_id and context
3. **Sanitize file uploads** - Check file types and sizes
4. **Rate limiting** - Implement for production deployments

## Agent Dependencies and Module Architecture

### Agent Hierarchy

All agents inherit from `BaseAgent` and are designed to be modular with minimal dependencies:

```
BaseAgent (abstract base class)
├── RouterAgent - Decides which agents to activate
├── ContextSearchAgent - RAG search (replaces old RAGAgent)
├── WebSearchAgent - Web search functionality
├── AttachmentAgent - File processing
├── ResponseAgent - Response generation with citations
├── CodeInterpreterAgent - Code execution
└── PythonToolAgent - Python-specific tools
```

### Module Dependencies

Each agent uses shared infrastructure modules:

1. **Router Agent** (`router_agent.py`)
   - Uses: `IntelligentRouter`, `QueryTransformer`, `LLMProviderSelector`
   - Purpose: Analyzes queries and determines agent activation

2. **Context Search Agent** (`context_search_agent.py`)
   - Uses: `RAGProcessor`, `embedding_manager`
   - Purpose: Searches notes and conversations

3. **Web Search Agent** (`websearch_agent.py`)
   - Uses: `WebSearchProcessor`
   - Purpose: Performs web searches

4. **Response Agent** (`response_agent.py`)
   - Uses: `LLMProvider`, `CitationEngine`, `SystemPromptManager`
   - Purpose: Generates final response with citations

### Shared Infrastructure Modules

These modules support multiple agents:

- **`llm_provider.py`**: LLM model selection and management
- **`embedding_manager.py`**: Embedding operations for notes/conversations
- **`rag_processor.py`**: RAG search functionality
- **`citation_engine.py`**: Citation generation and tracking
- **`streaming_response_generator.py`**: SSE streaming support
- **`query_transformer.py`**: Query enhancement and transformation
- **`db_manager.py`**: Database connection pooling

## Detailed File Usage Mapping

### Core Entry Points

1. **`src/main.py`**
   - Main application entry point
   - Registers all endpoints
   - Configures Quart app with CORS
   - Serves both YouWoAI and Humansa systems

### Chat System (`src/chat/`)

#### Endpoints
- **`modular_chat_endpoint.py`**: OpenAI-compatible chat API
- **`multi_agent_endpoint_v2.py`**: Multi-agent response API with output items
- **`url_embeddings_endpoint.py`**: URL embedding operations
- **`admin_embedding_endpoints.py`**: Admin embedding controls
- **`conversation_title_endpoint.py`**: Title generation
- **`file_analyzer_endpoint.py`**: File analysis
- **`document_converter_endpoint.py`**: Document conversion

#### Agents
- **`base.py`**: Abstract base class for all agents
- **`router_agent.py`**: Query routing logic
- **`context_search_agent.py`**: RAG search implementation
- **`websearch_agent.py`**: Web search implementation
- **`attachment_agent.py`**: File attachment processing
- **`response_agent.py`**: Response generation with citations
- **`citation_agent.py`**: Citation-specific logic
- **`code_interpreter_agent.py`**: Code execution capabilities

#### Core Infrastructure
- **`embedding/`**: Embedding generation and management
  - `embedding_manager.py`: Central embedding coordinator
  - `note_embedder.py`: Note-specific embeddings
  - `conversation_embedder.py`: Conversation embeddings
  - `embedding_provider_selector.py`: Provider abstraction

- **`postgres/`**: Database operations
  - `db_manager.py`: Connection pooling
  - `embedding_operations.py`: Embedding CRUD
  - `conversation_operations.py`: Conversation CRUD

- **`provider/`**: LLM providers
  - `llm_provider.py`: Provider selection and management
  - `o3_model_wrapper.py`: O3 model integration

- **`streaming/`**: Streaming infrastructure
  - `streaming_response_generator.py`: SSE streaming
  - `streaming_response_generator_new.py`: Enhanced streaming

### Humansa System (`src/humansa/`)

#### Endpoints
- **`humansa_chat_endpoint.py`**: Humansa AI-agent chat
- **`o3_demo_endpoint.py`**: O3 reasoning demonstration

#### Core Components
- **`humansa_agent.py`**: Main Humansa agent logic
- **`humansa_tools.py`**: Tool implementations
- **`openai_integration.py`**: OpenAI function calling
- **`comprehensive_response_streaming_handler_fixed.py`**: Streaming handler

### Humansa Multi-Agent System (V2)

The Humansa system has evolved into a sophisticated multi-agent orchestration framework:

#### Architecture
- **Pattern 2 Orchestration** (`v2/orchestrator_pattern2.py`): LlamaIndex FunctionAgent pattern with sub-agents as tools
- **Workflow State Management**: Maintains patient context, medical history, and agent coordination state
- **Memory Integration**: Long-term memory via Mem0 for patient profiles and conversation continuity

#### Specialized Agents (`v2/agents/`)
- **Appointment Agent**: Books medical appointments, manages scheduling
- **Diagnosis Agent**: Analyzes symptoms, provides assessments
- **Medication Agent**: Drug information, interaction checks, prescription management
- **Emergency Triage Agent**: Urgency assessment, emergency routing
- **Product Agent**: Medical product recommendations and ordering
- **General Medical Agent**: General health Q&A and guidance

#### Key Features
- **Transparent Reasoning**: Full visibility into agent decision-making process
- **Tool Orchestration**: Coordinated tool execution across agents
- **Context Persistence**: Maintains state across multi-turn conversations
- **Error Resilience**: Graceful fallback strategies for failed operations

For detailed documentation, see: `/documentation/ml-server/humansa-agent-system.md`

## Test Dashboard System

A comprehensive web-based testing framework for the ML Server:

### Overview
- **Purpose**: Centralized test execution, monitoring, and analysis
- **Architecture**: FastAPI backend (port 6002) + React frontend
- **Database**: Uses same PostgreSQL instance as ML server

### Key Features

#### Multi-Instance Support
- **Instance Pool**: Manages ML server instances (ports 6001-6009)
- **Parallel Execution**: Run tests concurrently across multiple instances
- **Isolated Databases**: Each instance uses separate test database (test1-test9)
- **Automatic Scaling**: Spins up/down instances based on workload

#### Test Management
- **JSON Test Definitions**: Standardized test format with expectations
- **Test Suites**: Organized by functionality (appointment, medical, product, etc.)
- **Real-time Monitoring**: WebSocket-based live updates
- **Comprehensive Logging**: Captures ML server logs per test execution

#### Results Analysis
- **Hierarchical View**: Jobs → Runs → Suites → Tests → Logs
- **Performance Metrics**: Response times, success rates, trends
- **Export Capabilities**: PDF/CSV reports for sharing
- **Failure Analysis**: Detailed error tracking and debugging

### Usage
```bash
# Start dashboard
cd test_dashboard
./launch_dashboard.sh

# Access UI
http://localhost:6002

# Start with multi-instance support
./launch_multi_instance.sh
```

### Test Format Example
```json
{
  "id": "TEST_001",
  "name": "Test appointment booking",
  "execution": {
    "endpoint": "/v2/humansa/responses/create",
    "payload": {"input": "Book appointment with Dr. Li"}
  },
  "expectations": {
    "response": {
      "output_contains": ["appointment", "Dr. Li"],
      "status_code": 200
    }
  }
}
```

For detailed documentation, see: `/documentation/ml-server/test-dashboard.md`

## Important Notes

1. **Two Systems, One Server**: Both YouWoAI and Humansa systems run on the same port
2. **Test Environment**: Complete isolated environment with test database on port 5454
3. **Test Server**: Always use port 5002 for testing, never 5001
4. **Virtual Environment**: CRITICAL - Always activate before any Python work
5. **Requirements.txt**: MUST be updated after ANY pip install
6. **Streaming Formats**: 
   - Chat completions: Simple SSE with text deltas
   - Multi-agent: Complex output items with envelope pattern
7. **Agent Independence**: Agents are modular but share infrastructure modules
8. **Error Handling**: Always return proper error responses with status codes

Remember: Good logging, proper async handling, and comprehensive testing make debugging much easier!