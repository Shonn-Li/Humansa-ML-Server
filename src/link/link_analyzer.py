"""
Link Analyzer for YouWoAI ML Server

This module provides content extraction for:
- YouTube videos (using youtube-transcript-api)
- Bilibili videos (using bilibili-api-python)
- General web pages (using LlamaIndex SpiderWebReader)
"""

import os
import re
import json
import asyncio
import requests
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing llama-index components
try:
    from llama_index.core import Document
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    # Fallback Document class
    class Document:
        def __init__(self, text: str, metadata: Optional[Dict] = None):
            self.text = text
            self.metadata = metadata or {}
    LLAMA_INDEX_AVAILABLE = False

# Try importing web reader
try:
    from llama_index.readers.web import SpiderWebReader
    SPIDER_WEB_READER_AVAILABLE = True
except ImportError:
    SPIDER_WEB_READER_AVAILABLE = False

# Direct API imports
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import WebshareProxyConfig

    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

try:
    from bilibili_api import video, sync
    BILIBILI_API_AVAILABLE = True
except ImportError:
    BILIBILI_API_AVAILABLE = False


def detect_platform_from_url(url: str) -> Optional[str]:
    """Detect platform from URL patterns."""
    url_lower = url.lower()

    # YouTube patterns
    if any(pattern in url_lower for pattern in ['youtube.com', 'youtu.be', 'm.youtube.com']):
        return 'youtube'

    # Bilibili patterns
    if any(pattern in url_lower for pattern in ['bilibili.com', 'b23.tv', 'm.bilibili.com']):
        return 'bilibili'

    return None


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\n?#]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([^&\n?#]+)',
        r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([^&\n?#]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_bilibili_video_id(url: str) -> Optional[str]:
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


def format_timestamp(seconds: float) -> str:
    """Format seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def analyze_youtube_content(url: str, languages: Optional[List[str]] = None) -> List[Document]:
    """Extract transcript with timestamps from YouTube video."""
    if not YOUTUBE_API_AVAILABLE:
        raise Exception(
            "YouTube Transcript API is not available. Please install youtube-transcript-api")

    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    if languages is None:
        languages = ['en']
    try:
        # Try to get transcript in preferred languages
        transcript_data = None
        used_language = None

        if os.getenv("PUBLIC_ENV") != "dev":
            logger.info(
                "Using WebshareProxyConfig for YouTube Transcript API")
            ytt_api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=os.getenv("WEBSHARE_PROXY_USERNAME"),
                    proxy_password=os.getenv("WEBSHARE_PROXY_PASSWORD"),
                )
            )
        else:
            ytt_api = YouTubeTranscriptApi()

        # Use the new API method (fetch) consistently
        try:
            # Try to fetch transcript with preferred languages
            fetched_transcript = ytt_api.fetch(video_id, languages=languages)
            transcript_data = fetched_transcript.to_raw_data()
            used_language = fetched_transcript.language_code
        except Exception:
            # If direct fetch fails, try listing available transcripts
            try:
                transcript_list = ytt_api.list(video_id)
                transcript = transcript_list.find_transcript(languages)
                fetched_transcript = transcript.fetch()
                transcript_data = fetched_transcript.to_raw_data()
                used_language = transcript.language_code
            except Exception:
                try:
                    # Try to find any available transcript
                    transcript_list = ytt_api.list(video_id)
                    transcript = next(iter(transcript_list))
                    fetched_transcript = transcript.fetch()
                    transcript_data = fetched_transcript.to_raw_data()
                    used_language = transcript.language_code
                except Exception as e:
                    raise Exception(
                        f"No transcript available for video {video_id}: {str(e)}")

        if not transcript_data:
            raise Exception(f"No transcript data found for video {video_id}")

        # Format transcript with timestamps
        formatted_segments = []
        for entry in transcript_data:
            start_time = entry.get('start', 0)
            duration = entry.get('duration', 0)
            text = entry.get('text', '').strip()

            timestamp = format_timestamp(start_time)
            formatted_segments.append({
                'timestamp': timestamp,
                'start_seconds': start_time,
                'duration': duration,
                'text': text
            })

        # Create formatted content
        formatted_content = []
        for segment in formatted_segments:
            formatted_content.append(
                f"[{segment['timestamp']}] {segment['text']}")

        full_content = '\n'.join(formatted_content)

        # Create document with metadata
        document = Document(
            text=full_content,
            metadata={
                'video_id': video_id,
                'platform': 'youtube',
                'language': used_language,
                'url': url,
                'total_segments': len(transcript_data),
                'format': 'timestamped_transcript',
                'segments': formatted_segments
            }
        )

        return [document]

    except Exception as e:
        raise Exception(f"Failed to extract YouTube transcript: {str(e)}")


async def get_bilibili_subtitle_content(video_obj, video_id: str) -> Dict[str, Any]:
    """Get Bilibili subtitle content with proper async handling."""
    try:
        # Get video info
        info = await asyncio.wait_for(video_obj.get_info(), timeout=15)
        title = info.get('title', 'Unknown Title')

        # Get pages to obtain cid
        pages = await asyncio.wait_for(video_obj.get_pages(), timeout=15)
        if not pages:
            return {
                'success': False,
                'title': title,
                'message': 'No video pages found'
            }

        cid = pages[0]['cid']

        # Get subtitle info using cid
        subtitle_info = await asyncio.wait_for(video_obj.get_subtitle(cid=cid), timeout=15)

        if not subtitle_info or not isinstance(subtitle_info, dict) or not subtitle_info.get('subtitles'):
            return {
                'success': False,
                'title': title,
                'message': 'No subtitles available for this video'
            }

        # Get first available subtitle
        subtitles = subtitle_info.get('subtitles', [])
        subtitle = subtitles[0]
        subtitle_url = subtitle.get('subtitle_url', '')
        lang = subtitle.get('lan_doc', subtitle.get('lan', 'unknown'))

        if not subtitle_url:
            return {
                'success': False,
                'title': title,
                'message': 'No subtitle URL found'
            }

        # Fix URL format
        if subtitle_url.startswith('//'):
            subtitle_url = 'https:' + subtitle_url

        # Fetch subtitle content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'application/json, text/plain, */*'
        }

        response = requests.get(subtitle_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return {
                'success': False,
                'title': title,
                'message': f'Failed to fetch subtitle: HTTP {response.status_code}'
            }

        subtitle_data = response.json()
        body = subtitle_data.get('body', [])

        if not body:
            return {
                'success': False,
                'title': title,
                'message': 'Subtitle file contains no content'
            }

        return {
            'success': True,
            'title': title,
            'language': lang,
            'subtitle_data': body,
            'info': info
        }

    except asyncio.TimeoutError:
        raise Exception("Timeout while fetching Bilibili content")
    except Exception as e:
        error_msg = str(e).lower()
        if "credential" in error_msg or "sessdata" in error_msg:
            raise Exception(
                "Bilibili subtitle access requires authentication. Many videos have subtitles that are only accessible when logged in.")
        elif "需要 cid" in str(e):
            raise Exception(
                "Bilibili API requires video page information (cid) to access subtitles.")
        else:
            raise Exception(f"Failed to get Bilibili content: {str(e)}")


def analyze_bilibili_content(url: str) -> List[Document]:
    """Extract transcript with timestamps from Bilibili video."""
    if not BILIBILI_API_AVAILABLE:
        error_msg = "Bilibili API is not available. Please install bilibili-api-python"
        document = Document(
            text=f"Bilibili video analysis is currently unavailable.\n\nURL: {url}\n\nError: {error_msg}",
            metadata={
                'platform': 'bilibili',
                'url': url,
                'error': 'dependency_unavailable',
                'format': 'error_message'
            }
        )
        return [document]

    video_id = extract_bilibili_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    try:
        # Create video object
        if video_id.startswith('av'):
            aid = int(video_id[2:])
            v = video.Video(aid=aid)
        else:
            v = video.Video(bvid=video_id)

        # Get subtitle content with proper async handling
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, use thread executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            get_bilibili_subtitle_content(v, video_id))
                    )
                    result = future.result(timeout=30)
            else:
                result = loop.run_until_complete(
                    get_bilibili_subtitle_content(v, video_id))
        except RuntimeError:
            # No event loop, create new one
            result = asyncio.run(get_bilibili_subtitle_content(v, video_id))

        if not result['success']:
            # Create document explaining the issue
            document = Document(
                text=f"No subtitles available for this Bilibili video.\n\nTitle: {result['title']}\nVideo ID: {video_id}\n\n{result['message']}",
                metadata={
                    'video_id': video_id,
                    'platform': 'bilibili',
                    'url': url,
                    'title': result['title'],
                    'subtitle_available': False,
                    'format': 'no_subtitles'
                }
            )
            return [document]

        # Format subtitle with timestamps
        formatted_segments = []
        formatted_content = []

        for entry in result['subtitle_data']:
            from_time = entry.get('from', 0)
            to_time = entry.get('to', 0)
            content = entry.get('content', '').strip()

            if content:
                start_timestamp = format_timestamp(from_time)
                end_timestamp = format_timestamp(to_time)

                formatted_segments.append({
                    'start_timestamp': start_timestamp,
                    'end_timestamp': end_timestamp,
                    'start_seconds': from_time,
                    'end_seconds': to_time,
                    'duration': to_time - from_time,
                    'text': content
                })

                formatted_content.append(
                    f"[{start_timestamp} - {end_timestamp}] {content}")

        if not formatted_content:
            raise Exception("No valid subtitle content found")

        full_content = '\n'.join(formatted_content)

        # Create document with metadata
        document = Document(
            text=full_content,
            metadata={
                'video_id': video_id,
                'platform': 'bilibili',
                'language': result['language'],
                'url': url,
                'title': result['title'],
                'total_segments': len(formatted_segments),
                'subtitle_available': True,
                'format': 'timestamped_transcript',
                'segments': formatted_segments,
                'duration': result['info'].get('duration', 0),
                'view_count': result['info'].get('stat', {}).get('view', 0)
            }
        )

        return [document]

    except Exception as e:
        raise Exception(f"Failed to extract Bilibili content: {str(e)}")


def analyze_web_content(url: str, spider_api_key: Optional[str] = None) -> List[Document]:
    """Extract content from general web pages using Spider."""
    if not SPIDER_WEB_READER_AVAILABLE:
        raise Exception(
            "SpiderWebReader is not available. Please install llama-index-readers-web")

    # Get API key from environment if not provided
    if spider_api_key is None:
        spider_api_key = os.getenv("SPIDER_API_KEY")

    if not spider_api_key:
        raise ValueError(
            "Spider API key is required. Set SPIDER_API_KEY environment variable")

    try:
        reader = SpiderWebReader(api_key=spider_api_key, mode="scrape")
        documents = reader.load_data(url=url)
        return documents
    except Exception as e:
        raise Exception(f"Failed to extract web content: {str(e)}")


def analyze_link(url: str, platform: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze a link and extract content based on platform.

    Args:
        url: The URL to analyze
        platform: Platform type ('youtube', 'bilibili', 'web'). If None, will auto-detect
        options: Additional options including:
            - languages: Language codes for YouTube transcript (default: ['en'])
            - spider_api_key: Spider API key for web content extraction

    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - platform: Detected or specified platform
        - data: Content data with title, content, metadata
        - error: Error message if failed
        - suggestions: List of suggestions if failed
    """
    if options is None:
        options = {}

    languages = options.get("languages", ["en"])
    spider_api_key = options.get(
        "spider_api_key") or os.getenv("SPIDER_API_KEY")

    result = {
        "success": False,
        "platform": platform,
        "data": None,
        "error": None,
        "suggestions": []
    }

    try:
        # Auto-detect platform if not specified
        if platform is None:
            detected_platform = detect_platform_from_url(url)
            if detected_platform:
                platform = detected_platform
                result["platform"] = platform
            else:
                platform = "web"
                result["platform"] = platform

        # Extract content based on platform
        if platform == "youtube":
            if not YOUTUBE_API_AVAILABLE:
                result["error"] = "missing_dependency"
                result["suggestions"] = [
                    "YouTube API is not available",
                    "Install youtube-transcript-api: pip install youtube-transcript-api"
                ]
                return result
            documents = analyze_youtube_content(url, languages)

        elif platform == "bilibili":
            documents = analyze_bilibili_content(url)

        elif platform == "web":
            if not SPIDER_WEB_READER_AVAILABLE:
                result["error"] = "missing_dependency"
                result["suggestions"] = [
                    "Web reader is not available",
                    "Install llama-index-readers-web: pip install llama-index-readers-web"
                ]
                return result
            if not spider_api_key:
                result["error"] = "missing_api_key"
                result["suggestions"] = [
                    "Set SPIDER_API_KEY in your environment variables",
                    "Get an API key from spider.cloud"
                ]
                return result
            documents = analyze_web_content(url, spider_api_key)

        else:
            raise ValueError(f"Unsupported platform: {platform}")

        # Process results
        if documents:
            doc = documents[0]
            result["data"] = {
                "title": doc.metadata.get("title", doc.metadata.get("video_id", "Extracted Content")),
                "content": doc.text,
                "url": url,
                "metadata": doc.metadata
            }

            # Add language info for transcripts
            if platform in ["youtube", "bilibili"]:
                result["data"]["language"] = doc.metadata.get(
                    "language", "unknown")

        result["success"] = True

    except ValueError as e:
        result["error"] = "invalid_input"
        result["suggestions"] = [str(e)]
    except Exception as e:
        error_msg = str(e).lower()

        if "transcript" in error_msg or "subtitle" in error_msg:
            result["error"] = "extraction_failed"
            if platform == "youtube":
                result["suggestions"] = [
                    "Check if the video has captions/transcripts available",
                    "Try a different language option",
                    "Verify the video ID is correct"
                ]
            elif platform == "bilibili":
                result["suggestions"] = [
                    "This video may not have auto-generated subtitles",
                    "Try a different Bilibili video with manual captions"
                ]
        elif "dependency" in error_msg or "not available" in error_msg:
            result["error"] = "missing_dependency"
            result["suggestions"] = [
                "Install required dependencies",
                "Check Python environment setup"
            ]
        else:
            result["error"] = "extraction_failed"
            result["suggestions"] = [
                "Check if the URL is accessible",
                "Verify the content format is supported",
                f"Original error: {str(e)}"
            ]

    return result


if __name__ == "__main__":
    # Test with a YouTube video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print("Testing YouTube analysis...")
    result = analyze_link(test_url)
    print(f"Platform: {result['platform']}")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Title: {result['data']['title']}")
        print(f"Content length: {len(result['data']['content'])}")
    else:
        print(f"Error: {result['error']}")
        print(f"Suggestions: {result['suggestions']}")
