#!/usr/bin/env python3
"""
Simple test for bilibili-api module.
"""

print("Testing bilibili-api import...")
try:
    from bilibili_api import video, sync
    print("✓ bilibili-api imported successfully")
except ImportError as e:
    print(f"✗ Failed to import bilibili-api: {e}")
    exit(1)

print("\nTesting Video class instantiation...")
try:
    v = video.Video(bvid="BV1GJ411x7h7")
    print("✓ Video instance created successfully")
except Exception as e:
    print(f"✗ Failed to create Video instance: {e}")
    exit(1)

print("\nTesting get_info() method...")
try:
    info = sync(v.get_info())
    print(f"✓ Video info retrieved successfully")
    print(f"  Title: {info.get('title', 'N/A')}")
    print(f"  Duration: {info.get('duration', 'N/A')} seconds")
except Exception as e:
    print(f"✗ Failed to get video info: {e}")
    print(f"  Error type: {type(e).__name__}")

print("\nTesting get_subtitle() method...")
try:
    subtitle_info = sync(v.get_subtitle(page_index=0))
    print(f"✓ Subtitle info retrieved")
    print(f"  Type: {type(subtitle_info)}")
    if isinstance(subtitle_info, dict):
        subtitles = subtitle_info.get('subtitles', [])
        print(f"  Subtitles count: {len(subtitles)}")
    else:
        print(f"  Content: {subtitle_info}")
except Exception as e:
    print(f"✗ Failed to get subtitle info: {e}")
    print(f"  Error type: {type(e).__name__}")

print("\nTest completed!")
