#!/usr/bin/env python3
"""
Debug script to test bilibili-api module directly.
"""

import asyncio
from bilibili_api import video, sync
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


def test_bilibili_api_basic():
    """Test basic bilibili-api functionality."""
    print("=== Testing bilibili-api Basic Functionality ===")

    # Test with a known working video ID
    test_bvids = [
        "BV1GJ411x7h7",  # A popular tech video
        "BV1xx411c7mD",  # Another test video
        "BV1Yh411e7zZ",  # Another test video
    ]

    for bvid in test_bvids:
        print(f"\nTesting BVID: {bvid}")
        try:
            # Create video instance
            v = video.Video(bvid=bvid)

            # Get basic video info
            print("Getting video info...")
            info = sync(v.get_info())

            print(f"  Title: {info.get('title', 'N/A')}")
            print(f"  Duration: {info.get('duration', 'N/A')} seconds")
            print(f"  View count: {info.get('stat', {}).get('view', 'N/A')}")
            print(f"  Upload date: {info.get('pubdate', 'N/A')}")

            # Try to get subtitle info
            print("Getting subtitle info...")
            try:
                subtitle_info = sync(v.get_subtitle(page_index=0))
                print(f"  Subtitle info type: {type(subtitle_info)}")
                print(f"  Subtitle info: {subtitle_info}")

                if subtitle_info and isinstance(subtitle_info, dict):
                    subtitles = subtitle_info.get('subtitles', [])
                    print(f"  Number of subtitles: {len(subtitles)}")

                    if subtitles:
                        for i, subtitle in enumerate(subtitles):
                            print(f"    Subtitle {i+1}:")
                            print(
                                f"      Language: {subtitle.get('lan_doc', subtitle.get('lan', 'unknown'))}")
                            print(
                                f"      URL: {subtitle.get('subtitle_url', 'N/A')}")
                    else:
                        print("    No subtitles found in response")
                else:
                    print(
                        f"    Unexpected subtitle_info format: {subtitle_info}")

            except Exception as subtitle_error:
                print(f"  Subtitle error: {subtitle_error}")
                print(f"  Error type: {type(subtitle_error).__name__}")

        except Exception as e:
            print(f"  Error getting video info: {e}")
            print(f"  Error type: {type(e).__name__}")


def test_url_extraction():
    """Test URL extraction function."""
    print("\n=== Testing URL Extraction ===")

    from ai_chat_bot.link_analyzer import extract_bilibili_video_id, validate_bilibili_url

    test_urls = [
        "https://www.bilibili.com/video/BV1GJ411x7h7",
        "https://www.bilibili.com/video/av12345",
        "https://bilibili.com/video/BV1xx411c7mD",
        "https://m.bilibili.com/video/BV1Yh411e7zZ",
        "https://b23.tv/abc123",
    ]

    for url in test_urls:
        print(f"\nURL: {url}")
        print(f"  Valid: {validate_bilibili_url(url)}")
        print(f"  Video ID: {extract_bilibili_video_id(url)}")


if __name__ == "__main__":
    print("Debugging Bilibili API Integration")
    print("=" * 50)

    test_url_extraction()
    test_bilibili_api_basic()

    print("\n" + "=" * 50)
    print("Debug completed!")
