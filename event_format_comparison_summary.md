## Event Format Comparison: O3 Demo vs Regular Humansa

### Test Case

**Message**: "帮我预约个最近一周的医生，要在深圳的，专科是心血管科"

### Key Differences

#### 1. Event Volume

- **O3 Demo**: 6 events total
- **Regular Humansa**: 45 events total

#### 2. Output Items

- **O3 Demo**: 2 output items (1 reasoning, 1 message)
- **Regular Humansa**: 7 output items (6 reasoning, 1 message)

#### 3. Event Structure Differences

**O3 Demo Events:**

- Uses `"event"` field for event type
- Simpler structure with fewer fields
- Example: `{"event": "response.created", "sequence_number": 0, "response": {...}}`

**Regular Humansa Events:**

- Uses `"type"` field for event type
- Includes additional `agentic_mode` and `agentic_metadata` fields
- Example: `{"type": "response.created", "sequence_number": 0, "response": {...}, "agentic_mode": true, "agentic_metadata": {...}}`

#### 4. Output Item Structure

**O3 Demo Output Items:**
✅ **HAVE `status` field**:

```json
{
  "id": "rs_ac2c7507",
  "type": "reasoning",
  "status": "completed",  // ✅ Present
  "content": [...]
}
```

**Regular Humansa Output Items:**
❌ **MISSING `status` field**:

```json
{
  "id": "rs_a09ac31d",
  "type": "reasoning",
  // ❌ No status field
  "content": [...]
}
```

#### 5. Reasoning Content

- **O3 Demo**: Single reasoning item with comprehensive content
- **Regular Humansa**: Multiple reasoning items with step-by-step content

#### 6. Message Content

Both formats have similar message structure:

```json
{
  "id": "msg_xxx",
  "type": "message",
  "role": "assistant",
  "status": "completed",
  "content": [
    {
      "type": "output_text",
      "text": "...",
      "annotations": []
    }
  ]
}
```

### Validation Issues

- **O3 Demo**: All output items have required `status` field ✅
- **Regular Humansa**: Reasoning items missing `status` field ❌

### Conclusion

The main format difference is that **Regular Humansa reasoning items are missing the `status` field**, which causes validation failures. Otherwise, both formats follow the same basic structure with `id`, `type`, and `content` fields.

The backend should handle both formats, but Regular Humansa needs to add the `status: "completed"` field to reasoning items to be fully compliant.
