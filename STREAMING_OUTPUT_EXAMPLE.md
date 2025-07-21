# Streaming Output Format Example

## Complete Flow for Query with Attachment

**Query**: "Analyze this paper and provide citations"  
**Attachment**: https://arxiv.org/pdf/2311.10122.pdf

### Output Items in Order:

```
OUTPUT_ITEM 1: Reasoning (Router)
ID: router_e82b2a2d
Content: "Analyzing query and routing to appropriate agents...
         User has attached a PDF file that needs to be processed.
         Query routed to agents: attachment, rag, response, citation"

OUTPUT_ITEM 2: Function Tool Call (Attachment Processing)
ID: fc_582bc514
Type: function_tool_call
Tool: process_attachment
Input: {"url": "https://arxiv.org/pdf/2311.10122.pdf"}
Status: in_progress → completed
Result: "Extracted 15 pages of content about reinforcement learning..."

OUTPUT_ITEM 3: File Search Call (RAG)
ID: fs_88816c73
Type: file_search_call
Query: "reinforcement learning PARL paper"
Status: in_progress → completed
Results: 3 relevant documents found

OUTPUT_ITEM 4: Reasoning (Response Planning)
ID: resp_planning_123
Content: "Combining attachment content with RAG results to create comprehensive response..."

OUTPUT_ITEM 5: Message (Main Response)
ID: msg_4df9fcf4
Type: message
Content: "Based on my analysis of the provided paper [1], here are the key points about reinforcement learning:

1. The paper introduces a new framework called PARL (Policy-Aware Reinforcement Learning) that addresses...

2. Key contributions include [2]:
   - Novel policy gradient estimation method
   - Improved sample efficiency by 45%
   - Better generalization across environments

3. The experimental results demonstrate [3]...

[Continues with full response content]"

OUTPUT_ITEM 6: Reasoning (Citation)
ID: cit_239bf95d
Content: "Adding citations and formatting references...
         Found 4 citation points in the response.
         Formatting sources list..."

OUTPUT_ITEM 7: Content Part (Citation Addition)
Type: content_part
Content: "

Sources:
[1] Provided document - https://arxiv.org/pdf/2311.10122.pdf
[2] Zhang et al., 'PARL: Policy-Aware Reinforcement Learning', 2023, Section 3.2
[3] Experimental Results, Table 2, p. 8
[4] Personal notes on PARL framework (retrieved from knowledge base)"
```

### Final Metadata:
```json
{
  "agent_results": {
    "router_agent": {
      "status": "success",
      "data": {
        "decision": "multi_agent",
        "agents_selected": ["attachment", "rag", "response", "citation"]
      }
    },
    "attachment_agent": {
      "status": "success", 
      "data": {
        "files_processed": 1,
        "content_length": 45000,
        "extraction_time": 2.3
      }
    },
    "rag_agent": {
      "status": "success",
      "data": {
        "documents_found": 3,
        "relevance_scores": [0.92, 0.87, 0.81]
      }
    },
    "response_agent": {
      "status": "success",
      "data": {
        "model_used": "gpt-4o-mini",
        "tokens_generated": 850
      }
    },
    "citation_agent": {
      "status": "success",
      "data": {
        "citations_added": 4,
        "citation_style": "numbered"
      }
    }
  },
  "workflow_time": 8.45,
  "total_tokens": 2150
}
```

## Output Item Types Summary

### 1. **Reasoning Items**
- Show agent thinking/decision process
- IDs: `router_xxx`, `cit_xxx`, `resp_planning_xxx`
- Content: Text explaining what the agent is doing

### 2. **Tool Call Items**
- **Function Tool Call**: Generic tools including attachment processing
- **File Search Call**: RAG/knowledge base searches  
- **Web Search Call**: Internet searches
- IDs: `fc_xxx`, `fs_xxx`, `ws_xxx`

### 3. **Message Items**
- The actual response content
- IDs: `msg_xxx`
- Contains the main answer to the user

### 4. **Content Parts**
- Additional content like citations
- Added by citation agent
- Appended to the main response

## Testing This Flow

```bash
# Run the quick single test
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python tests/quick_test_single.py

# View the generated log
cat test_logs/*/Attachment_Test_Example_readable.txt
```

This will show you the exact output items and flow for your specific test case.