#!/usr/bin/env python3
"""
Comprehensive validation test suite for multi-agent system
Validates expected behavior for attachments, citations, and streaming
"""

import asyncio
import httpx
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sys

class ComprehensiveValidator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.base_url = "http://localhost:5002/v1/multi-agent/response"
        self.results = []
        
    async def validate_all(self):
        """Run all validation tests"""
        print("="*80)
        print("COMPREHENSIVE MULTI-AGENT VALIDATION")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Run test suites
        await self.validate_attachment_processing()
        await self.validate_citation_formatting()
        await self.validate_streaming_format()
        await self.validate_agent_integration()
        await self.validate_edge_cases()
        
        # Summary
        self.print_summary()
        
    async def validate_attachment_processing(self):
        """Validate attachment agent processes files correctly"""
        print("\n" + "="*60)
        print("1. ATTACHMENT PROCESSING VALIDATION")
        print("="*60)
        
        test_cases = [
            {
                "name": "PDF Attachment - Graph Reasoning",
                "query": "What is this paper about? Summarize the main topic.",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "expected": {
                    "content_keywords": ["graph", "reasoning", "llm", "teach"],
                    "not_keywords": ["parl", "predictable reinforcement"],
                    "agents": ["attachment", "response", "citation"],
                    "not_agents": ["rag"]
                }
            },
            {
                "name": "Multiple Attachments",
                "query": "Compare these two papers",
                "attachments": [
                    "https://arxiv.org/pdf/2505.18499.pdf",
                    "https://arxiv.org/pdf/2311.10122.pdf"
                ],
                "expected": {
                    "content_keywords": ["compare", "both", "first", "second"],
                    "agents": ["attachment", "response", "citation"],
                    "attachment_count": 2
                }
            },
            {
                "name": "Image Attachment",
                "query": "Describe what's shown in this image",
                "attachments": ["https://arxiv.org/html/2407.09124v1/x1.png"],
                "expected": {
                    "content_keywords": ["image", "shows", "diagram"],
                    "agents": ["attachment", "response"],
                    "is_image": True
                }
            }
        ]
        
        for test in test_cases:
            result = await self.run_attachment_test(test)
            self.results.append(result)
            
    async def run_attachment_test(self, test: Dict) -> Dict:
        """Run a single attachment test"""
        print(f"\nTest: {test['name']}")
        print("-"*50)
        
        request = {
            "messages": [{"role": "user", "content": test["query"]}],
            "attachments": test["attachments"],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": False
        }
        
        try:
            response = await self.client.post(self.base_url, json=request)
            result = response.json()
            
            # Validate response
            validations = []
            
            # Check agents
            if 'metadata' in result:
                agents = list(result['metadata'].get('agent_results', {}).keys())
                agents_clean = [a.replace('_agent', '') for a in agents]
                
                # Expected agents
                for expected_agent in test['expected'].get('agents', []):
                    if expected_agent in agents_clean:
                        validations.append(("✅", f"Agent '{expected_agent}' executed"))
                    else:
                        validations.append(("❌", f"Agent '{expected_agent}' NOT executed"))
                        
                # Unexpected agents
                for not_agent in test['expected'].get('not_agents', []):
                    if not_agent not in agents_clean:
                        validations.append(("✅", f"Agent '{not_agent}' correctly NOT executed"))
                    else:
                        validations.append(("❌", f"Agent '{not_agent}' should NOT be executed"))
                        
                # Check attachment processing
                if 'attachment_agent' in result['metadata']['agent_results']:
                    att_data = result['metadata']['agent_results']['attachment_agent']
                    att_count = att_data.get('data', {}).get('metadata', {}).get('attachment_count', 0)
                    
                    if 'attachment_count' in test['expected']:
                        if att_count == test['expected']['attachment_count']:
                            validations.append(("✅", f"Processed {att_count} attachments"))
                        else:
                            validations.append(("❌", f"Expected {test['expected']['attachment_count']} attachments, got {att_count}"))
                            
            # Check content
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '').lower()
            
            # Expected keywords
            for keyword in test['expected'].get('content_keywords', []):
                if keyword in content:
                    validations.append(("✅", f"Content contains '{keyword}'"))
                else:
                    validations.append(("❌", f"Content missing '{keyword}'"))
                    
            # Unexpected keywords
            for keyword in test['expected'].get('not_keywords', []):
                if keyword not in content:
                    validations.append(("✅", f"Content correctly does NOT contain '{keyword}'"))
                else:
                    validations.append(("❌", f"Content should NOT contain '{keyword}'"))
                    
            # Print results
            for status, msg in validations:
                print(f"  {status} {msg}")
                
            # Overall result
            passed = all(status == "✅" for status, _ in validations)
            return {
                "test": test['name'],
                "passed": passed,
                "validations": validations
            }
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            return {
                "test": test['name'],
                "passed": False,
                "error": str(e)
            }
            
    async def validate_citation_formatting(self):
        """Validate citation formatting follows expected patterns"""
        print("\n" + "="*60)
        print("2. CITATION FORMATTING VALIDATION")
        print("="*60)
        
        test_cases = [
            {
                "name": "Basic Citation Test",
                "query": "What is machine learning? Include citations.",
                "attachments": [],
                "stream": False,
                "expected": {
                    "has_numbered_citations": True,
                    "has_sources_section": True,
                    "citation_pattern": r'\[\d+\]'
                }
            },
            {
                "name": "Attachment Citation",
                "query": "Summarize this paper with citations",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": False,
                "expected": {
                    "has_numbered_citations": True,
                    "has_attachment_source": True,
                    "source_contains_url": True
                }
            },
            {
                "name": "Streaming Citation",
                "query": "Explain reinforcement learning with citations",
                "attachments": [],
                "stream": True,
                "expected": {
                    "has_citation_events": True,
                    "has_annotation_events": True,
                    "follows_openai_format": True
                }
            }
        ]
        
        for test in test_cases:
            result = await self.run_citation_test(test)
            self.results.append(result)
            
    async def run_citation_test(self, test: Dict) -> Dict:
        """Run a single citation test"""
        print(f"\nTest: {test['name']}")
        print("-"*50)
        
        request = {
            "messages": [{"role": "user", "content": test["query"]}],
            "attachments": test.get("attachments", []),
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": test.get("stream", False),
            "enable_citations": True
        }
        
        try:
            validations = []
            
            if test.get("stream", False):
                # Streaming test
                citation_events = []
                annotation_events = []
                content = ""
                
                async with self.client.stream('POST', self.base_url, json=request) as response:
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            event_data = line[6:]
                            if event_data == '[DONE]':
                                break
                                
                            try:
                                event = json.loads(event_data)
                                event_type = event.get('type', '')
                                
                                # Track citation events
                                if 'citation' in event_type or 'cit_' in str(event):
                                    citation_events.append(event)
                                    
                                # Track annotation events
                                if 'annotation' in event_type:
                                    annotation_events.append(event)
                                    
                                # Collect content
                                if event_type == 'response.output_text.delta':
                                    content += event.get('delta', '')
                                    
                            except:
                                pass
                                
                # Validate streaming format
                if test['expected'].get('has_citation_events'):
                    if citation_events:
                        validations.append(("✅", f"Found {len(citation_events)} citation events"))
                    else:
                        validations.append(("❌", "No citation events found"))
                        
                if test['expected'].get('has_annotation_events'):
                    if annotation_events:
                        validations.append(("✅", f"Found {len(annotation_events)} annotation events"))
                        
                        # Check OpenAI format
                        for event in annotation_events[:1]:  # Check first annotation
                            if all(key in event.get('annotation', {}) for key in ['type', 'start_index', 'end_index']):
                                validations.append(("✅", "Annotations follow OpenAI format"))
                            else:
                                validations.append(("❌", "Annotations missing required fields"))
                    else:
                        validations.append(("⚠️", "No annotation events found (may be OK)"))
                        
            else:
                # Non-streaming test
                response = await self.client.post(self.base_url, json=request)
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
            # Validate content format
            if test['expected'].get('has_numbered_citations'):
                citation_pattern = test['expected'].get('citation_pattern', r'\[\d+\]')
                citations = re.findall(citation_pattern, content)
                if citations:
                    validations.append(("✅", f"Found {len(citations)} numbered citations"))
                else:
                    validations.append(("❌", "No numbered citations found"))
                    
            if test['expected'].get('has_sources_section'):
                if any(marker in content for marker in ['Sources:', 'References:', '\n[1]', '\n[2]']):
                    validations.append(("✅", "Has sources/references section"))
                else:
                    validations.append(("❌", "No sources section found"))
                    
            if test['expected'].get('has_attachment_source'):
                if any(url in content for url in test.get('attachments', [])):
                    validations.append(("✅", "Attachment URL included in sources"))
                else:
                    validations.append(("❌", "Attachment URL not in sources"))
                    
            # Print results
            for status, msg in validations:
                print(f"  {status} {msg}")
                
            passed = all(status == "✅" for status, _ in validations)
            return {
                "test": test['name'],
                "passed": passed,
                "validations": validations
            }
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            return {
                "test": test['name'],
                "passed": False,
                "error": str(e)
            }
            
    async def validate_streaming_format(self):
        """Validate streaming follows OpenAI Response API format"""
        print("\n" + "="*60)
        print("3. STREAMING FORMAT VALIDATION")
        print("="*60)
        
        request = {
            "messages": [{"role": "user", "content": "Test streaming format"}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": True
        }
        
        validations = []
        event_types = set()
        event_pairs = {
            'response.output_item.added': 'response.output_item.done',
            'response.content_part.added': 'response.content_part.done',
        }
        event_tracking = {key: 0 for key in event_pairs}
        
        print("Analyzing streaming event structure...")
        print("-"*50)
        
        try:
            async with self.client.stream('POST', self.base_url, json=request) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                            
                        try:
                            event = json.loads(event_data)
                            event_type = event.get('type', '')
                            event_types.add(event_type)
                            
                            # Track paired events
                            for start, end in event_pairs.items():
                                if event_type == start:
                                    event_tracking[start] += 1
                                elif event_type == end:
                                    event_tracking[start] -= 1
                                    
                        except:
                            pass
                            
            # Validate event structure
            required_events = ['response.created', 'response.in_progress', 'response.done']
            for event in required_events:
                if event in event_types:
                    validations.append(("✅", f"Has required event: {event}"))
                else:
                    validations.append(("❌", f"Missing required event: {event}"))
                    
            # Check paired events
            for event, count in event_tracking.items():
                if count == 0:
                    validations.append(("✅", f"Event pairs balanced: {event}"))
                else:
                    validations.append(("❌", f"Unbalanced events: {event} (diff: {count})"))
                    
            # Print results
            for status, msg in validations:
                print(f"  {status} {msg}")
                
            print(f"\nTotal event types: {len(event_types)}")
            
            passed = all(status == "✅" for status, _ in validations)
            self.results.append({
                "test": "Streaming Format Validation",
                "passed": passed,
                "validations": validations
            })
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            self.results.append({
                "test": "Streaming Format Validation",
                "passed": False,
                "error": str(e)
            })
            
    async def validate_agent_integration(self):
        """Validate agents work together correctly"""
        print("\n" + "="*60)
        print("4. AGENT INTEGRATION VALIDATION")
        print("="*60)
        
        test_cases = [
            {
                "name": "Attachment + Citation Integration",
                "query": "Summarize key points from this paper and cite them properly",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "expected": {
                    "agents_order": ["router", "attachment", "response", "citation"],
                    "attachment_in_citations": True,
                    "proper_content_flow": True
                }
            },
            {
                "name": "No RAG with Attachments",
                "query": "What does this document say about the main topic?",
                "attachments": ["https://arxiv.org/pdf/2311.10122.pdf"],
                "expected": {
                    "no_rag": True,
                    "attachment_only": True
                }
            },
            {
                "name": "Web Search + Citation",
                "query": "What are the latest developments in quantum computing? Include citations.",
                "attachments": [],
                "expected": {
                    "agents": ["router", "web_search", "response", "citation"],
                    "web_sources_cited": True
                }
            }
        ]
        
        for test in test_cases:
            result = await self.run_integration_test(test)
            self.results.append(result)
            
    async def run_integration_test(self, test: Dict) -> Dict:
        """Run integration test"""
        print(f"\nTest: {test['name']}")
        print("-"*50)
        
        request = {
            "messages": [{"role": "user", "content": test["query"]}],
            "attachments": test.get("attachments", []),
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": False
        }
        
        try:
            response = await self.client.post(self.base_url, json=request)
            result = response.json()
            validations = []
            
            # Check metadata
            if 'metadata' in result:
                agents_used = list(result['metadata'].get('agent_results', {}).keys())
                agents_clean = [a.replace('_agent', '') for a in agents_used]
                
                # Check no RAG with attachments
                if test['expected'].get('no_rag') and test.get('attachments'):
                    if 'rag' not in agents_clean:
                        validations.append(("✅", "RAG correctly NOT used with attachments"))
                    else:
                        validations.append(("❌", "RAG should NOT be used with attachments"))
                        
                # Check expected agents
                if 'agents' in test['expected']:
                    for agent in test['expected']['agents']:
                        if agent in agents_clean:
                            validations.append(("✅", f"Agent '{agent}' present"))
                        else:
                            validations.append(("❌", f"Agent '{agent}' missing"))
                            
                # Check attachment context in citations
                if test['expected'].get('attachment_in_citations'):
                    citation_data = result['metadata'].get('agent_results', {}).get('citation_agent', {})
                    if citation_data.get('data', {}).get('citations', {}).get('sources'):
                        has_attachment_source = any(
                            s.get('source_type') == 'file' 
                            for s in citation_data['data']['citations']['sources']
                        )
                        if has_attachment_source:
                            validations.append(("✅", "Attachment included in citation sources"))
                        else:
                            validations.append(("❌", "Attachment NOT in citation sources"))
                            
            # Print results
            for status, msg in validations:
                print(f"  {status} {msg}")
                
            passed = all(status == "✅" for status, _ in validations)
            return {
                "test": test['name'],
                "passed": passed,
                "validations": validations
            }
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            return {
                "test": test['name'],
                "passed": False,
                "error": str(e)
            }
            
    async def validate_edge_cases(self):
        """Validate edge cases"""
        print("\n" + "="*60)
        print("5. EDGE CASE VALIDATION")
        print("="*60)
        
        test_cases = [
            {
                "name": "Empty Attachments Array",
                "query": "Process these attachments",
                "attachments": [],
                "expected": {
                    "no_attachment_agent": True,
                    "graceful_handling": True
                }
            },
            {
                "name": "Invalid Attachment URL",
                "query": "Analyze this file",
                "attachments": ["https://invalid-url-that-does-not-exist.com/file.pdf"],
                "expected": {
                    "handles_error": True,
                    "provides_feedback": True
                }
            },
            {
                "name": "No Citations Requested",
                "query": "Just tell me about machine learning",
                "attachments": [],
                "enable_citations": False,
                "expected": {
                    "no_citation_agent": True,
                    "no_citations_in_response": True
                }
            }
        ]
        
        for test in test_cases:
            result = await self.run_edge_case_test(test)
            self.results.append(result)
            
    async def run_edge_case_test(self, test: Dict) -> Dict:
        """Run edge case test"""
        print(f"\nTest: {test['name']}")
        print("-"*50)
        
        request = {
            "messages": [{"role": "user", "content": test["query"]}],
            "attachments": test.get("attachments", []),
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": False,
            "enable_citations": test.get("enable_citations", True)
        }
        
        try:
            response = await self.client.post(self.base_url, json=request)
            result = response.json()
            validations = []
            
            # Check response status
            if response.status_code == 200:
                validations.append(("✅", "Request handled successfully"))
            else:
                validations.append(("❌", f"Request failed with status {response.status_code}"))
                
            # Check agents
            if 'metadata' in result:
                agents = list(result['metadata'].get('agent_results', {}).keys())
                
                if test['expected'].get('no_attachment_agent'):
                    if 'attachment_agent' not in agents:
                        validations.append(("✅", "Attachment agent correctly NOT used"))
                    else:
                        validations.append(("❌", "Attachment agent should NOT be used"))
                        
                if test['expected'].get('no_citation_agent'):
                    if 'citation_agent' not in agents:
                        validations.append(("✅", "Citation agent correctly NOT used"))
                    else:
                        validations.append(("❌", "Citation agent should NOT be used"))
                        
            # Check content
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if test['expected'].get('no_citations_in_response'):
                if not re.search(r'\[\d+\]', content):
                    validations.append(("✅", "No citation markers in response"))
                else:
                    validations.append(("❌", "Found citation markers when none expected"))
                    
            # Print results
            for status, msg in validations:
                print(f"  {status} {msg}")
                
            passed = all(status == "✅" for status, _ in validations)
            return {
                "test": test['name'],
                "passed": passed,
                "validations": validations
            }
            
        except Exception as e:
            if test['expected'].get('handles_error'):
                print(f"  ✅ Error handled: {str(e)[:50]}...")
                return {
                    "test": test['name'],
                    "passed": True,
                    "handled_error": str(e)
                }
            else:
                print(f"  ❌ ERROR: {str(e)}")
                return {
                    "test": test['name'],
                    "passed": False,
                    "error": str(e)
                }
                
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get('passed', False))
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result.get('passed', False):
                    print(f"  - {result['test']}")
                    if 'error' in result:
                        print(f"    Error: {result['error']}")
                        
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        
        # Check specific issues
        attachment_issues = any(
            'attachment' in str(r) and not r.get('passed', False) 
            for r in self.results
        )
        
        citation_issues = any(
            'citation' in str(r).lower() and not r.get('passed', False)
            for r in self.results
        )
        
        if attachment_issues:
            print("\n⚠️  Attachment Processing Issues:")
            print("  1. Ensure ML server is restarted with latest code")
            print("  2. Check FileAttachmentManager is processing URLs correctly")
            print("  3. Verify embeddings are created for attachment URLs")
            
        if citation_issues:
            print("\n⚠️  Citation Formatting Issues:")
            print("  1. Check CitationEngine is extracting sources correctly")
            print("  2. Verify streaming annotations follow OpenAI format")
            print("  3. Ensure citation markers [1], [2] are properly added")
            
        if passed_tests == total_tests:
            print("\n✅ All tests passed! System is working correctly.")

async def main():
    validator = ComprehensiveValidator()
    await validator.validate_all()
    await validator.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())