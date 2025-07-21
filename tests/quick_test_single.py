#!/usr/bin/env python3
"""
Quick test for a single query to show log output format
"""

import asyncio
from test_with_detailed_logging import DetailedAgentTester

async def run_single_test():
    """Run a single test and show the log location"""
    tester = DetailedAgentTester()
    
    print("Running single attachment test...")
    print("-" * 60)
    
    # Test with attachment
    result = await tester.test_query(
        name="Attachment_Test_Example",
        query="Summarize the key points from this paper about reinforcement learning",
        attachments=["https://arxiv.org/pdf/2311.10122.pdf"],
        stream=True
    )
    
    print(f"\nTest Status: {result['status']}")
    print(f"Agents Detected: {' → '.join(result['agents']) if result['agents'] else 'None'}")
    print(f"Has Citations: {result['has_citations']}")
    print(f"Response Length: {result['response_length']} characters")
    
    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print(f"\n📁 Detailed logs saved to:")
    print(f"   {tester.log_base_dir}/Attachment_Test_Example.json")
    print(f"   {tester.log_base_dir}/Attachment_Test_Example_readable.txt")
    
    print("\nTo view the readable log:")
    print(f"cat {tester.log_base_dir}/Attachment_Test_Example_readable.txt")
    
    await tester.client.aclose()

if __name__ == "__main__":
    asyncio.run(run_single_test())