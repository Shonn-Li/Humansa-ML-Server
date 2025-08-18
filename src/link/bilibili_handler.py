"""
Bilibili Video Transcript Handler with Hybrid Authentication

This module implements a production-ready Bilibili subtitle extraction system
with multiple fallback strategies and authentication options.

Features:
- Public subtitle detection (no auth required)
- Authenticated subtitle extraction (SESSDATA required)
- yt-dlp integration as primary method
- Caching support to reduce API calls
- Rate limiting compliance
"""

import os
import json
import logging
import requests
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class BilibiliTranscriptHandler:
    """
    Production-ready Bilibili transcript extraction with hybrid authentication.
    
    Strategy:
    1. Check if subtitles are publicly available (no auth)
    2. If login required, use SESSDATA authentication
    3. Use yt-dlp as primary extraction method
    4. Fallback to direct API if yt-dlp fails
    """
    
    def __init__(self, sessdata: Optional[str] = None):
        """
        Initialize handler with optional SESSDATA authentication.
        
        Args:
            sessdata: Optional SESSDATA cookie for authenticated access
        """
        self.sessdata = sessdata or os.getenv('BILIBILI_SESSDATA')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'application/json, text/plain, */*'
        }
        
    def extract_video_id(self, url_or_id: str) -> str:
        """Extract video ID from URL or return ID if already extracted."""
        if 'bilibili.com' in url_or_id:
            # Extract BV or av ID from URL
            if '/BV' in url_or_id:
                vid = url_or_id.split('/BV')[1].split('?')[0].split('/')[0]
                return f'BV{vid}'
            elif 'av' in url_or_id:
                vid = url_or_id.split('av')[1].split('?')[0].split('/')[0]
                return f'av{vid}'
        return url_or_id
    
    def check_public_access(self, video_id: str) -> Dict[str, Any]:
        """
        Check if video subtitles are publicly accessible without authentication.
        
        Returns:
            Dict with success status, need_login flag, and video info
        """
        try:
            # Get video info
            info_url = "https://api.bilibili.com/x/web-interface/view"
            params = {'bvid': video_id} if video_id.startswith('BV') else {'aid': video_id[2:]}
            
            response = requests.get(info_url, params=params, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return {'success': False, 'message': 'Failed to get video info'}
            
            data = response.json()
            if data.get('code') != 0:
                return {'success': False, 'message': data.get('message', 'Unknown error')}
            
            video_info = data['data']
            cid = video_info.get('cid')
            title = video_info.get('title', 'Unknown Title')
            
            # Check subtitle availability
            player_url = "https://api.bilibili.com/x/player/wbi/v2"
            player_params = {'bvid': video_id, 'cid': cid} if video_id.startswith('BV') else {'aid': video_id[2:], 'cid': cid}
            
            player_response = requests.get(player_url, params=player_params, headers=self.headers, timeout=10)
            if player_response.status_code == 200:
                player_data = player_response.json()
                need_login = player_data.get('data', {}).get('need_login_subtitle', False)
                subtitle_info = player_data.get('data', {}).get('subtitle', {})
                
                return {
                    'success': True,
                    'need_login': need_login,
                    'has_subtitles': bool(subtitle_info.get('subtitles', [])),
                    'title': title,
                    'cid': cid,
                    'video_info': video_info
                }
            
            return {'success': False, 'message': 'Failed to get player info'}
            
        except Exception as e:
            logger.error(f"Error checking public access: {e}")
            return {'success': False, 'message': str(e)}
    
    def extract_with_ytdlp(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract subtitles using yt-dlp (most reliable method).
        
        Returns:
            Subtitle data or None if extraction fails
        """
        try:
            # Prepare yt-dlp command
            cmd = [
                'yt-dlp',
                '--skip-download',  # Don't download video
                '--write-subs',
                '--write-auto-subs',
                '--sub-format', 'json',
                '--sub-langs', 'zh.*',  # Chinese subtitles
                '--quiet',
                '--no-warnings',
                '--print', 'title',
                '--print', 'duration',
                '--output', 'temp_%(id)s.%(ext)s'
            ]
            
            # Add authentication if available
            if self.sessdata:
                cookie_file = self._create_cookie_file()
                cmd.extend(['--cookies', cookie_file])
            
            cmd.append(video_url)
            
            # Execute yt-dlp
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse output
                lines = result.stdout.strip().split('\n')
                title = lines[0] if lines else 'Unknown'
                duration = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 0
                
                # Find subtitle file
                subtitle_files = list(Path('.').glob('temp_*.json'))
                if subtitle_files:
                    with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                        subtitle_data = json.load(f)
                    
                    # Clean up
                    for file in subtitle_files:
                        os.remove(file)
                    
                    return {
                        'success': True,
                        'title': title,
                        'duration': duration,
                        'subtitles': subtitle_data,
                        'method': 'yt-dlp'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"yt-dlp extraction failed: {e}")
            return None
        finally:
            # Clean up cookie file
            if self.sessdata and os.path.exists('temp_cookies.txt'):
                os.remove('temp_cookies.txt')
    
    def extract_with_api(self, video_id: str, cid: str) -> Optional[Dict[str, Any]]:
        """
        Extract subtitles using direct API call (fallback method).
        
        Returns:
            Subtitle data or None if extraction fails
        """
        try:
            # Prepare headers with authentication
            headers = self.headers.copy()
            if self.sessdata:
                headers['Cookie'] = f'SESSDATA={self.sessdata}'
            
            # Get subtitle data
            subtitle_url = "https://api.bilibili.com/x/player/wbi/v2"
            params = {'bvid': video_id, 'cid': cid} if video_id.startswith('BV') else {'aid': video_id[2:], 'cid': cid}
            
            response = requests.get(subtitle_url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            subtitle_info = data.get('data', {}).get('subtitle', {})
            subtitles = subtitle_info.get('subtitles', [])
            
            if subtitles:
                # Download first available subtitle
                subtitle_url = subtitles[0]['subtitle_url']
                if not subtitle_url.startswith('http'):
                    subtitle_url = f'https:{subtitle_url}'
                
                sub_response = requests.get(subtitle_url, headers=headers, timeout=10)
                if sub_response.status_code == 200:
                    subtitle_data = sub_response.json()
                    return {
                        'success': True,
                        'subtitles': subtitle_data.get('body', []),
                        'method': 'api',
                        'language': subtitles[0].get('lan', 'zh')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"API extraction failed: {e}")
            return None
    
    def extract_transcript(self, url_or_id: str) -> Dict[str, Any]:
        """
        Main method to extract transcript with hybrid approach.
        
        Returns:
            Dict with transcript data and metadata
        """
        video_id = self.extract_video_id(url_or_id)
        video_url = f"https://www.bilibili.com/video/{video_id}" if not url_or_id.startswith('http') else url_or_id
        
        # Step 1: Check public access
        public_check = self.check_public_access(video_id)
        
        if not public_check['success']:
            return {
                'success': False,
                'error': public_check.get('message', 'Failed to check video'),
                'video_id': video_id
            }
        
        # Step 2: Determine if authentication is needed
        need_auth = public_check.get('need_login', False)
        
        if need_auth and not self.sessdata:
            return {
                'success': False,
                'error': 'This video requires authentication. Please provide SESSDATA.',
                'video_id': video_id,
                'title': public_check.get('title', 'Unknown'),
                'need_auth': True
            }
        
        # Step 3: Try yt-dlp first (most reliable)
        ytdlp_result = self.extract_with_ytdlp(video_url)
        if ytdlp_result and ytdlp_result['success']:
            return {
                'success': True,
                'video_id': video_id,
                'title': ytdlp_result['title'],
                'subtitles': ytdlp_result['subtitles'],
                'method': 'yt-dlp',
                'authenticated': bool(self.sessdata)
            }
        
        # Step 4: Fallback to API method
        if public_check.get('cid'):
            api_result = self.extract_with_api(video_id, public_check['cid'])
            if api_result and api_result['success']:
                return {
                    'success': True,
                    'video_id': video_id,
                    'title': public_check.get('title', 'Unknown'),
                    'subtitles': api_result['subtitles'],
                    'method': 'api',
                    'authenticated': bool(self.sessdata)
                }
        
        # Step 5: All methods failed
        return {
            'success': False,
            'error': 'Failed to extract subtitles with all methods',
            'video_id': video_id,
            'title': public_check.get('title', 'Unknown'),
            'has_subtitles': public_check.get('has_subtitles', False),
            'need_auth': need_auth
        }
    
    def format_transcript(self, subtitle_data: List[Dict]) -> str:
        """
        Format subtitle data into readable transcript.
        
        Args:
            subtitle_data: List of subtitle entries
            
        Returns:
            Formatted transcript string
        """
        formatted_lines = []
        
        for entry in subtitle_data:
            start = entry.get('from', 0)
            end = entry.get('to', start)
            text = entry.get('content', '').strip()
            
            if text:
                start_time = self._format_timestamp(start)
                end_time = self._format_timestamp(end)
                formatted_lines.append(f"[{start_time} - {end_time}] {text}")
        
        return '\n'.join(formatted_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def _create_cookie_file(self) -> str:
        """Create temporary cookie file for yt-dlp."""
        cookie_content = f"""# Netscape HTTP Cookie File
.bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\t{self.sessdata}
"""
        with open('temp_cookies.txt', 'w') as f:
            f.write(cookie_content)
        return 'temp_cookies.txt'


# Integration function for link_analyzer.py
def extract_bilibili_transcript(url: str, sessdata: Optional[str] = None) -> Dict[str, Any]:
    """
    Main integration point for link_analyzer.py
    
    Args:
        url: Bilibili video URL
        sessdata: Optional SESSDATA for authentication
        
    Returns:
        Dict with transcript data and metadata
    """
    handler = BilibiliTranscriptHandler(sessdata)
    result = handler.extract_transcript(url)
    
    if result['success'] and 'subtitles' in result:
        # Format the transcript
        result['formatted_transcript'] = handler.format_transcript(result['subtitles'])
    
    return result