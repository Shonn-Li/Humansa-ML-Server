# Humansa Documentation

Welcome to the Humansa medical AI system documentation. This directory contains all documentation related to the Humansa V2 multi-agent medical consultation platform.

## Directory Structure

### 📁 [research/](./research/)
Research documents, evaluations, and system design documentation.

- **[MEMORY_SYSTEMS_COMPARISON_RESEARCH.md](./research/MEMORY_SYSTEMS_COMPARISON_RESEARCH.md)** - Comprehensive comparison of state-of-the-art memory systems
- **[HUMANZA_USER_PROFILE_MEMORY_SYSTEM_RECOMMENDATIONS.md](./research/HUMANZA_USER_PROFILE_MEMORY_SYSTEM_RECOMMENDATIONS.md)** - Recommendations for Humanza memory system
- **[HUMANSA_V2_FLOW_DIAGRAM.md](./research/HUMANSA_V2_FLOW_DIAGRAM.md)** - System flow diagrams
- **[HUMANSA_V2_SIMPLE_FLOW.md](./research/HUMANSA_V2_SIMPLE_FLOW.md)** - Simplified flow documentation
- **HUMANSA_V2_*EVALUATION*.md** - Various evaluation reports

### 📁 [implementations/](./implementations/)
Current implementation details, fixes, and improvements.

- **[HUMANSA_WORKING_SOLUTION.md](./implementations/HUMANSA_WORKING_SOLUTION.md)** - Current working implementation
- **[HUMANSA_IMPROVEMENTS.md](./implementations/HUMANSA_IMPROVEMENTS.md)** - Implemented improvements
- **HUMANSA_FIXES_*.md** - Various bug fixes and solutions

### 📁 [to-be-implemented/](./to-be-implemented/)
Future features and implementations waiting to be developed.

- **[HUMANZA_MEMORY_IMPLEMENTATION_GUIDE.md](./to-be-implemented/HUMANZA_MEMORY_IMPLEMENTATION_GUIDE.md)** - Detailed implementation guide for enhanced memory system

### 📁 [guides/](./guides/)
Testing guides, setup instructions, and operational documentation.

- **HUMANSA_TEST_*.md** - Various testing guides and results
- **humansa_test_output_*.md** - Test execution outputs
- **Test environment setup and validation guides**

## Quick Links

### For Developers
1. Start with [HUMANSA_WORKING_SOLUTION.md](./implementations/HUMANSA_WORKING_SOLUTION.md) to understand current implementation
2. Review [HUMANZA_MEMORY_IMPLEMENTATION_GUIDE.md](./to-be-implemented/HUMANZA_MEMORY_IMPLEMENTATION_GUIDE.md) for upcoming features
3. Check testing guides in the [guides/](./guides/) directory

### For Researchers
1. Read [MEMORY_SYSTEMS_COMPARISON_RESEARCH.md](./research/MEMORY_SYSTEMS_COMPARISON_RESEARCH.md) for memory system analysis
2. Review evaluation reports in [research/](./research/) directory
3. Study flow diagrams for system architecture

### For Operations
1. Follow setup guides in [guides/](./guides/) directory
2. Review test validation results
3. Check implementation fixes documentation

## Key Features

### Current Implementation
- Multi-agent medical consultation system
- LlamaIndex-based architecture
- PostgreSQL storage with patient profiles
- Basic conversation history tracking
- Tool-calling capabilities for medical queries

### Proposed Memory Enhancement
- Hierarchical memory system (short/mid/long-term)
- Intelligent entity extraction
- Temporal knowledge graphs
- Advanced profile building
- Semantic memory retrieval

## Related Components

- **Main Server**: `/src/humansa/`
- **V2 Implementation**: `/src/humansa/v2/`
- **Testing**: `/test/test_humansa_*.py`
- **Configuration**: Various SQL and setup scripts

## Contributing

When adding new documentation:
1. Place research and design docs in `research/`
2. Implementation details go in `implementations/`
3. Future features in `to-be-implemented/`
4. Operational guides in `guides/`
5. Update this README with new additions

## Version History

- **V2**: Current multi-agent system with LlamaIndex
- **V2 Enhanced** (Proposed): Advanced memory system with profile building
- See individual documents for detailed version information