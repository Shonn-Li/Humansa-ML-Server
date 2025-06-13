#!/usr/bin/env python3
"""
Test the analyze_link endpoint via HTTP requests.
"""

import requests
import json

SERVER_URL = "http://127.0.0.1:5003"

def test_youtube_endpoint():
    """Test YouTube link analysis via HTTP endpoint."""
    print("=== Testing YouTube Link Analysis ===")
    
    payload = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "platform": "youtube",
        "options": {
            "languages": ["en"]
        }
    }
    
    try:
        response = requests.post(
            f"{SERVER_URL}/analyze_link",
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            print(f"Platform: {result.get('platform', 'N/A')}")
            
            if result.get('success') and result.get('data'):
                data = result['data']
                print(f"Title: {data.get('title', 'N/A')}")
                print(f"Language: {data.get('language', 'N/A')}")
                content = data.get('content', '')
                if content:
                    lines = content.split('\n')
                    print(f"Content lines: {len(lines)}")
                    print("First few lines:")
                    for line in lines[:3]:
                        print(f"  {line}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
                print(f"Suggestions: {result.get('suggestions', [])}")
        else:
            print(f"HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def test_bilibili_endpoint():
    """Test Bilibili link analysis via HTTP endpoint."""
    print("\n=== Testing Bilibili Link Analysis ===")
    
    payload = {
        "url": "https://www.bilibili.com/video/BV1GJ411x7h7",
        "platform": "bilibili"
    }
    
    try:
        response = requests.post(
            f"{SERVER_URL}/analyze_link",
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            print(f"Platform: {result.get('platform', 'N/A')}")
            
            if result.get('success') and result.get('data'):
                data = result['data']
                print(f"Title: {data.get('title', 'N/A')}")
                print(f"Language: {data.get('language', 'N/A')}")
                content = data.get('content', '')
                print(f"Content length: {len(content)}")
                if content:
                    lines = content.split('\n')
                    print(f"Content lines: {len(lines)}")
                    print("First few lines:")
                    for line in lines[:3]:
                        print(f"  {line}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
                print(f"Suggestions: {result.get('suggestions', [])}")
        else:
            print(f"HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def test_auto_detection():
    """Test auto-detection functionality."""
    print("\n=== Testing Auto-Detection ===")
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.bilibili.com/video/BV1GJ411x7h7",
        "https://github.com"
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        payload = {"url": url}  # No platform specified
        
        try:
            response = requests.post(
                f"{SERVER_URL}/analyze_link",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  Detected platform: {result.get('platform', 'N/A')}")
                print(f"  Success: {result.get('success', False)}")
                if not result.get('success'):
                    print(f"  Error: {result.get('error', 'N/A')}")
            else:
                print(f"  HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"  Request failed: {e}")

if __name__ == "__main__":
    print("Testing Analyze Link Endpoint")
    print("=" * 50)
    
    # Test YouTube functionality
    test_youtube_endpoint()
    
    # Test Bilibili functionality  
    test_bilibili_endpoint()
    
    # Test auto-detection
    test_auto_detection()
    
    print("\n" + "=" * 50)
    print("Endpoint testing completed!")
