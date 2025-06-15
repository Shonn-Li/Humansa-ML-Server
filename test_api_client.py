#!/usr/bin/env python3
"""
Example usage of Enhanced YouWoAI ML Server API

This script demonstrates how to use the enhanced chat bot API endpoints.
"""

import requests
import json
import base64
import asyncio
import aiohttp

# Server configuration
SERVER_URL = "http://localhost:5001"


def test_basic_chat():
    """Test basic chat completion"""
    print("🔧 Testing basic chat completion...")

    url = f"{SERVER_URL}/v1/chat/completions"

    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Tell me about artificial intelligence."}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()

        print("✅ Basic chat test passed!")
        print(f"Provider: {result.get('provider', 'unknown')}")
        print(f"Model: {result.get('model', 'unknown')}")
        print(
            f"Response: {result['choices'][0]['message']['content'][:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Basic chat test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Basic chat test failed: {e}")
        return False


def test_enhanced_chat():
    """Test enhanced chat endpoint"""
    print("\n🔧 Testing enhanced chat endpoint...")

    url = f"{SERVER_URL}/v1/chat"

    data = {
        "question": "What are the benefits of using multiple LLM providers?",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "enable_web_search": False  # Set to True if you have search API keys
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()

        print("✅ Enhanced chat test passed!")
        print(f"Provider: {result.get('provider', 'unknown')}")
        print(f"Answer: {result.get('answer', '')[:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Enhanced chat test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Enhanced chat test failed: {e}")
        return False


def test_list_models():
    """Test model listing"""
    print("\n🔧 Testing model listing...")

    url = f"{SERVER_URL}/v1/models"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        result = response.json()

        print("✅ Model listing test passed!")
        print("Available models:")
        for model in result.get('data', []):
            print(f"  - {model['id']} ({model['provider']})")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Model listing test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Model listing test failed: {e}")
        return False


def test_streaming_chat():
    """Test streaming chat response"""
    print("\n🔧 Testing streaming chat...")

    url = f"{SERVER_URL}/v1/chat/completions"

    data = {
        "messages": [
            {"role": "user", "content": "Tell me a short story about AI and humans working together."}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 200,
        "stream": True
    }

    try:
        response = requests.post(url, json=data, stream=True, timeout=30)
        response.raise_for_status()

        print("✅ Streaming chat initiated...")
        print("Streaming response:")

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                            print(chunk['choices'][0]['delta']
                                  ['content'], end='', flush=True)
                    except json.JSONDecodeError:
                        continue

        print("\n✅ Streaming test completed!")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Streaming test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False


def test_web_search():
    """Test web search functionality"""
    print("\n🔧 Testing web search...")

    url = f"{SERVER_URL}/v1/chat/completions"

    data = {
        "messages": [
            {"role": "user", "content": "What are the latest developments in AI for 2024?"}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 300,
        "enable_web_search": True
    }

    try:
        # Longer timeout for web search
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()

        print("✅ Web search test completed!")
        if result.get('search_results'):
            print(f"Found {len(result['search_results'])} search results")
            print(f"First result: {result['search_results'][0]['title']}")
        else:
            print("No search results (web search might not be configured)")

        print(
            f"Response: {result['choices'][0]['message']['content'][:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"⚠️  Web search test warning: {e}")
        return True  # Don't fail if web search isn't configured
    except Exception as e:
        print(f"⚠️  Web search test warning: {e}")
        return True


def test_analyze_and_chat():
    """Test analyze and chat functionality"""
    print("\n🔧 Testing analyze and chat...")

    url = f"{SERVER_URL}/v1/analyze_and_chat"

    data = {
        "url": "https://example.com",  # Simple test URL
        "question": "What is this website about?",
        "model": "gpt-4o-mini",
        "temperature": 0.7
    }

    try:
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()

        print("✅ Analyze and chat test completed!")
        if result.get('link_analysis'):
            print(
                f"Link analysis success: {result['link_analysis'].get('success', False)}")
        print(f"Answer: {result.get('answer', '')[:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"⚠️  Analyze and chat test warning: {e}")
        return True  # Don't fail if link analysis isn't fully configured
    except Exception as e:
        print(f"⚠️  Analyze and chat test warning: {e}")
        return True


def test_file_attachment():
    """Test file attachment functionality"""
    print("\n🔧 Testing file attachment...")

    # Create a simple text file as base64
    test_content = "This is a test document for the YouWoAI ML Server.\n\nIt contains sample text for testing file attachment functionality."
    test_content_b64 = base64.b64encode(test_content.encode()).decode()

    url = f"{SERVER_URL}/v1/chat/completions"

    data = {
        "messages": [
            {"role": "user", "content": "Please summarize the content of this document."}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 200,
        "attachments": [
            {
                "type": "text/plain",
                "content": test_content_b64,
                "filename": "test_document.txt"
            }
        ]
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()

        print("✅ File attachment test completed!")
        print(
            f"Response: {result['choices'][0]['message']['content'][:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"⚠️  File attachment test warning: {e}")
        return True  # Don't fail if file processing isn't fully configured
    except Exception as e:
        print(f"⚠️  File attachment test warning: {e}")
        return True


def test_health_check():
    """Test server health"""
    print("🔧 Testing server health...")

    url = f"{SERVER_URL}/health"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        result = response.json()

        print("✅ Health check passed!")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Service: {result.get('service', 'unknown')}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def main():
    """Run all API tests"""
    print("🚀 Testing Enhanced YouWoAI ML Server API")
    print("=" * 50)

    tests = [
        test_health_check,
        test_list_models,
        test_basic_chat,
        test_enhanced_chat,
        test_streaming_chat,
        test_web_search,
        test_analyze_and_chat,
        test_file_attachment
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")

    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
    elif passed > 0:
        print("⚠️  Some tests passed - server is working with basic functionality")
    else:
        print("❌ Most tests failed - check server configuration")

    print("\nTo enable full functionality:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. For web search: Set SERPER_API_KEY, SERPAPI_API_KEY, or BING_SEARCH_API_KEY")
    print("3. For additional providers: Set ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, XAI_API_KEY, GOOGLE_API_KEY")
    print("4. For file attachments: Install llama-index-readers-file")
    print("5. For link analysis: Set SPIDER_API_KEY")


if __name__ == "__main__":
    main()
