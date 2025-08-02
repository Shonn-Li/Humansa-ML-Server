#!/usr/bin/env python3
"""
Simple test of form filling logic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.humansa.v2.forms.form_filling_agent import FormFillingAgent
import json

def test_form_filling():
    agent = FormFillingAgent()
    
    test_queries = [
        "我想看医生",
        "我头疼想看医生", 
        "我想找李明医生看病",
        "我想预约李明医生看内科，明天上午9点，最近头疼发烧",
        "给孩子挂个儿科号，最近咳嗽",
        "紧急！胸闷心慌，需要马上看医生"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        result = agent.fill_form_from_query(query)
        
        print(f"Confidence: {result['extraction_confidence']:.0%}")
        print(f"Extracted:")
        for key, value in result.items():
            if key not in ['extraction_confidence', 'missing_fields', 'suggestions']:
                print(f"  {key}: {value}")
        
        if result['missing_fields']:
            print(f"Missing: {', '.join(result['missing_fields'])}")
            
        if result['suggestions']:
            print("Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion['type']}: {suggestion.get('message', '')}")
                if 'doctors' in suggestion:
                    for doc in suggestion['doctors']:
                        print(f"    * {doc['name']} ({doc['title']})")

if __name__ == "__main__":
    print("Form Filling Agent Test")
    print("=" * 60)
    test_form_filling()