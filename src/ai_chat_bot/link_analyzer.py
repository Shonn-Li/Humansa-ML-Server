import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import json

from llama_index.core import Document
from llama_index.readers.web import SpiderWebReader

# Direct API imports
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import asyncio
try:
    from bilibili_api import video, sync
    BILIBILI_API_AVAILABLE = True
except ImportError:
    BILIBILI_API_AVAILABLE = False


def detect_platform_from_url(url: str) -> Optional[str]:
    """
    Detect platform from URL patterns.

    Args:
        url: The URL to analyze

    Returns:
        Platform name ('youtube', 'bilibili') or None if not detected
    """
    url_lower = url.lower()

    # YouTube patterns
    youtube_patterns = [
        'youtube.com',
        'youtu.be',
        'm.youtube.com'
    ]

    # Bilibili patterns
    bilibili_patterns = [
        'bilibili.com',
        'b23.tv',
        'm.bilibili.com'
    ]

    for pattern in youtube_patterns:
        if pattern in url_lower:
            return 'youtube'

    for pattern in bilibili_patterns:
        if pattern in url_lower:
            return 'bilibili'

    return None


def validate_youtube_url(url: str) -> bool:
    """
    Validate if the URL is a proper YouTube video URL.

    Args:
        url: YouTube URL to validate

    Returns:
        True if valid YouTube URL, False otherwise
    """
    youtube_regex = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
    return bool(re.match(youtube_regex, url))


def validate_bilibili_url(url: str) -> bool:
    """
    Validate if the URL is a proper Bilibili video URL.

    Args:
        url: Bilibili URL to validate

    Returns:
        True if valid Bilibili URL, False otherwise
    """
    bilibili_patterns = [
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/[a-zA-Z0-9]+',
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/BV[a-zA-Z0-9]+',
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/av\d+',
        r'(?:https?://)?(?:m\.)?bilibili\.com/video/[a-zA-Z0-9]+',
        r'(?:https?://)?b23\.tv/[a-zA-Z0-9]+'
    ]

    for pattern in bilibili_patterns:
        if re.match(pattern, url):
            return True
    return False


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.

    Args:
        url: YouTube video URL

    Returns:
        Video ID or None if not found
    """
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
    """
    Extract video ID from Bilibili URL.

    Args:
        url: Bilibili video URL

    Returns:
        Video ID (BV number or av number) or None if not found
    """
    patterns = [
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[A-Za-z0-9]+)',
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/(av\d+)',
        r'(?:https?://)?(?:m\.)?bilibili\.com/video/(BV[A-Za-z0-9]+)',
        r'(?:https?://)?(?:m\.)?bilibili\.com/video/(av\d+)',
        r'(?:https?://)?b23\.tv/([A-Za-z0-9]+)'  # Short URL format
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Convert av number to BV if needed
            if video_id.startswith('av'):
                # For now, return the av number as is, bilibili-api can handle both
                return video_id
            return video_id
    return None


def format_timestamp(seconds: float) -> str:
    """
    Format seconds to MM:SS or HH:MM:SS format.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def analyze_youtube_content(url: str, languages: Optional[List[str]] = None) -> List[Document]:
    """
    Extract transcript with timestamps from YouTube video using direct API.

    Args:
        url: YouTube video URL
        languages: List of language codes to try for transcript (default: ['en'])

    Returns:
        List of Document objects containing the transcript with timestamps
    """
    if not validate_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    if languages is None:
        languages = ['en']

    try:
        # Try to get transcript in preferred languages
        transcript_data = None
        used_language = None

        for lang in languages:
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=[lang])
                used_language = lang
                break
            except Exception:
                continue

        # If no specific language worked, try to get any available transcript
        if transcript_data is None:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(
                    video_id)
                transcript = transcript_list.find_generated_transcript(['en'])
                transcript_data = transcript.fetch()
                used_language = 'en'
            except Exception:
                try:
                    # Try any available transcript
                    transcript_list = YouTubeTranscriptApi.list_transcripts(
                        video_id)
                    transcript = next(iter(transcript_list))
                    transcript_data = transcript.fetch()
                    used_language = transcript.language_code
                except Exception as e:
                    raise Exception(
                        f"No transcript available for video {video_id}: {str(e)}")

        if not transcript_data:
            raise Exception(f"No transcript data found for video {video_id}")

        # Format transcript with timestamps
        formatted_content = []
        for entry in transcript_data:
            start_time = entry.get('start', 0)
            duration = entry.get('duration', 0)
            text = entry.get('text', '').strip()

            timestamp = format_timestamp(start_time)
            formatted_content.append(f"[{timestamp}] {text}")

        # Join all content
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
                'format': 'timestamped_transcript'
            }
        )

        return [document]

    except Exception as e:
        raise Exception(f"Failed to extract YouTube transcript: {str(e)}")


async def get_bilibili_video_info_async(video_obj, video_id: str, timeout: int = 15):
    """
    Get Bilibili video info asynchronously with proper error handling.
    """
    try:
        info = await asyncio.wait_for(video_obj.get_info(), timeout=timeout)
        return info
    except asyncio.TimeoutError:
        raise Exception(
            "Timeout while fetching video information from Bilibili")
    except Exception as e:
        error_msg = str(e).lower()
        if "403" in error_msg or "401" in error_msg:
            raise Exception(
                f"Access denied. Video may be private, region-locked, or deleted. Video ID: {video_id}")
        elif "404" in error_msg:
            raise Exception(
                f"Video not found. Video may have been deleted or the ID is incorrect. Video ID: {video_id}")
        else:
            raise Exception(
                f"Cannot access video information. Error: {str(e)}")


async def get_bilibili_subtitle_info_async(video_obj, video_id: str, timeout: int = 15):
    """
    Get Bilibili subtitle info asynchronously with proper error handling.
    """
    try:
        subtitle_info = await asyncio.wait_for(video_obj.get_subtitle(page_index=0), timeout=timeout)
        return subtitle_info
    except asyncio.TimeoutError:
        raise Exception(
            "Timeout while fetching subtitle information from Bilibili")
    except Exception as e:
        raise Exception(f"Failed to get subtitle info: {str(e)}")


def analyze_bilibili_content(url: str) -> List[Document]:
    """
    Extract transcript with timestamps from Bilibili video using bilibili-api module.

    Args:
        url: Bilibili video URL

    Returns:
        List of Document objects containing the transcript with timestamps
    """
    if not BILIBILI_API_AVAILABLE:
        raise Exception(
            "bilibili-api-python module is not available. Please install it with: pip install bilibili-api-python")

    if not validate_bilibili_url(url):
        raise ValueError(f"Invalid Bilibili URL: {url}")

    video_id = extract_bilibili_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    try:
        # Handle both BV and av format video IDs
        if video_id.startswith('av'):
            # Convert av to aid (numeric part)
            aid = int(video_id[2:])
            v = video.Video(aid=aid)
        else:
            # BV format
            v = video.Video(bvid=video_id)

        # Get video info using async with proper event loop handling
        loop = None
        try:
            # Check if there's already an event loop running
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to use run_in_executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            get_bilibili_video_info_async(v, video_id))
                    )
                    info = future.result(timeout=20)
            else:
                info = loop.run_until_complete(
                    get_bilibili_video_info_async(v, video_id))
        except RuntimeError:
            # No event loop, create a new one
            info = asyncio.run(get_bilibili_video_info_async(v, video_id))

        title = info.get('title', 'Unknown Title')

        # Try to get subtitles/closed captions
        try:
            # Get subtitle info using async
            loop = None
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(
                                get_bilibili_subtitle_info_async(v, video_id))
                        )
                        subtitle_info = future.result(timeout=20)
                else:
                    subtitle_info = loop.run_until_complete(
                        get_bilibili_subtitle_info_async(v, video_id))
            except RuntimeError:
                subtitle_info = asyncio.run(
                    get_bilibili_subtitle_info_async(v, video_id))

            if not subtitle_info or not isinstance(subtitle_info, dict) or not subtitle_info.get('subtitles'):
                # No subtitles available - create document with this info
                document = Document(
                    text=f"No subtitles available for this Bilibili video.\n\nTitle: {title}\nVideo ID: {video_id}\n\nThis video may not have auto-generated subtitles or manual captions.",
                    metadata={
                        'video_id': video_id,
                        'platform': 'bilibili',
                        'url': url,
                        'title': title,
                        'subtitle_available': False,
                        'format': 'no_subtitles'
                    }
                )
                return [document]

            # Process available subtitles
            subtitles = subtitle_info.get('subtitles', [])
            if not subtitles:
                raise Exception("No subtitle data found in response")

            # Get the first available subtitle (usually Chinese or English)
            subtitle = subtitles[0]
            subtitle_url = subtitle.get('subtitle_url', '')
            lang = subtitle.get('lan_doc', subtitle.get('lan', 'unknown'))

            if not subtitle_url:
                raise Exception("No subtitle URL found")

            # Fix URL format if needed
            if subtitle_url.startswith('//'):
                subtitle_url = 'https:' + subtitle_url

            # Fetch subtitle content with proper headers and timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
            }

            subtitle_response = requests.get(
                subtitle_url, headers=headers, timeout=30)
            if subtitle_response.status_code != 200:
                raise Exception(
                    f"Failed to fetch subtitle content: HTTP {subtitle_response.status_code}")

            try:
                subtitle_data = subtitle_response.json()
            except ValueError as json_error:
                raise Exception(
                    f"Invalid JSON response from subtitle URL: {str(json_error)}")

            # Format subtitle with timestamps
            formatted_content = []
            body = subtitle_data.get('body', [])

            if not body:
                raise Exception("Subtitle file contains no content")

            for entry in body:
                from_time = entry.get('from', 0)
                to_time = entry.get('to', 0)
                content = entry.get('content', '').strip()

                if content:  # Only include non-empty content
                    start_timestamp = format_timestamp(from_time)
                    end_timestamp = format_timestamp(to_time)
                    formatted_content.append(
                        f"[{start_timestamp} - {end_timestamp}] {content}")

            if not formatted_content:
                raise Exception("No valid subtitle content found in file")

            full_content = '\n'.join(formatted_content)

            # Create document with metadata
            document = Document(
                text=full_content,
                metadata={
                    'video_id': video_id,
                    'platform': 'bilibili',
                    'language': lang,
                    'url': url,
                    'title': title,
                    'total_segments': len(body),
                    'subtitle_available': True,
                    'format': 'timestamped_transcript',
                    'duration': info.get('duration', 0),
                    'view_count': info.get('stat', {}).get('view', 0)
                }
            )

            return [document]

        except Exception as subtitle_error:
            # If subtitle extraction fails, provide detailed error info
            error_msg = str(subtitle_error).lower()

            if "not found" in error_msg or "empty" in error_msg:
                # Create document indicating no subtitles
                document = Document(
                    text=f"No subtitles available for this Bilibili video.\n\nTitle: {title}\nVideo ID: {video_id}\n\nThis video does not have subtitles or closed captions available. Many Bilibili videos rely on user-generated content and may not have auto-generated subtitles.",
                    metadata={
                        'video_id': video_id,
                        'platform': 'bilibili',
                        'url': url,
                        'title': title,
                        'subtitle_available': False,
                        'format': 'no_subtitles',
                        'duration': info.get('duration', 0),
                        'view_count': info.get('stat', {}).get('view', 0)
                    }
                )
                return [document]
            else:
                raise Exception(
                    f"Failed to extract Bilibili subtitles: {str(subtitle_error)}")

    except Exception as e:
        # Provide more helpful error messages
        error_msg = str(e).lower()

        if "http" in error_msg and ("403" in error_msg or "401" in error_msg):
            raise Exception(
                f"Access denied when fetching Bilibili content. This could be due to: "
                f"1) The video is region-locked or private, "
                f"2) API rate limiting, "
                f"3) Network connectivity issues. "
                f"Video ID: {video_id}. Original error: {str(e)}"
            )
        elif "no subtitle" in error_msg or "subtitles" in error_msg:
            raise Exception(
                f"No subtitles available for this Bilibili video. "
                f"Many Bilibili videos don't have auto-generated subtitles or closed captions. "
                f"Try a different video that has manual captions. "
                f"Video ID: {video_id}"
            )
        elif "network" in error_msg or "connection" in error_msg:
            raise Exception(
                f"Network error when accessing Bilibili API. "
                f"Please check your internet connection and try again. "
                f"Video ID: {video_id}"
            )
        else:
            raise Exception(f"Failed to extract Bilibili content: {str(e)}")


def analyze_web_content(url: str, spider_api_key: Optional[str] = None) -> List[Document]:
    """
    Extract content from general web pages using Spider.

    Args:
        url: Web page URL
        spider_api_key: Spider API key (can be None if set in environment)

    Returns:
        List of Document objects containing the web content
    """
    # Get API key from environment if not provided
    if spider_api_key is None:
        spider_api_key = os.getenv("SPIDER_API_KEY")

    if not spider_api_key:
        raise ValueError(
            "Spider API key is required. Set SPIDER_API_KEY environment variable or provide api_key parameter")

    try:
        reader = SpiderWebReader(
            api_key=spider_api_key,
            mode="scrape"
        )
        documents = reader.load_data(url=url)
        return documents
    except Exception as e:
        raise Exception(f"Failed to extract web content: {str(e)}")


def analyze_link(
    url: str,
    platform: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
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
                # Default to web content extraction
                platform = "web"
                result["platform"] = platform

        # Extract content based on platform
        if platform == "youtube":
            documents = analyze_youtube_content(url, languages)
        elif platform == "bilibili":
            documents = analyze_bilibili_content(url)
        elif platform == "web":
            if not spider_api_key:
                result["error"] = "missing_dependency"
                result["suggestions"] = [
                    "Set SPIDER_API_KEY in your environment variables",
                    "Get an API key from spider.cloud"
                ]
                return result
            documents = analyze_web_content(url, spider_api_key)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        # Convert documents to serializable format
        if documents:
            # Extract content and metadata from first document
            doc = documents[0]
            result["data"] = {
                "title": doc.metadata.get("title", "Extracted Content"),
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

        # Categorize errors and provide helpful suggestions
        if "transcript" in error_msg or "subtitle" in error_msg:
            result["error"] = "extraction_failed"
            if platform == "youtube":
                result["suggestions"] = [
                    "Check if the video ID is correct",
                    "Verify the video has captions/transcripts available",
                    "Try a different language option"
                ]
            elif platform == "bilibili":
                result["suggestions"] = [
                    "This video may not have auto-generated subtitles",
                    "Check if manual subtitles are available",
                    "Try a different Bilibili video"
                ]
        elif "api" in error_msg or "key" in error_msg:
            result["error"] = "api_error"
            result["suggestions"] = [
                "Check your API key configuration",
                "Verify API quotas and limits"
            ]
        elif "dependency" in error_msg or "import" in error_msg:
            result["error"] = "missing_dependency"
            result["suggestions"] = [
                "Install required dependencies",
                "Check Python environment compatibility"
            ]
        else:
            result["error"] = "extraction_failed"
            result["suggestions"] = [
                "Check if the URL is accessible",
                "Verify the content format is supported"
            ]

    return result


def format_content_for_analysis(documents: List[Document]) -> str:
    """
    Format document content for further analysis or storage.

    Args:
        documents: List of Document objects

    Returns:
        Formatted text content
    """
    if not documents:
        return ""

    content_parts = []

    for i, doc in enumerate(documents):
        content_parts.append(f"--- Document {i + 1} ---")
        content_parts.append(doc.text)

        # Add metadata if available
        if doc.metadata:
            metadata_str = []
            for key, value in doc.metadata.items():
                if value:  # Only include non-empty metadata
                    metadata_str.append(f"{key}: {value}")

            if metadata_str:
                content_parts.append(f"Metadata: {', '.join(metadata_str)}")

        content_parts.append("")  # Empty line between documents

    return "\n".join(content_parts)


# Example usage and testing
if __name__ == "__main__":
    # Test YouTube analysis
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print("Testing YouTube analysis...")
    result = analyze_link(youtube_url, platform="youtube")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Content: {format_content_for_analysis(result['content'])}")
    else:
        print(f"Error: {result['error']}")

    # Test auto-detection
    print("\nTesting auto-detection...")
    result = analyze_link(youtube_url)  # No platform specified
    print(f"Detected platform: {result['platform']}")
    print(f"Success: {result['success']}")
