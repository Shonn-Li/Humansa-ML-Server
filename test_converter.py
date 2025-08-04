#!/usr/bin/env python3
"""
Test Converter - Converts existing Python tests to standardized JSON format
==========================================================================

This script helps migrate existing test cases to the new JSON-based format
for the Test Management Dashboard.
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import ast
import argparse


class TestConverter:
    """Convert Python test cases to standardized JSON format"""
    
    def __init__(self):
        self.test_counter = {
            "appointment": 1,
            "medical_consultation": 1,
            "product": 1,
            "identity": 1,
            "emergency": 1,
            "multi_turn": 1,
            "edge_case": 1,
            "performance": 1
        }
        
        self.suite_prefixes = {
            "appointment": "APT",
            "medical_consultation": "MED",
            "product": "PRD",
            "identity": "IDT",
            "emergency": "EMG",
            "multi_turn": "MTN",
            "edge_case": "EDG",
            "performance": "PRF"
        }
    
    def generate_test_id(self, suite: str) -> str:
        """Generate unique test ID"""
        prefix = self.suite_prefixes.get(suite, "TST")
        count = self.test_counter.get(suite, 1)
        test_id = f"{prefix}_{count:03d}"
        self.test_counter[suite] = count + 1
        return test_id
    
    def detect_suite(self, test_name: str, file_path: str) -> str:
        """Detect test suite from name and file path"""
        name_lower = test_name.lower()
        path_lower = file_path.lower()
        
        if "appointment" in name_lower or "appointment" in path_lower:
            return "appointment"
        elif "medical" in name_lower or "doctor" in name_lower:
            return "medical_consultation"
        elif "product" in name_lower:
            return "product"
        elif "identity" in name_lower or "你是谁" in name_lower:
            return "identity"
        elif "emergency" in name_lower or "urgent" in name_lower:
            return "emergency"
        elif "multi" in name_lower or "turn" in name_lower:
            return "multi_turn"
        elif "edge" in name_lower:
            return "edge_case"
        elif "performance" in name_lower:
            return "performance"
        else:
            return "edge_case"
    
    def extract_expectations(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Extract expectations from legacy test case"""
        expectations = {
            "response": {},
            "reasoning": {},
            "agents": {},
            "context": {},
            "server_logs": {},
            "performance": {}
        }
        
        # Response expectations
        if "expected_keywords" in test_case:
            keywords = test_case["expected_keywords"]
            if isinstance(keywords, str):
                keywords = [keywords]
            expectations["response"]["output_contains"] = keywords
        
        if "min_response_length" in test_case:
            expectations["response"]["min_length"] = test_case["min_response_length"]
        
        if "max_response_length" in test_case:
            expectations["response"]["max_length"] = test_case["max_response_length"]
        
        # Agent expectations
        if "expected_agents" in test_case:
            expectations["agents"]["touched"] = test_case["expected_agents"]
        
        # Performance expectations
        if "max_response_time" in test_case:
            expectations["performance"]["response_time_max"] = test_case["max_response_time"]
        
        return expectations
    
    def convert_single_test(self, test_case: Dict[str, Any], file_path: str = "") -> Dict[str, Any]:
        """Convert a single test case to JSON format"""
        suite = self.detect_suite(test_case.get("name", ""), file_path)
        test_id = self.generate_test_id(suite)
        
        # Determine test type
        test_type = "multi_turn" if "turns" in test_case else "single"
        
        # Build the standardized test
        standardized_test = {
            "id": test_id,
            "name": test_case.get("name", "Unnamed test"),
            "suite": suite,
            "type": test_type,
            "priority": test_case.get("priority", 3),
            "tags": test_case.get("tags", []),
            "config": {
                "timeout": 30,
                "retries": 0,
                "parallel_safe": True
            },
            "setup": {
                "user_context": {
                    "user_id": f"test_user_{test_id.lower()}"
                }
            },
            "execution": {
                "endpoint": "/v2/humansa/responses/create",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json"
                },
                "payload": {
                    "model": "gpt-4-turbo",
                    "user_id": "${user_context.user_id}",
                    "metadata": {
                        "test_id": "${id}",
                        "test_name": "${name}"
                    }
                }
            },
            "expectations": self.extract_expectations(test_case)
        }
        
        # Handle single vs multi-turn
        if test_type == "single":
            standardized_test["execution"]["payload"]["input"] = test_case.get("query", "")
        else:
            # Extract turns for multi-turn tests
            turns = test_case.get("turns", [])
            if len(turns) > 1:
                # Last turn is the main query
                standardized_test["execution"]["payload"]["input"] = turns[-1]
                # Previous turns go in setup
                standardized_test["setup"]["previous_turns"] = []
                for i, turn in enumerate(turns[:-1]):
                    standardized_test["setup"]["previous_turns"].append({
                        "role": "user" if i % 2 == 0 else "assistant",
                        "content": turn
                    })
        
        return standardized_test
    
    def convert_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Convert all tests in a Python file to JSON format"""
        converted_tests = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to find test case definitions
        # Pattern 1: Direct list assignments
        list_pattern = r'(\w+_TEST_CASES)\s*=\s*\[(.*?)\]'
        matches = re.findall(list_pattern, content, re.DOTALL)
        
        for var_name, list_content in matches:
            try:
                # Parse the list content
                test_cases = ast.literal_eval(f"[{list_content}]")
                for test_case in test_cases:
                    if isinstance(test_case, dict):
                        converted = self.convert_single_test(test_case, file_path)
                        converted_tests.append(converted)
            except:
                print(f"Failed to parse {var_name} in {file_path}")
        
        # Pattern 2: Individual test definitions
        dict_pattern = r'test_\w+\s*=\s*{(.*?)}'
        dict_matches = re.findall(dict_pattern, content, re.DOTALL)
        
        for dict_content in dict_matches:
            try:
                test_case = ast.literal_eval(f"{{{dict_content}}}")
                converted = self.convert_single_test(test_case, file_path)
                converted_tests.append(converted)
            except:
                pass
        
        return converted_tests
    
    def save_test(self, test: Dict[str, Any], output_dir: str = "test_definitions"):
        """Save converted test to JSON file"""
        suite_dir = Path(output_dir) / test["suite"]
        suite_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename from test ID and sanitized name
        safe_name = re.sub(r'[^\w\s-]', '', test["name"])
        safe_name = re.sub(r'[-\s]+', '_', safe_name)[:50]
        filename = f"{test['id']}_{safe_name}.json"
        
        file_path = suite_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def convert_directory(self, input_dir: str, output_dir: str = "test_definitions"):
        """Convert all test files in a directory"""
        converted_count = 0
        
        for file_path in Path(input_dir).rglob("test_*.py"):
            print(f"Converting {file_path}...")
            try:
                tests = self.convert_file(str(file_path))
                for test in tests:
                    saved_path = self.save_test(test, output_dir)
                    print(f"  ✅ Saved: {saved_path}")
                    converted_count += 1
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"\nConverted {converted_count} tests total")
        return converted_count


def create_sample_legacy_test():
    """Create a sample legacy test file for demonstration"""
    sample_content = '''
"""Sample legacy test file"""

APPOINTMENT_TEST_CASES = [
    {
        "name": "Book appointment with Dr. Li",
        "query": "我想预约李明医生明天上午9点看头痛",
        "expected_keywords": ["李明医生", "明天", "上午9点"],
        "expected_agents": ["AppointmentAgent"],
        "min_response_length": 50,
        "max_response_time": 5.0
    },
    {
        "name": "Multi-turn appointment booking",
        "turns": [
            "我想预约看病",
            "李医生",
            "明天上午"
        ],
        "expected_keywords": ["预约", "确认"],
        "expected_agents": ["AppointmentAgent", "FormAgent"]
    }
]

MEDICAL_TEST_CASES = [
    {
        "name": "Ask about headache treatment",
        "query": "头痛怎么办？",
        "expected_keywords": ["头痛", "建议", "治疗"],
        "expected_agents": ["MedicalAgent"],
        "priority": 4
    }
]
'''
    
    with open("sample_legacy_tests.py", "w") as f:
        f.write(sample_content)
    
    print("Created sample_legacy_tests.py")


def main():
    parser = argparse.ArgumentParser(description="Convert legacy tests to JSON format")
    parser.add_argument("--input", "-i", help="Input file or directory")
    parser.add_argument("--output", "-o", default="test_definitions", help="Output directory")
    parser.add_argument("--sample", action="store_true", help="Create sample legacy test")
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_legacy_test()
        return
    
    converter = TestConverter()
    
    if args.input:
        if os.path.isfile(args.input):
            tests = converter.convert_file(args.input)
            for test in tests:
                saved_path = converter.save_test(test, args.output)
                print(f"Saved: {saved_path}")
        elif os.path.isdir(args.input):
            converter.convert_directory(args.input, args.output)
        else:
            print(f"Error: {args.input} not found")
    else:
        print("Usage: python test_converter.py --input <file_or_dir> [--output <dir>]")
        print("       python test_converter.py --sample  # Create sample legacy test")


if __name__ == "__main__":
    main()