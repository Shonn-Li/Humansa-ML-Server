"""
Link Processing Module for YouWoAI ML Server

This module provides independent link analysis and content extraction capabilities:
- YouTube video content extraction
- Bilibili video content extraction  
- General web page content extraction
- URL validation and processing

This module is completely independent from chat functionality.
"""

from .link_analyzer import analyze_link

__all__ = [
    'analyze_link'
]
