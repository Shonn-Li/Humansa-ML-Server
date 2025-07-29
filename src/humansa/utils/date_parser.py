"""
Chinese Natural Language Date Parser for HUMANSA

Handles common Chinese date expressions and converts them to date ranges.
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)


class ChineseDateParser:
    """Parse Chinese natural language date expressions."""
    
    # Common Chinese date patterns
    DATE_PATTERNS = {
        # Relative days
        '今天': 0,
        '明天': 1,
        '后天': 2,
        '大后天': 3,
        
        # This/next week
        '本周': 'this_week',
        '这周': 'this_week',
        '下周': 'next_week',
        '下个周': 'next_week',
        
        # This/next month
        '本月': 'this_month',
        '这个月': 'this_month',
        '下月': 'next_month',
        '下个月': 'next_month',
    }
    
    # Weekday mappings
    WEEKDAYS = {
        '一': 0, '周一': 0, '星期一': 0,
        '二': 1, '周二': 1, '星期二': 1,
        '三': 2, '周三': 2, '星期三': 2,
        '四': 3, '周四': 3, '星期四': 3,
        '五': 4, '周五': 4, '星期五': 4,
        '六': 5, '周六': 5, '星期六': 5,
        '日': 6, '周日': 6, '星期日': 6, '天': 6, '周天': 6
    }
    
    @classmethod
    def parse_chinese_date(cls, text: str) -> Optional[Dict[str, any]]:
        """
        Parse Chinese date expression and return date information.
        
        Args:
            text: Chinese text containing date expression
            
        Returns:
            Dict with:
                - start_date: Start date string (YYYY-MM-DD)
                - end_date: End date string (YYYY-MM-DD)
                - days_ahead: Number of days ahead (for simple cases)
                - original_text: Original input text
                - parsed_type: Type of date parsed
        """
        text = text.strip()
        today = datetime.now().date()
        
        # Check for exact matches first
        for pattern, value in cls.DATE_PATTERNS.items():
            if pattern in text:
                if isinstance(value, int):
                    # Simple day offset
                    target_date = today + timedelta(days=value)
                    return {
                        'start_date': target_date.strftime('%Y-%m-%d'),
                        'end_date': target_date.strftime('%Y-%m-%d'),
                        'days_ahead': value,
                        'original_text': text,
                        'parsed_type': 'relative_day'
                    }
                elif value == 'this_week':
                    # Get current week's start (Monday) and end (Sunday)
                    start = today - timedelta(days=today.weekday())
                    end = start + timedelta(days=6)
                    return {
                        'start_date': start.strftime('%Y-%m-%d'),
                        'end_date': end.strftime('%Y-%m-%d'),
                        'days_ahead': (end - today).days,
                        'original_text': text,
                        'parsed_type': 'this_week'
                    }
                elif value == 'next_week':
                    # Get next week's start and end
                    start = today + timedelta(days=(7 - today.weekday()))
                    end = start + timedelta(days=6)
                    return {
                        'start_date': start.strftime('%Y-%m-%d'),
                        'end_date': end.strftime('%Y-%m-%d'),
                        'days_ahead': (end - today).days,
                        'original_text': text,
                        'parsed_type': 'next_week'
                    }
                elif value == 'this_month':
                    # Get current month's start and end
                    start = today.replace(day=1)
                    # Get last day of month
                    if today.month == 12:
                        end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                    return {
                        'start_date': start.strftime('%Y-%m-%d'),
                        'end_date': end.strftime('%Y-%m-%d'),
                        'days_ahead': (end - today).days,
                        'original_text': text,
                        'parsed_type': 'this_month'
                    }
                elif value == 'next_month':
                    # Get next month's start and end
                    if today.month == 12:
                        start = today.replace(year=today.year + 1, month=1, day=1)
                        end = start.replace(month=2, day=1) - timedelta(days=1)
                    else:
                        start = today.replace(month=today.month + 1, day=1)
                        if start.month == 12:
                            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
                        else:
                            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
                    return {
                        'start_date': start.strftime('%Y-%m-%d'),
                        'end_date': end.strftime('%Y-%m-%d'),
                        'days_ahead': (end - today).days,
                        'original_text': text,
                        'parsed_type': 'next_month'
                    }
        
        # Check for specific weekday patterns (e.g., "下周一", "本周五")
        weekday_pattern = r'(本周|这周|下周|下个周)(一|二|三|四|五|六|日|天)'
        match = re.search(weekday_pattern, text)
        if match:
            week_type = match.group(1)
            weekday = match.group(2)
            
            if weekday in cls.WEEKDAYS:
                target_weekday = cls.WEEKDAYS[weekday]
                
                if week_type in ['本周', '这周']:
                    # This week's specific day
                    days_until = target_weekday - today.weekday()
                    if days_until < 0:  # Already passed this week
                        days_until += 7
                    target_date = today + timedelta(days=days_until)
                else:  # Next week
                    days_until = target_weekday - today.weekday() + 7
                    target_date = today + timedelta(days=days_until)
                
                return {
                    'start_date': target_date.strftime('%Y-%m-%d'),
                    'end_date': target_date.strftime('%Y-%m-%d'),
                    'days_ahead': (target_date - today).days,
                    'original_text': text,
                    'parsed_type': 'specific_weekday'
                }
        
        # Check for "X天内" pattern (within X days)
        within_pattern = r'(\d+)天内'
        match = re.search(within_pattern, text)
        if match:
            days = int(match.group(1))
            end_date = today + timedelta(days=days)
            return {
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days_ahead': days,
                'original_text': text,
                'parsed_type': 'within_days'
            }
        
        # Check for "X天后" pattern (X days later)
        after_pattern = r'(\d+)天后'
        match = re.search(after_pattern, text)
        if match:
            days = int(match.group(1))
            target_date = today + timedelta(days=days)
            return {
                'start_date': target_date.strftime('%Y-%m-%d'),
                'end_date': target_date.strftime('%Y-%m-%d'),
                'days_ahead': days,
                'original_text': text,
                'parsed_type': 'days_later'
            }
        
        # No pattern matched
        logger.debug(f"No date pattern found in: {text}")
        return None
    
    @classmethod
    def extract_date_range(cls, text: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Extract date range from Chinese text.
        
        Returns:
            Tuple of (start_date, end_date, days_ahead) or (None, None, None)
        """
        result = cls.parse_chinese_date(text)
        if result:
            return result['start_date'], result['end_date'], result.get('days_ahead')
        return None, None, None