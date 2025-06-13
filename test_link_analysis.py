#!/usr/bin/env python3
"""
Test script for the link analysis endpoint
"""
import requests
import json
import sys


def test_youtube_link():
    """Test YouTube link analysis"""
    url = "http://localhost:5001/analyze_link"

    # Test with a known YouTube video that has transcripts
    payload = {
        "link": "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "options": {
            "languages": ["en"]
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"YouTube Test - Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running on port 5001.")
        return False
    except Exception as e:
        print(f"Error testing YouTube link: {e}")
        return False


def test_web_link():
    """Test web link analysis"""
    url = "http://localhost:5001/analyze_link"

    # Test with Wikipedia (should work with Spider API)
    payload = {
        "link": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "platform": "web"
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Web Test - Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running on port 5001.")
        return False
    except Exception as e:
        print(f"Error testing web link: {e}")
        return False


def test_auto_detection():
    """Test platform auto-detection"""
    url = "http://localhost:5001/analyze_link"

    # Test auto-detection with YouTube URL
    payload = {
        "link": "https://youtu.be/dQw4w9WgXcQ"
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Auto-detection Test - Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running on port 5001.")
        return False
    except Exception as e:
        print(f"Error testing auto-detection: {e}")
        return False


def main():
    print("=== Link Analysis API Test ===\n")

    tests = [
        ("YouTube Analysis", test_youtube_link),
        ("Web Analysis", test_web_link),
        ("Auto-detection", test_auto_detection)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        result = test_func()
        results.append((test_name, result))
        print(f"{test_name}: {'PASSED' if result else 'FAILED'}")
        print("-" * 50)

    print("\n=== Test Summary ===")
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the server logs and configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
