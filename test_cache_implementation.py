#!/usr/bin/env python3
"""
Test web search caching implementation
"""

import requests
import json
import time


def test_web_search_caching():
    """Test the web search caching functionality"""

    base_url = "http://localhost:5001"

    print("🔍 Testing Web Search Caching Implementation")
    print("=" * 60)

    # Test 1: Check cache stats (should be empty initially)
    print("\n1. Checking initial cache stats...")
    try:
        response = requests.get(f"{base_url}/search_cache_stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Cache stats: {stats}")
        else:
            print(f"   ❌ Failed to get cache stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache stats failed: {e}")

    # Test 2: First search (should be cache miss)
    print(f"\n2. Testing first search (cache miss)...")
    test_query = "latest AI news 2024"

    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": f"Search for: {test_query}"}
            ],
            "model": "gpt-4.1-nano",
            "enable_web_search": True,
            "max_tokens": 100
        }

        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data,
            timeout=30
        )
        first_search_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            search_results = result.get('search_results', [])
            print(f"   ✅ First search completed in {first_search_time:.2f}s")
            print(f"   Found {len(search_results)} results")

            if search_results:
                first_result = search_results[0]
                cached_status = first_result.get('cached', 'unknown')
                print(f"   Cache status: {cached_status}")

        else:
            print(f"   ❌ First search failed: {response.status_code}")

    except Exception as e:
        print(f"   ❌ First search failed: {e}")
        return

    # Test 3: Second search (should be cache hit)
    print(f"\n3. Testing second search (should be cache hit)...")

    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data,
            timeout=30
        )
        second_search_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            search_results = result.get('search_results', [])
            print(f"   ✅ Second search completed in {second_search_time:.2f}s")
            print(f"   Found {len(search_results)} results")

            if search_results:
                second_result = search_results[0]
                cached_status = second_result.get('cached', 'unknown')
                cache_age = second_result.get('cache_age', 'unknown')
                print(f"   Cache status: {cached_status}")
                print(f"   Cache age: {cache_age}")

                # Check if it was faster (cache hit should be faster)
                speed_improvement = (
                    (first_search_time - second_search_time) / first_search_time) * 100
                print(f"   Speed improvement: {speed_improvement:.1f}%")

        else:
            print(f"   ❌ Second search failed: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Second search failed: {e}")

    # Test 4: Final cache stats
    print(f"\n4. Checking final cache stats...")
    try:
        response = requests.get(f"{base_url}/search_cache_stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Final cache stats:")
            print(f"      Total entries: {stats.get('total_entries', 0)}")
            print(f"      Active entries: {stats.get('active_entries', 0)}")
            print(f"      Total accesses: {stats.get('total_accesses', 0)}")
            print(
                f"      Avg accesses per entry: {stats.get('avg_accesses_per_entry', 0):.1f}")
        else:
            print(
                f"   ❌ Failed to get final cache stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Final cache stats failed: {e}")

    print(f"\n" + "=" * 60)
    print("🎯 Caching Test Summary:")
    print("   - First search should be slower (API call)")
    print("   - Second search should be faster (cache hit)")
    print("   - Cache stats should show 1 entry with 2 accesses")
    print("   - Results should be marked as cached=true on second call")


def test_different_ttl_queries():
    """Test different TTL based on query types"""

    print(f"\n🕒 Testing Different TTL for Query Types")
    print("=" * 60)

    base_url = "http://localhost:5001"

    test_queries = [
        ("latest news AI", "News query - should get 2h TTL"),
        ("NVIDIA stock price", "Stock query - should get 1h TTL"),
        ("best AI models comparison", "Review query - should get 7d TTL"),
        ("what is machine learning", "General query - should get 24h TTL")
    ]

    for query, description in test_queries:
        print(f"\n   Testing: {description}")
        try:
            chat_data = {
                "messages": [{"role": "user", "content": query}],
                "model": "gpt-4.1-nano",
                "enable_web_search": True,
                "max_tokens": 50
            }

            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=chat_data,
                timeout=30
            )

            if response.status_code == 200:
                print(f"   ✅ {query[:30]}... - processed successfully")
            else:
                print(f"   ❌ {query[:30]}... - failed: {response.status_code}")

        except Exception as e:
            print(f"   ❌ {query[:30]}... - error: {e}")


if __name__ == "__main__":
    print("🚀 Starting Web Search Caching Tests")
    print("Note: Requires server running and web search API key configured")

    # Test basic caching
    test_web_search_caching()

    # Test different TTL logic
    test_different_ttl_queries()

    print(f"\n🏁 Testing Complete!")
