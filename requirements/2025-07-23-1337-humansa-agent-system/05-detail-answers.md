# Expert Answers - Humansa Agent System

## Phase 2: Technical Implementation Answers

### Q1: Should the v2 system continue using LlamaIndex's ReActAgent pattern rather than building a custom orchestrator from scratch?
**Answer: YES**
- Use ReActAgent but implement multi-agent workflow
- Reference: https://docs.llamaindex.ai/en/stable/understanding/agent/multi_agent/

### Q2: Should the new user memory system be stored in the existing conversation_v1 table structure rather than creating entirely new tables?
**Answer: YES**
- Use conversation_v1 with user ID
- Create additional patient info table for medical-specific data
- Use existing tables for test environment

### Q3: Should the mock appointment API follow the exact same database schema as the existing humansa_schedule table?
**Answer: YES**
- Use existing table schemas for consistency
- Set up same table types in test environment

### Q4: Should the new RAG processor integrate with the existing RAGProcessor class rather than creating a separate medical document processor?
**Answer: NO**
- Copy and modify existing RAGProcessor
- New version won't support note-related RAG for Humansa
- Focus on medical document processing

### Q5: Should the test environment database on port 5003 use a completely separate PostgreSQL instance?
**Answer: YES**
- Completely separate, initializable, non-dependent PostgreSQL instance
- Similar to existing youwoai_test setup