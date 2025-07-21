#!/usr/bin/env python3
"""Simple feature verification test"""

import httpx
import asyncio
import json

async def test_attachment_simple():
    """Test attachment routing with minimal query"""
    print("Testing Attachment Priority...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5001/v1/multi-agent/response",
            json={
                "messages": [{"role": "user", "content": "What?"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            agents = list(data.get('metadata', {}).get('agent_results', {}).keys())
            print(f"✅ Success! Agents: {agents}")
            print(f"✅ Attachment agent: {'attachment_agent' in agents}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False

async def test_citation_simple():
    """Test citation with minimal query"""
    print("\nTesting Citation...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5001/v1/multi-agent/response",
            json={
                "messages": [{"role": "user", "content": "Tell me about AI"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "enable_citations": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            has_citations = any(f"[{i}]" in content for i in range(1, 10))
            print(f"✅ Success!")
            print(f"✅ Has citations: {has_citations}")
            if has_citations:
                # Show first line with citation
                for line in content.split('\n'):
                    if '[' in line and ']' in line:
                        print(f"   Example: {line[:80]}...")
                        break
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False

async def test_check_logs():
    """Check ML server logs for errors"""
    print("\nChecking ML server logs...")
    proc = await asyncio.create_subprocess_exec(
        'tail', '-50', 'ml_server_final_fix.log',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    log_text = stdout.decode()
    if 'ERROR' in log_text or 'Exception' in log_text:
        print("❌ Errors found in logs:")
        for line in log_text.split('\n'):
            if 'ERROR' in line or 'Exception' in line:
                print(f"   {line}")
    else:
        print("✅ No errors in recent logs")

async def main():
    print("SIMPLE FEATURE VERIFICATION")
    print("=" * 60)
    
    # Test 1: Attachment
    await test_attachment_simple()
    
    # Brief pause
    await asyncio.sleep(2)
    
    # Test 2: Citation
    await test_citation_simple()
    
    # Check logs
    await test_check_logs()
    
    print("\n" + "=" * 60)
    print("Test complete. Check results above.")

if __name__ == "__main__":
    asyncio.run(main())