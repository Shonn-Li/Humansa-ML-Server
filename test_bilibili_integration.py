#!/usr/bin/env python3
"""
Test script for Bilibili integration using bilibili-api-python module.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ai_chat_bot.link_analyzer import analyze_link, analyze_bilibili_content

def test_bilibili_url_detection():
    """Test Bilibili URL pattern detection and validation."""
    print("=== Testing Bilibili URL Detection ===")
    
    test_urls = [
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://bilibili.com/video/BV1Yh411e7zZ",
        "https://m.bilibili.com/video/BV1GJ411x7h7",
        "https://b23.tv/abc123",
        "https://www.bilibili.com/video/av12345",
    ]
    
    for url in test_urls:
        result = analyze_link(url)
        print(f"URL: {url}")
        print(f"  Platform detected: {result['platform']}")
        print(f"  Success: {result['success']}")
        if not result['success']:
            print(f"  Error: {result['error']}")
            print(f"  Suggestions: {result['suggestions']}")
        print()

def test_bilibili_video_with_subtitles():
    """Test a known Bilibili video that should have subtitles."""
    print("=== Testing Bilibili Video with Subtitles ===")
    
    # Using a popular tech review video that likely has subtitles
    test_url = "https://www.bilibili.com/video/BV1GJ411x7h7"
    
    try:
        result = analyze_link(test_url, platform="bilibili")
        
        print(f"URL: {test_url}")
        print(f"Platform: {result['platform']}")
        print(f"Success: {result['success']}")
        
        if result['success'] and result['data']:
            data = result['data']
            print(f"Title: {data.get('title', 'N/A')}")
            print(f"Language: {data.get('language', 'N/A')}")
            print(f"Content length: {len(data.get('content', ''))}")
            
            content = data.get('content', '')
            if content:
                lines = content.split('\n')
                print(f"Total lines: {len(lines)}")
                print("First few lines:")
                for i, line in enumerate(lines[:5]):
                    print(f"  {i+1}: {line}")
                print("...")
                print("Last few lines:")
                for i, line in enumerate(lines[-3:]):
                    print(f"  {len(lines)-3+i+1}: {line}")
            
            metadata = data.get('metadata', {})
            print(f"Subtitle available: {metadata.get('subtitle_available', False)}")
            print(f"Total segments: {metadata.get('total_segments', 0)}")
            print(f"Video ID: {metadata.get('video_id', 'N/A')}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Suggestions: {result.get('suggestions', [])}")
            
    except Exception as e:
        print(f"Exception occurred: {e}")

def test_bilibili_video_without_subtitles():
    """Test a Bilibili video that likely doesn't have subtitles."""
    print("=== Testing Bilibili Video without Subtitles ===")
    
    # Using a random video URL that might not have subtitles
    test_url = "https://www.bilibili.com/video/BV1xx411c7mD"
    
    try:
        result = analyze_link(test_url, platform="bilibili")
        
        print(f"URL: {test_url}")
        print(f"Platform: {result['platform']}")
        print(f"Success: {result['success']}")
        
        if result['success'] and result['data']:
            data = result['data']
            print(f"Title: {data.get('title', 'N/A')}")
            content = data.get('content', '')
            print(f"Content: {content[:200]}...")
            
            metadata = data.get('metadata', {})
            print(f"Subtitle available: {metadata.get('subtitle_available', False)}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Suggestions: {result.get('suggestions', [])}")
            
    except Exception as e:
        print(f"Exception occurred: {e}")

def test_auto_detection():
    """Test automatic platform detection for Bilibili URLs."""
    print("=== Testing Auto-Detection ===")
    
    test_urls = [
        "https://www.bilibili.com/video/BV1GJ411x7h7",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://github.com",
    ]
    
    for url in test_urls:
        result = analyze_link(url)  # No platform specified
        print(f"URL: {url}")
        print(f"  Detected platform: {result['platform']}")
        print(f"  Success: {result['success']}")
        print()

if __name__ == "__main__":
    print("Testing Bilibili Integration with bilibili-api-python")
    print("=" * 60)
    
    # Run all tests
    test_bilibili_url_detection()
    test_auto_detection()
    test_bilibili_video_with_subtitles()
    test_bilibili_video_without_subtitles()
    
    print("=" * 60)
    print("Testing completed!")
