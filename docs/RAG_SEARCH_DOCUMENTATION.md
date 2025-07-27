# RAG (Retrieval Augmented Generation) Search Documentation

## Overview
The YouWoAI RAG search system combines multiple search strategies to find relevant content from user's notes and conversations. It uses both traditional keyword search and semantic vector similarity search to provide comprehensive results.

## Architecture

### 1. **Router Agent** (`intelligent_router.py`)
- Analyzes user queries to determine which tools to use
- Routes queries to appropriate search agents (knowledge base, web search, etc.)
- Condenses queries for better search performance

### 2. **Context Search Agent** (`context_search_agent.py`)
- Main entry point for searching user's content
- Supports two search modes:
  - **Agentic RAG**: Multi-step intelligent search with query understanding
  - **Hybrid Search**: Direct combination of keyword and vector search

### 3. **Agentic RAG Processor** (`agentic_rag_processor.py`)
- Uses LLM to understand query intent
- Performs multi-step retrieval with different strategies:
  - **Temporal search**: Find recent or time-specific content
  - **Keyword search**: Traditional text matching
  - **Semantic search**: Vector similarity using embeddings
  - **Query expansion**: Generate related search terms
- Iteratively refines search based on results

### 4. **Hybrid Search Engine** (`hybrid_search.py`)
- Combines keyword (BM25) and vector search results
- Configurable weighting between search methods
- Returns `HybridSearchResult` objects with:
  - `type_id`: Note or conversation ID
  - `type`: "note" or "conversation"
  - `chunk_text`: The matching text snippet
  - `title`: Note/conversation title (if available)
  - `hybrid_score`: Combined relevance score

### 5. **RAG Processor** (`rag_processor.py`)
- Core vector search implementation
- Uses embeddings stored in PostgreSQL with pgvector
- Returns `ChunkResult` objects from `embedding_v1` table
- Includes metadata from the database

## Search Flow

### Standard Flow (Hybrid Search):
1. User query → Router determines to use knowledge base search
2. Context Search Agent receives query
3. Query is embedded using the embedding model
4. Parallel search:
   - **Keyword search**: Uses PostgreSQL full-text search on `chunk_tsv` column
   - **Vector search**: Uses pgvector similarity on `embedding` column
5. Results are combined with configurable weights (default: 0.3 keyword, 0.7 vector)
6. Top results are formatted with titles and metadata

### Agentic Flow (When Enabled):
1. User query → Router → Context Search Agent
2. Agentic RAG Processor analyzes query to understand:
   - Intent (search, summarize, question, etc.)
   - Time constraints (recent, last week, etc.)
   - Key concepts to search for
3. Multi-step retrieval:
   - Execute initial search strategy
   - Evaluate results quality
   - Determine if more searches needed
   - Try alternative strategies (expand query, different keywords)
4. Combine and deduplicate results
5. Return comprehensive results

## Database Schema

### `embedding_v1` Table:
- `section_id`: Unique chunk identifier
- `type_id`: ID of the source note/conversation
- `type`: "note" or "conversation"
- `chunk_text`: The actual text content
- `embedding`: Vector representation (1536 dimensions)
- `chunk_tsv`: Full-text search vector
- `metadata`: JSONB field containing title and other info

### `note_v1` Table:
- `id`: Note ID
- `noteTitle`: The actual title of the note
- `ownerId`: User ID who owns the note

## Title Resolution

The system attempts to get titles from multiple sources:

1. **From search results directly**:
   - `HybridSearchResult.title` (when using hybrid search)
   - `ChunkResult.metadata.title` (when using agentic RAG)

2. **From database join**:
   - During search, titles can be joined from `note_v1.noteTitle`

3. **Fallback**:
   - If no title found, displays "Note #ID"

## Configuration

### Search Weights (in `hybrid_search.py`):
```python
keyword_weight = 0.3  # Weight for BM25 keyword search
vector_weight = 0.7   # Weight for semantic similarity
```

### Search Limits:
- Default: 20 results per search
- Context window: Top 10 results sent to LLM
- Sources displayed: Top 10 results

## Common Issues

1. **"Note #ID" instead of titles**:
   - Occurs when embeddings don't have title in metadata
   - Or when hybrid search doesn't properly join with note table

2. **Empty search results**:
   - Check if user has notes with embeddings
   - Verify embedding generation is working
   - Check database connection and permissions

3. **Agentic processor failures**:
   - Usually due to LLM provider issues
   - Falls back to hybrid search automatically