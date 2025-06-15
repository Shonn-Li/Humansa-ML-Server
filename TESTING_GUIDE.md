# Testing Guide for YouWoAI ML Server

## Recommended Test Files

### Primary Test (Recommended)

- **`test_enhanced_api.py`** - Comprehensive API testing
  - ✅ Health endpoint
  - ✅ Models listing
  - ✅ All 5 LLM providers (OpenAI, Anthropic, DeepSeek, Gemini, xAI/Grok)
  - ✅ Clear pass/fail reporting
  - ✅ Environment setup instructions

### Quick Validation

- **`test_startup.py`** - Basic server startup validation
  - ✅ Import testing
  - ✅ Configuration checking
  - ✅ Provider availability

## Optional Test Files

### Extended Feature Testing

- **`test_api_client.py`** - More comprehensive feature testing
  - Tests streaming responses
  - Tests web search integration
  - Tests file attachments
  - Tests both `/v1/chat/completions` and `/v1/chat` endpoints
  - Note: Some features may not be fully implemented

### Direct Module Testing

- **`test_enhanced_chat.py`** - Direct module testing (async-based)
  - Tests enhanced_chat_bot module directly
  - More complex setup
  - Useful for debugging internal functionality

## Testing Workflow

### 1. Quick Check

```bash
python test_startup.py
```

### 2. Comprehensive API Testing

```bash
python test_enhanced_api.py
```

### 3. Extended Feature Testing (Optional)

```bash
python test_api_client.py
```

## Environment Setup for Full Testing

```bash
# Core providers
export OPENAI_API_KEY=your_openai_key

# Optional providers
export ANTHROPIC_API_KEY=your_anthropic_key
export DEEPSEEK_API_KEY=your_deepseek_key
export XAI_API_KEY=your_xai_key
export GOOGLE_API_KEY=your_google_key

# Optional features (for test_api_client.py)
export SERPER_API_KEY=your_serper_key      # For web search
export SPIDER_API_KEY=your_spider_key      # For link analysis
```

## Test Coverage Summary

| Feature            | test_enhanced_api.py | test_startup.py | test_api_client.py | test_enhanced_chat.py |
| ------------------ | -------------------- | --------------- | ------------------ | --------------------- |
| Health Check       | ✅                   | ✅              | ✅                 | ❌                    |
| Model Listing      | ✅                   | ✅              | ✅                 | ✅                    |
| OpenAI Provider    | ✅                   | ❌              | ✅                 | ✅                    |
| Anthropic Provider | ✅                   | ❌              | ❌                 | ✅                    |
| DeepSeek Provider  | ✅                   | ❌              | ❌                 | ✅                    |
| Gemini Provider    | ✅                   | ❌              | ❌                 | ✅                    |
| xAI Provider       | ✅                   | ❌              | ❌                 | ✅                    |
| Streaming          | ❌                   | ❌              | ✅                 | ✅                    |
| Web Search         | ❌                   | ❌              | ✅                 | ✅                    |
| File Attachments   | ❌                   | ❌              | ✅                 | ✅                    |
| Error Handling     | ✅                   | ✅              | ✅                 | ✅                    |

## Recommendations

1. **For regular testing**: Use `test_enhanced_api.py`
2. **For quick validation**: Use `test_startup.py`
3. **For advanced features**: Use `test_api_client.py` (optional)
4. **For module debugging**: Use `test_enhanced_chat.py` (advanced users)

The `test_enhanced_api.py` provides the best balance of comprehensive coverage and reliability.
