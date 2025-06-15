#!/usr/bin/env python3
"""
Test script for advanced features of the enhanced YouWoAI ML Server API
- Web search integration
- PDF file processing
- Link analysis (YouTube, Bilibili, web content)
- File attachments
- RAG/indexing
"""

import requests
import json
import time
import base64
import os
from pathlib import Path


def test_advanced_features():
    """Test advanced features like web search, file processing, and link analysis"""

    base_url = "http://localhost:5001"

    print("🧪 Testing YouWoAI Advanced Features")
    print("=" * 60)

    # Test 1: Web Search Feature
    print("\n1. Testing Web Search...")
    test_data = {
        "messages": [
            {
                "role": "user",
                "content": "What are the latest developments in AI transformers? Search the web for recent information."
            }
        ],
        "provider": "openai",
        "model": "gpt-4o",
        "enable_web_search": True,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions", json=test_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Web search test passed")
            if result.get('search_results'):
                print(
                    f"   Found {len(result['search_results'])} search results")
                for i, search_result in enumerate(result['search_results'][:3]):
                    print(
                        f"   - {search_result.get('title', 'Unknown')}: {search_result.get('url', 'No URL')}")
            else:
                print("⚠️ No search results returned (web search may not be configured)")
        else:
            print(f"❌ Web search test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Web search test failed: {e}")

    # Test 2: PDF File Processing (using base64 encoded content)
    print("\n2. Testing PDF File Processing...")

    # Create a simple test PDF content (this is just sample base64 - in real use you'd encode actual PDF)
    sample_pdf_content = "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwKL0xlbmd0aCAzIDAgUgo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooVGhpcyBpcyBhIHRlc3QgUERGIGRvY3VtZW50LikgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagoKMyAwIG9iago8PAovTGVuZ3RoIDI1Cj4+CnN0cmVhbQo3MiA3MjAgVGQKKFRlc3QgY29udGVudCkgVGoKZW5kc3RyZWFtCmVuZG9iagoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDUgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDYgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9Db250ZW50cyBbMiAwIFIgMyAwIFJdCj4+CmVuZG9iagoKNSAwIG9iago8PAovVHlwZSAvUGFnZXMKL0tpZHMgWzQgMCBSXQovQ291bnQgMQo+PgplbmRvYmoKCjYgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCj4+CmVuZG9iagoKNyAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgNSAwIFIKPj4KZW5kb2JqCgp4cmVmCjAgOAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA3NCAwMDAwMCBuIAowMDAwMDAwMTc5IDAwMDAwIG4gCjAwMDAwMDAyNzMgMDAwMDAgbiAKMDAwMDAwMDQ2NSAwMDAwMCBuIAowMDAwMDA0OTIgMDAwMDAgbiAKMDAwMDAwNTYwIDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgOAovUm9vdCA3IDAgUgo+PgpzdGFydHhyZWYKNjEwCiUlRU9G"

    test_data = {
        "messages": [
            {
                "role": "user",
                "content": "Please analyze this PDF document and summarize its content."
            }
        ],
        "provider": "openai",
        "model": "gpt-4o",
        "attachments": [
            {
                "type": "application/pdf",
                "content": sample_pdf_content,
                "filename": "test_document.pdf"
            }
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions", json=test_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ PDF processing test passed")
            print(
                f"   Response length: {len(result['choices'][0]['message']['content'])}")
        else:
            print(f"❌ PDF processing test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ PDF processing test failed: {e}")

    # Test 3: Link Analysis (YouTube)
    print("\n3. Testing Link Analysis (YouTube)...")

    test_data = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "question": "What is this video about? Summarize the main points.",
        "provider": "openai",
        "model": "gpt-4o"
    }

    try:
        response = requests.post(
            f"{base_url}/v1/analyze_and_chat", json=test_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ YouTube link analysis test passed")
            if result.get('link_analysis', {}).get('success'):
                print(
                    f"   Video title: {result['link_analysis']['data'].get('title', 'Unknown')}")
                print(f"   Platform: {result['link_analysis']['platform']}")
                print(
                    f"   Language: {result['link_analysis']['data'].get('language', 'Unknown')}")
            else:
                print("⚠️ Link analysis failed - transcript may not be available")
        else:
            print(
                f"❌ YouTube link analysis test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ YouTube link analysis test failed: {e}")

    # Test 4: Web Content Analysis
    print("\n4. Testing Web Content Analysis...")

    test_data = {
        "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "question": "What are the main topics covered in this article about AI?",
        "provider": "openai",
        "model": "gpt-4o",
        "platform": "web"
    }

    try:
        response = requests.post(
            f"{base_url}/v1/analyze_and_chat", json=test_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Web content analysis test passed")
            if result.get('link_analysis', {}).get('success'):
                print(
                    f"   Content extracted from: {result['link_analysis']['data'].get('url', 'Unknown')}")
                print(
                    f"   Content length: {len(result['link_analysis']['data'].get('content', ''))}")
            else:
                print(
                    "⚠️ Web content extraction failed - Spider API may not be configured")
        else:
            print(
                f"❌ Web content analysis test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Web content analysis test failed: {e}")

    # Test 5: Image Processing (if available)
    print("\n5. Testing Image Processing...")

    # Create a simple base64 encoded 1x1 PNG image for testing
    simple_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    test_data = {
        "messages": [
            {
                "role": "user",
                "content": "What do you see in this image?"
            }
        ],
        "provider": "openai",
        "model": "gpt-4o",
        "attachments": [
            {
                "type": "image/png",
                "content": simple_png_base64,
                "filename": "test_image.png"
            }
        ],
        "enable_image_analysis": True,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions", json=test_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Image processing test passed")
            print(
                f"   Response length: {len(result['choices'][0]['message']['content'])}")
        else:
            print(f"❌ Image processing test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Image processing test failed: {e}")

    # Test 6: Combined Features (Web Search + File Analysis)
    print("\n6. Testing Combined Features (Web Search + PDF)...")

    test_data = {
        "messages": [
            {
                "role": "user",
                "content": "Analyze this document and also search the web for related information about AI developments."
            }
        ],
        "provider": "openai",
        "model": "gpt-4o",
        "enable_web_search": True,
        "attachments": [
            {
                "type": "application/pdf",
                "content": sample_pdf_content,
                "filename": "ai_research.pdf"
            }
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions", json=test_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Combined features test passed")
            if result.get('search_results'):
                print(
                    f"   Web search results: {len(result['search_results'])}")
            print(f"   Response includes analysis of both document and web search")
        else:
            print(f"❌ Combined features test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Combined features test failed: {e}")

    # Test 7: Check Available Dependencies
    print("\n7. Checking Available Dependencies...")

    dependencies_to_check = [
        "requests",
        "beautifulsoup4",
        "llama-index-readers-file",
        "llama-index-readers-web",
        "youtube-transcript-api",
        "bilibili-api-python",
        "spider-client"
    ]

    for dep in dependencies_to_check:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✅ {dep} is available")
        except ImportError:
            print(f"❌ {dep} is not available")

    # Test 8: Environment Variables Check
    print("\n8. Checking Environment Variables...")

    env_vars_to_check = [
        "OPENAI_API_KEY",
        "SERPER_API_KEY",
        "SERPAPI_API_KEY",
        "BING_SEARCH_API_KEY",
        "SPIDER_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY"
    ]

    for var in env_vars_to_check:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"⚠️ {var} is not set")

    print("\n" + "=" * 60)
    print("🏁 Advanced Features Testing Complete!")
    print("\nNotes:")
    print("- Web search requires API keys (SERPER_API_KEY, SERPAPI_API_KEY, or BING_SEARCH_API_KEY)")
    print("- Web content extraction requires SPIDER_API_KEY")
    print("- YouTube transcript extraction works without API keys")
    print("- PDF processing requires llama-index-readers-file")
    print("- Image analysis requires multimodal LLM support")


if __name__ == "__main__":
    test_advanced_features()
