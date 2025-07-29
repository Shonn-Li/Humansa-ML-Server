#!/usr/bin/env python3
"""Test Chinese date parser functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.humansa.utils.date_parser import ChineseDateParser
from datetime import datetime

def test_date_parser():
    """Test various Chinese date expressions."""
    test_cases = [
        "明天",
        "后天", 
        "下周",
        "本周",
        "下个月",
        "本月",
        "下周一",
        "本周五",
        "7天内",
        "3天后",
        "查看下周的可预约时间",
        "我想预约明天上午的骨科",
        "帮我找下个月的医生"
    ]
    
    print("Testing Chinese Date Parser")
    print("=" * 60)
    print(f"Today's date: {datetime.now().date()}")
    print("=" * 60)
    
    for test_case in test_cases:
        result = ChineseDateParser.parse_chinese_date(test_case)
        if result:
            print(f"\nInput: '{test_case}'")
            print(f"  Type: {result['parsed_type']}")
            print(f"  Start: {result['start_date']}")
            print(f"  End: {result['end_date']}")
            if result.get('days_ahead') is not None:
                print(f"  Days ahead: {result['days_ahead']}")
        else:
            print(f"\nInput: '{test_case}' - No date pattern found")
    
    # Test the extract function
    print("\n" + "=" * 60)
    print("Testing extract_date_range function:")
    print("=" * 60)
    
    for test_case in ["查看下周的可预约时间", "明天上午", "本月底"]:
        start, end, days = ChineseDateParser.extract_date_range(test_case)
        print(f"\nInput: '{test_case}'")
        print(f"  Returns: start={start}, end={end}, days={days}")

if __name__ == "__main__":
    test_date_parser()