#!/usr/bin/env python3
import time
import psutil
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import json
from datetime import datetime
import statistics


class BandwidthMonitor:
    def __init__(self):
        self.start_bytes = None
        self.end_bytes = None

    def start(self):
        """Record network bytes at start"""
        net_io = psutil.net_io_counters()
        self.start_bytes = net_io.bytes_sent + net_io.bytes_recv

    def stop(self):
        """Record network bytes at end and calculate usage"""
        net_io = psutil.net_io_counters()
        self.end_bytes = net_io.bytes_sent + net_io.bytes_recv
        bytes_used = self.end_bytes - self.start_bytes
        return bytes_used


def test_youtube_transcript_bandwidth(video_id, language='en'):
    """Test bandwidth usage for a single YouTube transcript fetch"""
    monitor = BandwidthMonitor()

    print(f"\n{'='*60}")
    print(f"Testing video: {video_id}")
    print(f"Language: {language}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*60}")

    # Monitor the actual API call
    monitor.start()
    start_time = time.time()

    try:
        # Fetch the transcript using the simpler method that returns data directly
        transcript_data = YouTubeTranscriptApi.get_transcript(
            video_id, languages=[language])

        # Stop monitoring
        duration = time.time() - start_time
        bytes_used = monitor.stop()

        # Calculate statistics
        kb_used = bytes_used / 1024
        mb_used = kb_used / 1024

        # Transcript stats - transcript_data is already a list of dicts
        transcript_json = json.dumps(transcript_data)
        transcript_length = len(transcript_json)
        text_length = sum(len(item.get('text', ''))
                          for item in transcript_data)
        total_duration = sum(item.get('duration', 0)
                             for item in transcript_data)

        print(f"\n✅ Success!")
        print(f"\nBandwidth Usage:")
        print(f"  - Bytes: {bytes_used:,}")
        print(f"  - KB: {kb_used:.2f}")
        print(f"  - MB: {mb_used:.4f}")

        print(f"\nTranscript Stats:")
        print(f"  - Segments: {len(transcript_data)}")
        print(
            f"  - Raw JSON size: {transcript_length:,} bytes ({transcript_length/1024:.2f} KB)")
        print(f"  - Text length: {text_length:,} characters")
        print(
            f"  - Video duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
        print(f"  - Fetch duration: {duration:.2f} seconds")

        # Cost calculation for Webshare.io
        cost_per_gb = 10  # $10 per GB (base plan estimate)
        cost_per_request = (mb_used / 1024) * cost_per_gb
        requests_per_gb = 1024 / mb_used if mb_used > 0 else 0

        print(f"\nCost Estimates (based on $10/GB):")
        print(f"  - Cost per request: ${cost_per_request:.6f}")
        print(f"  - Requests per GB: {requests_per_gb:.0f}")
        print(f"  - Requests per $1: {requests_per_gb/10:.0f}")

        return {
            'video_id': video_id,
            'bytes_used': bytes_used,
            'kb_used': kb_used,
            'mb_used': mb_used,
            'duration': duration,
            'segments': len(transcript_data),
            'transcript_size': transcript_length,
            'text_length': text_length,
            'video_duration': total_duration,
            'success': True
        }

    except Exception as e:
        bytes_used = monitor.stop()
        duration = time.time() - start_time

        print(f"\n❌ Error: {type(e).__name__}: {e}")
        print(f"  - Bytes used (failed request): {bytes_used:,}")
        print(f"  - Duration: {duration:.2f} seconds")

        return {
            'video_id': video_id,
            'bytes_used': bytes_used,
            'error': str(e),
            'duration': duration,
            'success': False
        }


def test_podcast():
    """Test the specific 2-hour podcast"""
    print("\n" + "="*80)
    print("TESTING 2-HOUR PODCAST")
    print("="*80)

    # Extract video ID from URL
    video_url = "https://www.youtube.com/watch?v=9V6tWC4CdFQ&t=151s"
    video_id = "9V6tWC4CdFQ"  # Extracted from the URL

    print(f"\nTesting podcast: {video_url}")
    print("Expected duration: ~2 hours")

    result = test_youtube_transcript_bandwidth(video_id)

    if result['success']:
        print("\n" + "="*80)
        print("BANDWIDTH ANALYSIS FOR 2-HOUR CONTENT")
        print("="*80)

        # Extrapolate for different content lengths
        mb_per_minute = result['mb_used'] / (
            result['video_duration'] / 60) if result.get('video_duration', 0) > 0 else 0

        print(f"\nBandwidth per content duration:")
        print(f"  - Per minute: {mb_per_minute:.4f} MB")
        print(f"  - 30-min podcast: {mb_per_minute * 30:.2f} MB")
        print(f"  - 1-hour podcast: {mb_per_minute * 60:.2f} MB")
        print(f"  - 2-hour podcast: {mb_per_minute * 120:.2f} MB")

        print(f"\nWith 15% proxy overhead:")
        print(
            f"  - 2-hour podcast with proxy: {result['mb_used'] * 1.15:.2f} MB")
        print(
            f"  - Cost with proxy: ${(result['mb_used'] * 1.15 / 1024) * 10:.4f}")


def main():
    print("YouTube Transcript API Bandwidth Usage Test")
    print("==========================================")
    print("Testing with 2-hour podcast as requested")

    # Test the 2-hour podcast
    test_podcast()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nBased on this test, you can calculate:")
    print("- Actual bandwidth usage for long-form content")
    print("- Cost per hour of content")
    print("- Monthly costs based on your expected usage")


if __name__ == "__main__":
    main()
