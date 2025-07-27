# Debug Logs for Response Context

This directory contains debug logs for the Response Agent to help diagnose why responses might be generic instead of using the provided RAG context.

## Log Format

Each log file is named: `context_{user_id}_{conversation_id}_{timestamp}.json`

## Log Contents

Each JSON file contains:

1. **Request Information**
   - User messages
   - Model requested
   - Feature flags (enable_rag, enable_citations, enable_web_search)

2. **Context Summary**
   - Which agents provided context
   - Combined context length
   - Number of sources found
   - Preview of context (first 1000 chars)

3. **Detailed Context**
   - Full context from each agent (context_search, web_search, attachment)
   - Router decision
   - All sources with metadata

4. **Combined Context**
   - The full combined context string passed to the LLM
   - This is what the model actually sees

## How to Debug

1. **Check if context exists**: Look at `combined_context_length`. If it's 0, no context was found.

2. **Verify RAG search worked**: Check `context_search_found` and look at the `full_context.context_search` section.

3. **Check sources**: Look at `sources` array to see what documents were found.

4. **Review the actual context**: Check `combined_context_full` to see exactly what was passed to the LLM.

## Common Issues

1. **"I'm happy to help..." responses**: Usually means no context was found or passed.

2. **Empty context**: Check if:
   - Notes exist for the user
   - RAG search is finding relevant documents
   - Context is being properly formatted

3. **Wrong context**: Verify the search query matches user intent by checking router decision.

## Server Logs

Also check the main server logs for lines starting with:
- `🎯 RESPONSE AGENT` - Summary of context
- `⚠️ WARNING` - Validation warnings
- `💾 Debug context saved` - Location of debug file