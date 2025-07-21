#!/usr/bin/env python3
"""
Test to verify attachment content is correctly processed
Shows full event stream and actual responses
"""

import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path
import sys

class AttachmentContentVerifier:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.base_url = "http://localhost:5002/v1/multi-agent/response"
        
    async def test_attachment_content(self, pdf_url: str, expected_content: str):
        """Test that attachment returns correct content, not RAG results"""
        
        print("="*80)
        print("ATTACHMENT CONTENT VERIFICATION TEST")
        print("="*80)
        print(f"PDF URL: {pdf_url}")
        print(f"Expected content keywords: {expected_content}")
        print("-"*80)
        
        # Test both streaming and non-streaming
        for stream in [True, False]:
            print(f"\n{'='*60}")
            print(f"TEST MODE: {'STREAMING' if stream else 'NON-STREAMING'}")
            print("="*60)
            
            request_data = {
                "messages": [{"role": "user", "content": "Summarize this paper and tell me what it's about"}],
                "attachments": [pdf_url],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": stream,
                "enable_citations": True
            }
            
            try:
                if stream:
                    await self._test_streaming(request_data, expected_content)
                else:
                    await self._test_non_streaming(request_data, expected_content)
                    
            except Exception as e:
                print(f"\n❌ ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                
    async def _test_streaming(self, request_data: dict, expected_content: str):
        """Test streaming response with full event logging"""
        
        print("\n📡 STREAMING EVENTS:")
        print("-"*60)
        
        events_log = []
        final_response = ""
        agents_detected = set()
        attachment_content = None
        rag_content = None
        
        async with self.client.stream('POST', self.base_url, json=request_data) as response:
            event_num = 0
            
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data == '[DONE]':
                        print(f"\n✅ Stream completed")
                        break
                        
                    try:
                        event = json.loads(event_data)
                        event_num += 1
                        event_type = event.get('type', '')
                        
                        # Log important events
                        if any(keyword in event_type for keyword in ['reasoning', 'tool', 'attachment', 'rag', 'output_item']):
                            print(f"\nEvent {event_num}: {event_type}")
                            
                            # Show reasoning content
                            if 'reasoning' in event_type and 'delta' in event:
                                delta = event.get('delta', '')
                                if delta and len(delta) > 1:
                                    print(f"  💭 {delta[:100]}...")
                                    
                                    # Detect agents from reasoning
                                    if 'attachment' in delta.lower():
                                        agents_detected.add('attachment')
                                    if 'rag' in delta.lower() or 'knowledge' in delta.lower():
                                        agents_detected.add('rag')
                                        
                            # Show tool calls
                            if 'tool_call' in event_type:
                                print(f"  🔧 Tool: {event.get('name', 'unknown')}")
                                
                            # Track output items
                            if 'output_item.added' in event_type:
                                item = event.get('item', {})
                                item_id = item.get('id', '')
                                item_type = item.get('type', '')
                                print(f"  📦 Output Item: {item_type} (ID: {item_id})")
                                
                                # Detect agents from IDs
                                if 'attachment' in item_id:
                                    agents_detected.add('attachment')
                                elif 'rag' in item_id or 'fs_' in item_id:
                                    agents_detected.add('rag')
                                    
                        # Collect response content
                        if event_type == 'response.output_text.delta':
                            delta_text = event.get('delta', '')
                            final_response += delta_text
                            
                            # Show first chunk of response
                            if len(final_response) < 200 and delta_text:
                                print(f"  📝 Response chunk: {delta_text[:50]}...")
                                
                        # Check metadata
                        if event_type == 'response.usage' and 'metadata' in event:
                            metadata = event['metadata']
                            print(f"\n📊 FINAL METADATA:")
                            
                            if 'agent_results' in metadata:
                                print("  Agents used:")
                                for agent_key in sorted(metadata['agent_results'].keys()):
                                    agent_data = metadata['agent_results'][agent_key]
                                    print(f"    - {agent_key}: {agent_data.get('status')}")
                                    
                                    # Check for content mixing
                                    if agent_key == 'attachment_agent':
                                        attachment_content = str(agent_data.get('data', {}))
                                    elif agent_key == 'rag_agent':
                                        rag_content = str(agent_data.get('data', {}))
                                        
                        events_log.append(event)
                        
                    except json.JSONDecodeError:
                        pass
                        
        # Analyze results
        print(f"\n\n🔍 ANALYSIS:")
        print("-"*60)
        print(f"Total events: {event_num}")
        print(f"Response length: {len(final_response)} characters")
        print(f"Agents detected from events: {agents_detected}")
        
        # Content verification
        print(f"\n📄 CONTENT VERIFICATION:")
        print(f"Expected keywords: {expected_content}")
        
        # Check if response contains expected content
        response_lower = final_response.lower()
        expected_lower = expected_content.lower()
        
        if expected_lower in response_lower:
            print(f"✅ CORRECT: Response contains expected content about '{expected_content}'")
        else:
            print(f"❌ WRONG: Response does NOT contain expected content")
            
        # Check for PARL contamination
        if 'parl' in response_lower and 'parl' not in expected_lower:
            print(f"⚠️  WARNING: Response mentions PARL when it shouldn't!")
            
        # Check if RAG was used
        if 'rag' in agents_detected:
            print(f"⚠️  WARNING: RAG agent was used for attachment processing")
            
        # Show response preview
        print(f"\n📋 RESPONSE PREVIEW (first 500 chars):")
        print("-"*60)
        print(final_response[:500])
        if len(final_response) > 500:
            print("... [truncated]")
            
    async def _test_non_streaming(self, request_data: dict, expected_content: str):
        """Test non-streaming response"""
        
        print("\n📥 NON-STREAMING REQUEST:")
        print("-"*60)
        
        try:
            response = await self.client.post(self.base_url, json=request_data)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error Response: {response.text}")
                return
                
            result = response.json()
            
            # Show metadata
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"\n📊 METADATA:")
                
                if 'agent_results' in metadata:
                    print("  Agents used:")
                    for agent_key in sorted(metadata['agent_results'].keys()):
                        agent_data = metadata['agent_results'][agent_key]
                        print(f"    - {agent_key}: {agent_data.get('status')}")
                        
                    # Warn if RAG was used
                    if 'rag_agent' in metadata['agent_results']:
                        print(f"\n⚠️  WARNING: RAG agent was used for attachment!")
                        
            # Get response content
            content = ""
            if 'choices' in result and result['choices']:
                content = result['choices'][0].get('message', {}).get('content', '')
                
            print(f"\nResponse length: {len(content)} characters")
            
            # Content verification
            print(f"\n📄 CONTENT VERIFICATION:")
            print(f"Expected keywords: {expected_content}")
            
            content_lower = content.lower()
            expected_lower = expected_content.lower()
            
            if expected_lower in content_lower:
                print(f"✅ CORRECT: Response contains expected content about '{expected_content}'")
            else:
                print(f"❌ WRONG: Response does NOT contain expected content")
                
            # Check for PARL contamination
            if 'parl' in content_lower and 'parl' not in expected_lower:
                print(f"⚠️  WARNING: Response mentions PARL when it shouldn't!")
                
            # Show response preview
            print(f"\n📋 RESPONSE PREVIEW (first 500 chars):")
            print("-"*60)
            print(content[:500])
            if len(content) > 500:
                print("... [truncated]")
                
        except Exception as e:
            print(f"\n❌ Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            
    async def run_verification_tests(self):
        """Run comprehensive attachment verification tests"""
        
        print("\n" + "="*80)
        print("RUNNING ATTACHMENT CONTENT VERIFICATION TESTS")
        print("="*80)
        
        # Test cases with expected content
        test_cases = [
            {
                "name": "Graph Reasoning Paper",
                "url": "https://arxiv.org/pdf/2505.18499.pdf",
                "expected": "graph reasoning"  # This paper is about teaching LLMs to reason on graphs
            },
            {
                "name": "Different Paper Test",
                "url": "https://arxiv.org/pdf/2311.10122.pdf", 
                "expected": "multimodal"  # This is a different paper, should not return PARL
            }
        ]
        
        for test in test_cases:
            print(f"\n\n{'#'*80}")
            print(f"TEST: {test['name']}")
            print(f"#"*80)
            
            await self.test_attachment_content(test['url'], test['expected'])
            
            # Pause between tests
            await asyncio.sleep(3)
            
        await self.client.aclose()
        
        print("\n" + "="*80)
        print("VERIFICATION TESTS COMPLETE")
        print("="*80)
        
async def main():
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5002/health")
            if response.status_code != 200:
                print("❌ ML Server not responding on port 5001")
                print("Please ensure the server is running")
                return
    except:
        print("❌ Cannot connect to ML Server on port 5001")
        print("Please start the server first")
        return
        
    verifier = AttachmentContentVerifier()
    await verifier.run_verification_tests()

if __name__ == "__main__":
    asyncio.run(main())