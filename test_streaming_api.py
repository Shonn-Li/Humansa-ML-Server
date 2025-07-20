"""
Test Suite for YouWoAI ML Server Streaming API
Tests OpenAI-standard streaming, citations, RAG, and file attachments
"""

import asyncio
import aiohttp
import json
import time
import base64
from typing import Dict, Any, AsyncGenerator
import os

# Configuration
ML_SERVER_URL = "http://localhost:5002"
TEST_USER_ID = 123  # Use integer user_id

# Test data
TEST_MESSAGES = [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": "What is the capital of France? Please provide a brief answer."}
]

class MLServerTester:
    def __init__(self, base_url: str = ML_SERVER_URL):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health(self):
        """Test health endpoint"""
        print("\n🏥 Testing health endpoint...")
        try:
            async with self.session.get(f"{self.base_url}/health") as resp:
                data = await resp.json()
                print(f"✅ Health check: {data}")
                return resp.status == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    async def test_streaming_chat(self):
        """Test streaming chat completion"""
        print("\n🌊 Testing streaming chat completion...")
        
        request_data = {
            "messages": TEST_MESSAGES,
            "model": "gpt-4o-mini",
            "stream": True,
            "user_id": TEST_USER_ID,
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                headers={"Accept": "text/event-stream"}
            ) as resp:
                print(f"Response status: {resp.status}")
                print(f"Response headers: {dict(resp.headers)}")
                
                chunks = []
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            print("✅ Stream completed")
                            break
                        try:
                            chunk = json.loads(data)
                            chunks.append(chunk)
                            
                            # Print first few chunks for debugging
                            if len(chunks) <= 3:
                                print(f"Chunk {len(chunks)}: {json.dumps(chunk, indent=2)}")
                            elif len(chunks) == 4:
                                print("... (continuing to receive chunks)")
                        except json.JSONDecodeError as e:
                            print(f"❌ Failed to parse chunk: {data}")
                            print(f"Error: {e}")
                
                print(f"✅ Received {len(chunks)} chunks")
                
                # Reconstruct full response
                full_content = ""
                for chunk in chunks:
                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            full_content += delta["content"]
                
                print(f"Full response: {full_content}")
                return True
                
        except Exception as e:
            print(f"❌ Streaming chat failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_non_streaming_chat(self):
        """Test non-streaming chat completion"""
        print("\n📄 Testing non-streaming chat completion...")
        
        request_data = {
            "messages": TEST_MESSAGES,
            "model": "gpt-4o-mini",
            "stream": False,
            "user_id": TEST_USER_ID,
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data
            ) as resp:
                print(f"Response status: {resp.status}")
                data = await resp.json()
                
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    print(f"✅ Response: {content}")
                    print(f"Usage: {data.get('usage', {})}")
                    return True
                else:
                    print(f"❌ Unexpected response format: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Non-streaming chat failed: {e}")
            return False
    
    async def test_multi_agent(self):
        """Test multi-agent endpoint"""
        print("\n🤖 Testing multi-agent endpoint...")
        
        request_data = {
            "messages": [
                {"role": "user", "content": "Search for the latest news about AI advancements in 2024"}
            ],
            "model": "gpt-4o-mini",
            "stream": False,  # Streaming not supported yet
            "user_id": TEST_USER_ID,
            "enable_citations": True
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/multi-agent/response",
                json=request_data
            ) as resp:
                print(f"Response status: {resp.status}")
                data = await resp.json()
                
                if data.get("status") == "success":
                    print(f"✅ Multi-agent response received")
                    print(f"Response preview: {data.get('response', '')[:200]}...")
                    
                    # Check agent results
                    metadata = data.get("metadata", {})
                    agent_results = metadata.get("agent_results", {})
                    print(f"\nAgent execution summary:")
                    for agent, result in agent_results.items():
                        print(f"  - {agent}: {result.get('status', 'unknown')}")
                    
                    print(f"Workflow time: {metadata.get('workflow_time', 0):.2f}s")
                    return True
                else:
                    print(f"❌ Multi-agent failed: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Multi-agent request failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_with_citations(self):
        """Test chat with citations enabled"""
        print("\n📚 Testing chat with citations...")
        
        request_data = {
            "messages": [
                {"role": "user", "content": "Tell me about machine learning. Include citations."}
            ],
            "model": "gpt-4o-mini",
            "stream": False,
            "user_id": TEST_USER_ID,
            "enable_citations": True
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data
            ) as resp:
                print(f"Response status: {resp.status}")
                data = await resp.json()
                
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    print(f"✅ Response with citations: {content[:300]}...")
                    
                    # Check if citations are present
                    if "[" in content and "]" in content:
                        print("✅ Citations found in response")
                    else:
                        print("⚠️ No citations found in response")
                    
                    return True
                else:
                    print(f"❌ Unexpected response format: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Citation test failed: {e}")
            return False
    
    async def test_with_file_attachment(self):
        """Test chat with file attachment"""
        print("\n📎 Testing chat with file attachment...")
        
        # Create a simple text file attachment
        test_content = "This is a test document about artificial intelligence and machine learning."
        encoded_content = base64.b64encode(test_content.encode()).decode()
        
        request_data = {
            "messages": [
                {"role": "user", "content": "Summarize the attached document."}
            ],
            "model": "gpt-4o-mini",
            "stream": False,
            "user_id": TEST_USER_ID,
            "attachments": [
                {
                    "type": "text",
                    "name": "test_document.txt",
                    "content": encoded_content
                }
            ]
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data
            ) as resp:
                print(f"Response status: {resp.status}")
                data = await resp.json()
                
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    print(f"✅ Response about attachment: {content[:300]}...")
                    return True
                else:
                    print(f"❌ Unexpected response format: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ File attachment test failed: {e}")
            return False
    
    async def test_streaming_with_citations(self):
        """Test streaming with citations enabled"""
        print("\n🌊📚 Testing streaming with citations...")
        
        request_data = {
            "messages": [
                {"role": "user", "content": "What are the main principles of machine learning? Please cite sources."}
            ],
            "model": "gpt-4o-mini",
            "stream": True,
            "user_id": TEST_USER_ID,
            "enable_citations": True,
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                headers={"Accept": "text/event-stream"}
            ) as resp:
                print(f"Response status: {resp.status}")
                
                chunks = []
                full_content = ""
                
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            print("✅ Stream with citations completed")
                            break
                        try:
                            chunk = json.loads(data)
                            chunks.append(chunk)
                            
                            # Accumulate content
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    full_content += delta["content"]
                                    
                        except json.JSONDecodeError:
                            print(f"Failed to parse chunk: {data}")
                
                print(f"✅ Received {len(chunks)} chunks")
                print(f"Full response preview: {full_content[:300]}...")
                
                # Check for citations
                if "[" in full_content and "]" in full_content:
                    print("✅ Citations found in streamed response")
                else:
                    print("⚠️ No citations found in streamed response")
                
                return True
                
        except Exception as e:
            print(f"❌ Streaming with citations failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting YouWoAI ML Server Test Suite")
        print(f"📍 Testing server at: {self.base_url}")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health),
            ("Non-Streaming Chat", self.test_non_streaming_chat),
            ("Streaming Chat", self.test_streaming_chat),
            ("Multi-Agent", self.test_multi_agent),
            ("Chat with Citations", self.test_with_citations),
            ("File Attachment", self.test_with_file_attachment),
            ("Streaming with Citations", self.test_streaming_with_citations),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                success = await test_func()
                results[test_name] = success
                await asyncio.sleep(1)  # Small delay between tests
            except Exception as e:
                print(f"❌ Test '{test_name}' crashed: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} - {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        print("=" * 50)
        
        return passed == total

async def main():
    """Main test runner"""
    async with MLServerTester() as tester:
        success = await tester.run_all_tests()
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)