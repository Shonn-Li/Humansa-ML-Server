# YouWoAI ML Server Documentation

This directory contains comprehensive documentation for the YouWoAI ML Server, including the multi-agent system, Humansa medical AI, and various technical guides.

## 📚 Documentation Structure

### 🏥 [Humansa Medical AI System](./humansa/)
Complete documentation for the Humansa V2 medical consultation platform.

- **[Research](./humansa/research/)** - Memory systems comparison, architecture analysis
- **[Implementations](./humansa/implementations/)** - Current working solutions
- **[To Be Implemented](./humansa/to-be-implemented/)** - Future memory system enhancements
- **[Guides](./humansa/guides/)** - Testing and operational guides
- **[Test Results](./humansa/test-results/)** - Test execution data

### 🤖 [Multi-Agent System](./agent/)
Documentation for the core multi-agent architecture.

- [Multi-Agent Modular Flow Diagram](./agent/YouWoAI_Multi_Agent_Modular_Flow_Diagram.md)
- [Multi-Agent Streaming V2 Diagram](./agent/YouWoAI_Multi_Agent_Streaming_V2_Diagram.md)

### 🛠️ Technical Documentation

- [Streaming Output Format Documentation](./STREAMING_OUTPUT_FORMAT_DOCUMENTATION.md)
- [Test Environment Setup](./TEST_ENVIRONMENT.md)
- [General Instructions](./instruction.md)

## Quick Navigation

### For New Developers
1. Start with [instruction.md](./instruction.md) for general setup
2. Review [Test Environment Setup](./TEST_ENVIRONMENT.md)
3. Explore the [Multi-Agent Flow Diagrams](./agent/)

### For Humansa Development
1. Read [Humansa README](./humansa/README.md)
2. Review [Current Implementation](./humansa/implementations/HUMANSA_WORKING_SOLUTION.md)
3. Study [Memory System Research](./humansa/research/MEMORY_SYSTEMS_COMPARISON_RESEARCH.md)

### For Testing
1. Follow [Test Environment Guide](./TEST_ENVIRONMENT.md)
2. Check [Humansa Test Guides](./humansa/guides/)
3. Review [Test Results](./humansa/test-results/)

## Key Features Documented

### Multi-Agent System
- Router Agent for intelligent request routing
- RAG Agent for retrieval-augmented generation
- Web Search Agent for external information
- Citation Agent for source attribution
- Streaming response generation

### Humansa Medical AI
- Multi-agent medical consultation
- Patient profile management
- Conversation history tracking
- Tool-calling for medical queries
- Proposed advanced memory system

### Infrastructure
- PostgreSQL with pgvector for embeddings
- Quart async web framework
- OpenAI-compatible API endpoints
- Docker deployment options

## Contributing to Documentation

When adding new documentation:
1. Place it in the appropriate subdirectory
2. Update relevant README files
3. Use clear, descriptive filenames
4. Include creation/update dates
5. Follow Markdown best practices

## Recent Updates

- **2024-01**: Added comprehensive memory system research
- **2024-01**: Organized Humansa documentation structure
- **2024-01**: Created memory implementation guides

## Need Help?

- Check [CLAUDE.md](../CLAUDE.md) for AI assistant guidance
- Review test files in `test/` directory
- Consult source code in `src/` for implementation details