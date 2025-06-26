# YouWoAI ML Server - Enhanced Edition

This is an **enhanced** machine learning inference server built with [Quart](https://pgjones.gitlab.io/quart/) and [LlamaIndex](https://github.com/jerryjliu/llama_index).

## 🚀 New Features

- **🤖 Multiple LLM Providers**: OpenAI, Anthropic, DeepSeek, xAI, Gemini
- **🔌 OpenAI-Compatible API**: Drop-in replacement for OpenAI API
- **🔍 Web Search Integration**: Real-time search with Serper/SerpAPI/Bing
- **📎 File Attachments**: PDF and image analysis support
- **⚡ Streaming Responses**: Real-time response streaming
- **📝 Note Context**: Integration with YouWoAI note system
- **🔗 Link Analysis**: YouTube, Bilibili, web content analysis

## One liner startup

```bash
python3 -m venv youwo-ml-venv && source youwo-ml-venv/bin/activate &&python -m src.main
```

## 🔧 Setup (Local Development)

### 1. Create and activate virtual environment

```bash
python3 -m venv youwo-ml-venv
source youwo-ml-venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file or set these environment variables:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional - Additional LLM providers
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
XAI_API_KEY=your_xai_api_key
GOOGLE_API_KEY=your_google_api_key  # For Gemini

# Optional - Web search (choose one)
SERPER_API_KEY=your_serper_api_key
SERPAPI_API_KEY=your_serpapi_api_key
BING_SEARCH_API_KEY=your_bing_api_key

# Database configuration
DB_HOST=your_db_host
DB_PORT=5432
DB_USERNAME=your_db_username
DB_ACTIVE_DATABASE=your_db_name
```

### 4. Run the server

```bash
source youwo-ml-venv/bin/activate
python src/main.py
# Server runs on port 5001 by default
```

### 5. Test the server

```bash
# Test all providers and functionality
python test_enhanced_api.py

# Quick startup validation
python test_startup.py

# Test health endpoint directly
curl http://localhost:5001/health

# Test chat completion directly
curl -X POST http://localhost:5001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## 📚 API Documentation

- **[Enhanced API Documentation](ENHANCED_API_DOCUMENTATION.md)** - Complete API reference
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Technical details and setup guide
- **[Original API Documentation](API_DOCUMENTATION.md)** - Link analysis features

## 🎯 Quick API Examples

### Basic Chat

```bash
curl -X POST http://localhost:5001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "gpt-4o"
  }'
```

### Chat with Web Search

```bash
curl -X POST http://localhost:5001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Latest AI news?"}],
    "enable_web_search": true
  }'
```

### Chat with Note Context

```bash
curl -X POST http://localhost:5001/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are my travel plans?",
    "note_ids": [1, 2, 3, 4, 5]
  }'
```

### Streaming Response

```bash
curl -X POST http://localhost:5001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'
```

## 🔄 Backward Compatibility

All existing endpoints remain functional:

- `/chat_bot` - Original chat bot
- `/analyze_link` - Link analysis
- `/get_related_notes` - Note retrieval
- `/health` - Health check

## 🏗️ Architecture

```
Frontend/Backend → ML Server (Port 5001)
                    ├── Multiple LLM Providers
                    ├── Web Search APIs
                    ├── File Processing
                    ├── Note Database
                    └── Link Analysis
```

### 🐳 Running with Docker

```bashz
# 1. Build the Docker image
docker build -t youwo-ml-server .

# 2. Run with environment variables
docker run -p 5001:5001 \
  -e OPENAI_API_KEY=your_key \
  -e DB_HOST=your_db_host \
  youwo-ml-server
```

## 🔧 Development

### Running Tests

```bash
source youwo-ml-venv/bin/activate

# Comprehensive API testing (recommended)
python test_enhanced_api.py

# Quick startup validation
python test_startup.py
```

### Adding New Providers

1. Add API key to environment variables
2. Update `enhanced_chat_bot.py` provider configuration
3. Test with the new provider

### File Upload Architecture

- **Recommended**: Use S3 URLs for file attachments
- **Alternative**: Base64 encoding for small files
- See [Enhanced API Documentation](ENHANCED_API_DOCUMENTATION.md) for details

## 🚀 Deployment

The enhanced server is designed for production deployment with:

- Auto-scaling LLM provider selection
- Robust error handling and fallbacks
- Comprehensive monitoring and logging
- Docker containerization support
- AWS/cloud deployment ready

## 📊 Monitoring

The server provides detailed logging for:

- Token usage per provider
- Response times and performance
- Error rates and fallback usage
- Cost tracking across providers

## 🛠️ Troubleshooting

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **API key errors**: Check environment variables are set
3. **Database connection**: Verify DB credentials
4. **File processing**: Install `llama-index-readers-file` for PDF/image support

### Getting Help

1. Check the [Enhanced API Documentation](ENHANCED_API_DOCUMENTATION.md)
2. Run `python test_enhanced_api.py` to diagnose issues
3. Check server logs for detailed error messages
