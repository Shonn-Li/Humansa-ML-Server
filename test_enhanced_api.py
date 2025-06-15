#!/usr/bin/env python3
"""
Test script for the enhanced YouWoAI ML Server API
"""

import requests
import json
import time


def test_server():
    """Test the enhanced ML server endpoints"""

    # Change this to the correct port
    base_url = "http://localhost:5001"

    print("🚀 Testing YouWoAI Enhanced ML Server")
    print("=" * 50)

    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed:", response.json())
        else:
            print("❌ Health check failed:", response.status_code)
            return
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # Test 2: List models
    print("\n2. Testing models endpoint...")
    try:
        response = requests.get(f"{base_url}/v1/models")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Found {len(models['data'])} available models:")
            for model in models['data'][:5]:  # Show first 5
                print(f"   - {model['id']} ({model['provider']})")
            if len(models['data']) > 5:
                print(f"   ... and {len(models['data']) - 5} more")
        else:
            print("❌ Models endpoint failed:", response.status_code)
    except Exception as e:
        print(f"❌ Models endpoint failed: {e}")

    # Test 3: Simple chat completion
    print("\n3. Testing chat completion...")
    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello! Please respond with exactly: 'API is working perfectly!'"}
            ],
            "model": "gpt-4.1-nano",  # Most cost-effective OpenAI model
            "max_tokens": 50
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print("✅ Chat completion successful:")
            print(f"   Response: {message}")
            print(f"   Provider: {result.get('provider', 'unknown')}")
            print(f"   Model: {result.get('model', 'unknown')}")
        else:
            print("❌ Chat completion failed:",
                  response.status_code, response.text)
    except Exception as e:
        print(f"❌ Chat completion failed: {e}")

    # Test 4: Test with different provider (if available)
    print("\n4. Testing with DeepSeek provider...")
    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello from DeepSeek!"}
            ],
            "provider": "deepseek",
            "model": "deepseek-chat",
            "max_tokens": 30
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print("✅ DeepSeek provider working:")
            print(f"   Response: {message}")
        else:
            print("❌ DeepSeek provider failed:", response.status_code)
    except Exception as e:
        print(f"❌ DeepSeek provider failed: {e}")

    # Test 5: Test Anthropic provider
    print("\n5. Testing Anthropic provider...")
    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello from Anthropic Claude!"}
            ],
            "provider": "anthropic",
            "model": "claude-3-5-haiku-20241022",  # Most cost-effective Anthropic model
            "max_tokens": 30
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print("✅ Anthropic provider working:")
            print(f"   Response: {message}")
        else:
            print("❌ Anthropic provider failed:", response.status_code)
            print("   (This is expected if ANTHROPIC_API_KEY is not set)")
    except Exception as e:
        print(f"❌ Anthropic provider failed: {e}")
        print("   (This is expected if ANTHROPIC_API_KEY is not set)")

    # Test 6: Test Gemini provider (will fail without API key)
    print("\n6. Testing Gemini provider...")
    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello from Gemini!"}
            ],
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",  # Most cost-effective Gemini model
            "max_tokens": 30
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print("✅ Gemini provider working:")
            print(f"   Response: {message}")
        else:
            print("❌ Gemini provider failed:", response.status_code)
            print("   (This is expected if GOOGLE_API_KEY is not set)")
    except Exception as e:
        print(f"❌ Gemini provider failed: {e}")
        print("   (This is expected if GOOGLE_API_KEY is not set)")

    # Test 7: Test xAI provider
    print("\n7. Testing xAI provider...")
    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello from Grok!"}
            ],
            "provider": "xai",
            "model": "grok-3-mini",  # Most cost-effective xAI model
            "max_tokens": 30
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print("✅ xAI provider working:")
            print(f"   Response: {message}")
        else:
            print("❌ xAI provider failed:", response.status_code)
            print("   (This is expected if XAI_API_KEY is not set)")
    except Exception as e:
        print(f"❌ xAI provider failed: {e}")
        print("   (This is expected if XAI_API_KEY is not set)")

    print("\n" + "=" * 50)
    print("🎉 Testing completed!")
    print("\nTo enable additional providers:")
    print("   export GOOGLE_API_KEY=your_google_api_key  # For Gemini")
    print("   export XAI_API_KEY=your_xai_api_key        # For xAI/Grok")
    print("   export DEEPSEEK_API_KEY=your_deepseek_key  # For DeepSeek")
    print("   export ANTHROPIC_API_KEY=your_anthropic_key # For Claude")
    print("   Then restart the server")


if __name__ == "__main__":
    test_server()
