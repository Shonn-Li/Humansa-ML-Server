# Quick Test Reference

## 🚀 Quick Start Testing

### Connect to Test Database
```bash
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d youwoai_test
```

### Verify Everything is Loaded
```bash
python scripts/verify_setup.py
```

## 📊 Test Data at a Glance

### Research Papers (Technical Deep Dives)
- **Note 10001**: PARL - Making AI predictable
- **Note 10002**: G1 - Teaching LLMs about graphs  
- **Note 10003**: Game theory + resource allocation

### Startup Content (Business Insights)
- **Note 10004**: AI startup opportunities
- **Note 10005**: Zepto's 10-min delivery
- **Note 10006**: Replit's growth to $100M
- **Note 10007**: Andrew Ng's AI advice

### Platform Content (Multi-language)
- **Note 10008**: YouWoAI intro (Chinese doc)
- **Note 10009**: Product demo (Chinese audio)

## 🧪 Quick Test Scenarios

### Test Semantic Search
```sql
-- Find notes about "reinforcement learning"
SELECT n.id, n."noteTitle", COUNT(e.id) as matching_chunks
FROM note_v1 n
JOIN embedding_v1 e ON e.type_id = n.id
WHERE e.chunk_text ILIKE '%reinforcement learning%'
GROUP BY n.id, n."noteTitle";
```

### Test Multi-language
1. Ask about Note 10008 in Chinese
2. Ask about Note 10009 in English
3. Mix languages in one query

### Test Technical Understanding
- "What's the difference between PARL and G1?"
- "How does Zepto achieve 10-minute delivery?"
- "Explain Andrew Ng's data-centric AI approach"

### Test Conversation Context
1. Start with a simple question about any note
2. Ask a follow-up that requires context
3. Change topic and see if it adapts

### Test Cross-Note Synthesis
- "Which startup would benefit from PARL's predictable AI?"
- "How could G1's graph reasoning help Zepto?"
- "Compare all the AI implementation approaches mentioned"

## 📈 Metrics to Track

1. **Response Time**: How fast are queries answered?
2. **Retrieval Accuracy**: Right chunks being used?
3. **Answer Quality**: Accurate and complete?
4. **Language Handling**: Smooth bilingual support?
5. **Context Retention**: Remembers conversation?

## 🔍 Common Issues to Check

- [ ] Chinese characters display correctly
- [ ] Long technical papers summarized well
- [ ] YouTube transcripts parsed properly
- [ ] Cross-note queries find all relevant info
- [ ] Conversations maintain context
- [ ] Embeddings return similar content

## 💡 Pro Testing Tips

1. **Start Simple**: Basic queries before complex ones
2. **Mix Content Types**: PDFs → YouTube → Audio
3. **Test Edge Cases**: Very long queries, mixed languages
4. **Check Consistency**: Same question, different phrasings
5. **Verify Sources**: Does it cite the right notes?

## 🛠️ Useful SQL Queries

### Check Note Distribution
```sql
SELECT 
  f."folderTitle",
  COUNT(n.id) as note_count,
  COUNT(DISTINCT n.notetype) as content_types
FROM folder_v1 f
LEFT JOIN note_v1 n ON n."folderId" = f.id
GROUP BY f.id, f."folderTitle";
```

### Find Conversations by Topic
```sql
SELECT 
  c.title,
  n."noteTitle",
  jsonb_array_length(c.messages) as messages
FROM conversation_v1 c
JOIN note_v1 n ON c.typeid = n.id
WHERE c.messages::text ILIKE '%AI%'
ORDER BY messages DESC;
```

### Embedding Statistics
```sql
SELECT 
  n."noteTitle",
  COUNT(e.id) as chunks,
  AVG(length(e.chunk_text)) as avg_chunk_size
FROM note_v1 n
JOIN embedding_v1 e ON e.type_id = n.id
GROUP BY n.id, n."noteTitle"
ORDER BY chunks DESC;
```

## 🎯 Goal

Ensure the test environment accurately represents production capabilities while providing diverse content for comprehensive testing.