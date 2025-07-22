# YouWoAI Test Data Guide

This guide provides detailed information about each note in the test environment, their content, and suggested testing scenarios.

## Test Notes Overview

| Note ID | Title | Type | Folder | Language | Content Focus |
|---------|-------|------|--------|----------|---------------|
| 10001 | 2311.18703v5.pdf | PDF | June-ML | English | Predictable RL agents |
| 10002 | 2505.18499v2.pdf | PDF | June-ML | English | Graph reasoning with LLMs |
| 10003 | 2505.06319v1.pdf | PDF | June-ML | English | Game theory + RL |
| 10004 | Startup Ideas You Can Now Build With AI | YouTube | Startup | English | AI startup opportunities |
| 10005 | How Zepto Became India's Fastest Growing Startup | YouTube | Startup | English | 10-minute delivery case study |
| 10006 | How Replit Went From $10M to $100M ARR | YouTube | Startup | English | SaaS growth strategies |
| 10007 | Andrew Ng: Building Faster with AI | YouTube | Startup | English | Practical AI implementation |
| 10008 | 欢迎来到由我AI.docx | Document | None | Chinese | YouWoAI platform introduction |
| 10009 | Product demo | Audio | None | Chinese | Product demo transcript |

## Detailed Note Descriptions

### 📄 Research Papers (June-ML Folder)

#### Note 10001: Predictability-Aware Reinforcement Learning (PARL)
- **Content**: Academic paper on making RL agents more predictable by minimizing trajectory entropy
- **Key Concepts**: Entropy rate, predictability vs performance trade-offs, safety in human-robot interaction
- **Testing Scenarios**:
  - Ask about entropy rate calculations
  - Query practical applications (robotics, autonomous driving)
  - Test understanding of trade-offs between predictability and optimal performance
  - Ask for implementation details (PAPPO, PASAC variants)

#### Note 10002: G1 - Graph Reasoning with LLMs
- **Content**: Research on improving LLMs' graph reasoning abilities through reinforcement learning
- **Key Concepts**: Erdős dataset, graph-theoretic tasks, zero-shot transfer, Group Relative Policy Optimization
- **Testing Scenarios**:
  - Ask about why LLMs struggle with graphs
  - Query about the Erdős dataset specifications
  - Test understanding of performance improvements (66.16% vs 47.16%)
  - Ask about real-world applications (Cora, PubMed networks)

#### Note 10003: RL for Game-Theoretic Resource Allocation
- **Content**: Using RL to solve Colonel Blotto games on graphs with resource allocation constraints
- **Key Concepts**: Multi-step Colonel Blotto Game (MCBG), action-displacement adjacency matrix, DQN/PPO
- **Testing Scenarios**:
  - Ask to explain Colonel Blotto game
  - Query about handling dynamic action spaces
  - Test understanding of symmetric vs asymmetric scenarios
  - Ask about practical applications (cybersecurity, market competition)

### 🎥 YouTube Videos (Startup Folder)

#### Note 10004: AI Startup Ideas
- **Content**: Discussion on new startup opportunities enabled by AI/LLMs
- **Key Concepts**: AI-native recruiting, personalized tutoring, full-stack service companies, infrastructure tooling
- **Testing Scenarios**:
  - Ask for specific startup examples mentioned
  - Query about why traditional lean startup doesn't apply
  - Test understanding of distribution vs technical moats
  - Ask about the "idea maze" concept

#### Note 10005: Zepto's Growth Story
- **Content**: Case study of India's fastest-growing grocery delivery startup
- **Key Concepts**: 10-minute delivery, dark store model, operational excellence, COVID timing
- **Testing Scenarios**:
  - Ask about Zepto's key success factors
  - Query about the dark store model
  - Test understanding of operational challenges
  - Ask for lessons for other startups

#### Note 10006: Replit's $100M ARR Journey
- **Content**: How Replit grew from $10M to $100M annual recurring revenue
- **Key Concepts**: AI integration, community building, education market, viral features, platform evolution
- **Testing Scenarios**:
  - Ask about key growth drivers
  - Query about B2B SaaS lessons
  - Test understanding of freemium strategy
  - Ask about community as a moat

#### Note 10007: Andrew Ng on Building with AI
- **Content**: Practical advice on implementing AI in projects and organizations
- **Key Concepts**: Iterative development, data-centric AI, pilot projects, deployment focus
- **Testing Scenarios**:
  - Ask for his main principles
  - Query about getting teams started with AI
  - Test understanding of build vs buy decisions
  - Ask about measuring AI project success

### 📝 Documents

#### Note 10008: YouWoAI Welcome Document (Chinese)
- **Content**: Platform introduction and features overview in Chinese
- **Key Concepts**: Multi-modal support, intelligent conversations, knowledge management, cross-platform
- **Testing Scenarios**:
  - Ask questions in Chinese about platform features
  - Test bilingual responses (Chinese question, English answer)
  - Query about specific functionality
  - Test understanding of user benefits

#### Note 10009: Product Demo (Audio)
- **Content**: Chinese audio transcript of YouWoAI product demonstration
- **Key Concepts**: Voice-to-text, intelligent Q&A, multi-language support, note management
- **Testing Scenarios**:
  - Ask about demo highlights in Chinese
  - Query about target users
  - Test understanding of voice transcription features
  - Ask about competitive advantages

## Testing Strategies by Feature

### 1. **Multi-Language Testing**
- Use Notes 10008 & 10009 for Chinese language processing
- Test code-switching between English and Chinese
- Verify proper handling of Chinese characters in responses

### 2. **Technical Depth Testing**
- Use Notes 10001-10003 for complex technical queries
- Test understanding of mathematical concepts
- Verify accurate summarization of research findings

### 3. **Business/Practical Testing**
- Use Notes 10004-10007 for business insights
- Test extraction of actionable advice
- Verify understanding of market dynamics

### 4. **Cross-Note Testing**
- Ask questions that require information from multiple notes
- Test semantic search across different note types
- Verify consistent quality across content types

### 5. **RAG (Retrieval Augmented Generation) Testing**
- Ask specific questions about details deep in the content
- Test the system's ability to find relevant chunks
- Verify citation/source attribution

### 6. **Conversation Context Testing**
- Build on previous questions in a conversation
- Test memory of earlier discussion points
- Verify coherent multi-turn dialogues

## Example Test Queries

### For Technical Notes:
```
"Compare the entropy minimization approach in PARL with the graph reasoning strategies in G1"
"How would PARL's predictability concepts apply to the Colonel Blotto game?"
"What are the computational complexity implications of the action-displacement adjacency matrix?"
```

### For Business Notes:
```
"What do Zepto and Replit have in common in their growth strategies?"
"How do Andrew Ng's AI principles apply to the startup ideas mentioned in the first video?"
"Which startup mentioned would benefit most from PARL's predictable AI agents?"
```

### For Chinese Content:
```
"用中文解释由我AI的核心优势"
"产品演示中提到了哪些关键功能？"
"How does YouWoAI compare to other note-taking apps? (test bilingual response)"
```

### For Cross-Content:
```
"Which research paper's concepts would be most useful for Zepto's logistics optimization?"
"How could G1's graph reasoning help with the resource allocation problems Replit might face?"
"给我推荐最适合学习AI创业的笔记" (Recommend notes for learning about AI startups)
```

## Embedding Coverage

Each note has multiple embeddings (chunks) for semantic search:
- Research papers: 33-53 embeddings each (detailed technical content)
- YouTube videos: 13-16 embeddings each (transcript segments)
- Documents: 1-5 embeddings (shorter content)

This enables testing of:
- Chunk-level retrieval accuracy
- Semantic similarity across different topics
- Context window management
- Relevance ranking

## Performance Benchmarks

When testing, consider measuring:
1. **Response Accuracy**: Does the answer correctly reflect the note content?
2. **Retrieval Precision**: Are the most relevant chunks being used?
3. **Language Handling**: Proper processing of English/Chinese/mixed queries
4. **Context Coherence**: Maintaining conversation context across turns
5. **Cross-Note Synthesis**: Ability to combine information from multiple sources

This test dataset provides comprehensive coverage for evaluating all major YouWoAI features and capabilities.