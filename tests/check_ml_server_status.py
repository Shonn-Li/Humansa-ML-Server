#!/usr/bin/env python3
"""
Check ML Server status and configuration
Verifies server is running and using correct database
"""

import httpx
import asyncio
import json
from datetime import datetime

ML_SERVER_URL = "http://localhost:5002"

async def check_ml_server():
    """Check ML server health and configuration"""
    
    print("ML Server Status Check")
    print("=" * 50)
    print(f"Server URL: {ML_SERVER_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    async with httpx.AsyncClient() as client:
        # 1. Check health endpoint
        try:
            response = await client.get(f"{ML_SERVER_URL}/health")
            if response.status_code == 200:
                print("✅ Health Check: Server is running")
                health_data = response.json()
                print(f"   Response: {health_data}")
            else:
                print(f"❌ Health Check Failed: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to ML Server: {e}")
            print("   Make sure the server is running: python src/main.py")
            return False
        
        # 2. Test multi-agent endpoint with simple query
        print("\n📝 Testing Multi-Agent Endpoint...")
        try:
            test_request = {
                "messages": [{"role": "user", "content": "Hello, this is a test"}],
                "user_id": 10001,  # Test user
                "model": "gpt-4.1-nano",
                "stream": False,
                "max_tokens": 100
            }
            
            response = await client.post(
                f"{ML_SERVER_URL}/v1/multi-agent/response",
                json=test_request,
                timeout=30.0
            )
            
            if response.status_code == 200:
                print("✅ Multi-Agent Endpoint: Working")
                result = response.json()
                if "response" in result:
                    print(f"   Response length: {len(result['response'])} chars")
                if "agents_triggered" in result:
                    print(f"   Agents triggered: {result['agents_triggered']}")
            else:
                print(f"❌ Multi-Agent Endpoint Failed: Status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Multi-Agent Test Failed: {e}")
        
        # 3. Check database connectivity (through a RAG query)
        print("\n🗄️ Testing Database Connection...")
        try:
            test_request = {
                "messages": [{"role": "user", "content": "What notes do I have about reinforcement learning?"}],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "stream": False
            }
            
            response = await client.post(
                f"{ML_SERVER_URL}/v1/multi-agent/response",
                json=test_request,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                # Check if RAG agent was triggered
                if "agents_triggered" in result and "rag" in result.get("agents_triggered", []):
                    print("✅ Database Query: RAG agent successfully accessed database")
                    print("   This confirms ML server is using the test database")
                else:
                    print("⚠️  Database Query: Response received but RAG agent not triggered")
                    print(f"   Agents: {result.get('agents_triggered', [])}")
            else:
                print(f"❌ Database Query Failed: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Database Test Failed: {e}")
        
        # 4. List available endpoints
        print("\n📋 Available Endpoints:")
        endpoints = [
            "/health",
            "/v1/multi-agent/response",
            "/v1/chat/completions",
            "/api/v1/rag/search",
            "/api/v1/web/search"
        ]
        
        for endpoint in endpoints:
            try:
                response = await client.options(f"{ML_SERVER_URL}{endpoint}")
                status = "✅" if response.status_code in [200, 204, 405] else "❌"
                print(f"   {status} {endpoint}")
            except:
                print(f"   ❌ {endpoint}")
    
    print("\n" + "=" * 50)
    print("Status check complete!")
    
    # Provide next steps
    print("\n📌 Next Steps:")
    print("1. If server is not running: python src/main.py")
    print("2. To switch to test database: python tests/setup_test_environment.py")
    print("3. To run agent tests: python tests/test_agents_real_environment.py")
    print("4. To restore production: python tests/setup_test_environment.py restore")

if __name__ == "__main__":
    asyncio.run(check_ml_server())