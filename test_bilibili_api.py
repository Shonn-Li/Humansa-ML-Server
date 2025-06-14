"""
Bilibili API Test Script

Installation requirements:
pip3 install bilibili-api-python
pip3 install aiohttp

Test script to verify bilibili-api-python functionality
"""

import asyncio
import sys
from typing import Dict, Any

# Test if bilibili_api is available
try:
    from bilibili_api import video
    print("✓ bilibili-api-python is installed")
except ImportError as e:
    print("✗ bilibili-api-python is not installed")
    print("Please install with: pip3 install bilibili-api-python")
    print("Also install: pip3 install aiohttp")
    sys.exit(1)

# Test if aiohttp is available
try:
    import aiohttp
    print("✓ aiohttp is installed")
except ImportError as e:
    print("✗ aiohttp is not installed")
    print("Please install with: pip3 install aiohttp")
    sys.exit(1)


async def test_video_info(bvid: str, description: str = "") -> Dict[str, Any]:
    """Test getting video information."""
    try:
        print(f"\n--- Testing {description} ({bvid}) ---")

        # Create video instance
        v = video.Video(bvid=bvid)

        # Get basic info
        print("Getting video info...")
        info = await v.get_info()

        # Print key information
        print(f"Title: {info.get('title', 'Unknown')}")
        print(f"Duration: {info.get('duration', 0)} seconds")
        print(f"View count: {info.get('stat', {}).get('view', 0)}")
        print(f"Upload date: {info.get('pubdate', 'Unknown')}")
        print(f"Description length: {len(info.get('desc', ''))}")

        # Test getting pages
        print("Getting video pages...")
        pages = await v.get_pages()
        print(f"Number of pages: {len(pages)}")
        if pages:
            print(f"First page CID: {pages[0].get('cid', 'Unknown')}")

        # Test getting subtitle info (may fail for some videos)
        try:
            print("Getting subtitle info...")
            if pages:
                cid = pages[0]['cid']
                subtitle_info = await v.get_subtitle(cid=cid)

                if subtitle_info and subtitle_info.get('subtitles'):
                    subtitles = subtitle_info.get('subtitles', [])
                    print(f"Available subtitles: {len(subtitles)}")
                    for i, sub in enumerate(subtitles[:3]):  # Show first 3
                        lang = sub.get('lan_doc', sub.get('lan', 'unknown'))
                        print(f"  Subtitle {i+1}: {lang}")
                else:
                    print("No subtitles available")
            else:
                print("Cannot get subtitles without pages")

        except Exception as e:
            print(
                f"Subtitle info failed (this is normal for many videos): {str(e)}")

        return {
            'success': True,
            'info': info,
            'pages': pages
        }

    except Exception as e:
        print(f"Error getting video info: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


async def main():
    """Main test function."""
    print("Bilibili API Test Script")
    print("=" * 50)

    # Test cases with different types of videos
    test_cases = [
        # Popular video from documentation
        ("BV1uv411q7Mv", "Documentation example video"),

        # Another test video (you can replace with any valid BV ID)
        ("BV1xx411c7mu", "Another test video"),

        # You can add more test cases here
        # ("BV1234567890", "Your test video"),
    ]

    results = []

    for bvid, description in test_cases:
        try:
            result = await test_video_info(bvid, description)
            results.append(result)

            # Add delay between requests to be respectful
            await asyncio.sleep(1)

        except Exception as e:
            print(f"Failed to test {bvid}: {str(e)}")
            results.append({'success': False, 'error': str(e)})

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    successful = sum(1 for r in results if r.get('success', False))
    print(f"Successful tests: {successful}/{len(results)}")

    if successful == 0:
        print("\n⚠️  All tests failed. Common issues:")
        print("1. Network connection problems")
        print("2. Bilibili API rate limiting")
        print("3. Invalid video IDs")
        print("4. Missing dependencies")
    elif successful == len(results):
        print("\n✅ All tests passed! Bilibili API is working correctly.")
    else:
        print(
            f"\n⚠️  {len(results) - successful} tests failed. Check individual errors above.")


async def test_url_parsing():
    """Test URL parsing functionality."""
    print("\n--- Testing URL Parsing ---")

    test_urls = [
        "https://www.bilibili.com/video/BV1uv411q7Mv",
        "https://bilibili.com/video/BV1xx411c7mu",
        "https://b23.tv/abc123",
        "https://m.bilibili.com/video/BV1234567890",
    ]

    import re

    def extract_bilibili_video_id(url: str) -> str:
        """Extract video ID from Bilibili URL."""
        patterns = [
            r'(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[A-Za-z0-9]+)',
            r'(?:https?://)?(?:www\.)?bilibili\.com/video/(av\d+)',
            r'(?:https?://)?(?:m\.)?bilibili\.com/video/(BV[A-Za-z0-9]+)',
            r'(?:https?://)?(?:m\.)?bilibili\.com/video/(av\d+)',
            r'(?:https?://)?b23\.tv/([A-Za-z0-9]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    for url in test_urls:
        video_id = extract_bilibili_video_id(url)
        print(f"URL: {url}")
        print(f"Extracted ID: {video_id}")
        print()


if __name__ == "__main__":
    print("Starting Bilibili API tests...")

    try:
        # Run URL parsing test
        asyncio.run(test_url_parsing())

        # Run main video tests
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
