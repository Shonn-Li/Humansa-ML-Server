#!/usr/bin/env python3
"""
Test Conversion Agent 1 - Convert Pattern 2 Test Suite to JSON Format
Converts test_pattern2_70_cases.py and related tests to standardized JSON format
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Import test cases
import sys
sys.path.append('archive/old_tests')

try:
    from test_HUMANSA_v2_70_cases_multiturn import SINGLE_TURN_TEST_CASES, MULTI_TURN_TEST_CASES
except ImportError as e:
    print(f"Error: Could not import test cases: {e}")
    # Define minimal test cases for fallback
    SINGLE_TURN_TEST_CASES = []
    MULTI_TURN_TEST_CASES = []

def get_category_code(category: str) -> str:
    """Get 3-letter category code"""
    category_map = {
        "Identity": "IDT",
        "Doctor Search": "DOC", 
        "Appointment": "APT",
        "Clinic": "CLI",
        "Service": "SRV",
        "Medical": "MED",
        "Product": "PRD",
        "Memory": "MEM",
        "Multi-turn Basic": "MTB",
        "Multi-turn Medical": "MTM",
        "Multi-turn Appointment": "MTA", 
        "Multi-turn Product": "MTP",
        "Multi-turn Emergency": "MTE",
        "Multi-turn Chronic": "MTC",
        "Multi-turn Pediatric": "MTP",
        "Multi-turn Medication": "MTD",
        "Multi-turn Follow-up": "MTF",
        "Multi-turn Health Check": "MTH",
        "Multi-turn Memory": "MTM",
        "Multi-turn Allergy": "MTA",
        "Multi-turn Location": "MTL",
        "Multi-turn Progress": "MTP",
        "Multi-turn Family": "MTF",
        "Multi-turn Chronic Care": "MCC",
        "Multi-turn Pregnancy": "MPG",
        "Multi-turn Mental Health": "MMH",
        "Multi-turn Vaccination": "MVA",
        "Multi-turn Elder Care": "MEC",
        "Multi-turn Journey": "MJN",
        "Multi-turn Decision": "MDS",
        "Multi-turn Rehab": "MRH",
        "Multi-turn Lifestyle": "MLS",
        "Multi-turn Insurance": "MIN",
        "Multi-turn Second Opinion": "MSO",
        "Multi-turn Travel": "MTR",
        "Multi-turn Pain": "MPN",
        "Multi-turn Prevention": "MPR",
        "Multi-turn Coordination": "MCO"
    }
    return category_map.get(category, "HMV")  # Default to HMV (Humansa V2)

def get_suite_name(category: str) -> str:
    """Get suite name from category"""
    if "Identity" in category:
        return "identity"
    elif "Doctor" in category or "Medical" in category:
        return "medical_consultation"
    elif "Appointment" in category:
        return "appointment"
    elif "Product" in category:
        return "product"
    elif "Emergency" in category:
        return "emergency"
    elif "Multi-turn" in category:
        return "multi_turn"
    elif "Memory" in category:
        return "multi_turn"
    else:
        return "edge_case"

def get_priority(category: str, test_name: str) -> int:
    """Get test priority based on category and name"""
    if "Emergency" in category or "Emergency" in test_name:
        return 5
    elif "Identity" in category or "Basic" in test_name:
        return 4
    elif "Appointment" in category or "Medical" in category:
        return 4
    elif "Memory" in category or "Multi-turn" in category:
        return 3
    else:
        return 3

def get_tags(category: str, test_name: str) -> List[str]:
    """Get tags based on category and test name"""
    tags = []
    
    # Category-based tags
    if "Identity" in category:
        tags.extend(["identity", "introduction"])
    elif "Doctor" in category:
        tags.extend(["doctor", "search"])
    elif "Appointment" in category:
        tags.extend(["appointment", "booking"])
    elif "Medical" in category:
        tags.extend(["medical", "consultation"])
    elif "Product" in category:
        tags.extend(["product", "recommendation"])
    elif "Memory" in category:
        tags.extend(["memory", "context"])
    elif "Emergency" in category:
        tags.extend(["emergency", "urgent"])
    
    # Multi-turn specific
    if "Multi-turn" in category:
        tags.append("multi_turn")
    
    # Name-based tags
    if "Emergency" in test_name or "急救" in test_name:
        tags.append("emergency")
    if "Child" in test_name or "孩子" in test_name:
        tags.append("pediatric")
    if "Medication" in test_name or "药" in test_name:
        tags.append("medication")
    
    return list(set(tags))  # Remove duplicates

def convert_single_turn_test(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a single-turn test case to JSON format"""
    category = test_case.get("category", "General")
    category_code = get_category_code(category)
    test_id = f"{category_code}_{test_case['id']:03d}"
    
    # Determine if it's a streaming test (even IDs use streaming)
    use_streaming = test_case['id'] % 2 == 0
    endpoint = "/v2/humansa/responses/stream" if use_streaming else "/v2/humansa/responses/create"
    
    json_test = {
        "id": test_id,
        "name": test_case['name'],
        "suite": get_suite_name(category),
        "type": "single",
        "priority": get_priority(category, test_case['name']),
        "tags": get_tags(category, test_case['name']),
        "config": {
            "timeout": 30,
            "retries": 1,
            "parallel_safe": True,
            "requirements": ["pattern2_orchestrator"]
        },
        "setup": {
            "user_context": {
                "user_id": test_case.get('user_id', f"test_user_{test_case['id']:03d}"),
                "profile": {}
            },
            "previous_turns": [],
            "environment": {
                "HUMANSA_USE_PATTERN2": "true"
            }
        },
        "execution": {
            "endpoint": endpoint,
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "gpt-4.1",
                "input": test_case['query'],
                "user_id": test_case.get('user_id', f"test_user_{test_case['id']:03d}"),
                "metadata": {
                    "test_id": test_id,
                    "test_name": test_case['name'],
                    "orchestrator": "pattern2"
                }
            }
        },
        "expectations": {
            "response": {
                "status_code": 200,
                "output_contains": test_case.get('expected_keywords', []),
                "output_excludes": [],
                "min_length": 20
            },
            "reasoning": {
                "steps_min": 1,
                "contains_keywords": [],
                "tool_calls": []
            },
            "agents": {
                "max_agents": 5
            },
            "context": {
                "mem0": {
                    "should_store": [],
                    "should_retrieve": []
                }
            },
            "server_logs": {
                "excludes": ["ERROR", "Exception"],
                "log_levels": {
                    "ERROR": "=0"
                }
            },
            "performance": {
                "response_time_max": 15.0,
                "token_usage_max": 2000
            }
        },
        "cleanup": {
            "commands": [],
            "reset_context": test_case.get('requires_context', False)
        }
    }
    
    # Special handling for memory tests
    if category == "Memory":
        if "Store" in test_case['name'] or "记录" in test_case['query']:
            json_test["expectations"]["context"]["mem0"]["should_store"] = ["personal_info"]
        elif "Recall" in test_case['name'] or "记得" in test_case['query']:
            json_test["expectations"]["context"]["mem0"]["should_retrieve"] = ["personal_info"]
            json_test["setup"]["previous_turns"] = [
                {
                    "role": "user",
                    "content": "我叫李明，45岁，有高血压"
                },
                {
                    "role": "assistant", 
                    "content": "好的，我已经记录了您的信息"
                }
            ]
    
    # Emergency tests should have urgent expectations
    if "Emergency" in category or "Emergency" in test_case['name']:
        json_test["expectations"]["response"]["output_contains"].extend(["120", "急救", "立即"])
        json_test["expectations"]["performance"]["response_time_max"] = 5.0
        json_test["priority"] = 5
    
    return json_test

def convert_multi_turn_test(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a multi-turn test case to JSON format"""
    category = test_case.get("category", "Multi-turn")
    category_code = get_category_code(category)
    test_id = f"{category_code}_{test_case['id']:03d}"
    
    # Build previous turns from the test case
    previous_turns = []
    for i, turn in enumerate(test_case['turns'][:-1]):  # All but last turn
        previous_turns.extend([
            {
                "role": "user",
                "content": turn['query']
            },
            {
                "role": "assistant",
                "content": f"Response to turn {i+1}"
            }
        ])
    
    # The last turn is the actual test query
    last_turn = test_case['turns'][-1]
    
    json_test = {
        "id": test_id,
        "name": test_case['name'],
        "suite": "multi_turn",
        "type": "multi_turn",
        "priority": get_priority(category, test_case['name']),
        "tags": get_tags(category, test_case['name']),
        "config": {
            "timeout": 60,
            "retries": 1,
            "parallel_safe": False,  # Multi-turn tests need sequential execution
            "requirements": ["pattern2_orchestrator", "mem0_integration"]
        },
        "setup": {
            "user_context": {
                "user_id": f"mt_test_{test_case['id']}",
                "profile": {}
            },
            "previous_turns": previous_turns,
            "environment": {
                "HUMANSA_USE_PATTERN2": "true"
            }
        },
        "execution": {
            "endpoint": "/v2/humansa/responses/stream",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "payload": {
                "model": "gpt-4.1",
                "input": last_turn['query'],
                "user_id": f"mt_test_{test_case['id']}",
                "metadata": {
                    "test_id": test_id,
                    "test_name": test_case['name'],
                    "orchestrator": "pattern2",
                    "conversation_turn": len(test_case['turns'])
                }
            }
        },
        "expectations": {
            "response": {
                "status_code": 200,
                "output_contains": last_turn.get('expected', []),
                "output_excludes": [],
                "min_length": 30
            },
            "reasoning": {
                "steps_min": 2,
                "contains_keywords": ["context", "previous"],
                "tool_calls": []
            },
            "agents": {
                "max_agents": 5
            },
            "context": {
                "mem0": {
                    "should_store": ["conversation_context"],
                    "should_retrieve": ["conversation_history"],
                    "memory_count": len(test_case['turns'])
                }
            },
            "server_logs": {
                "excludes": ["ERROR", "Exception"],
                "log_levels": {
                    "ERROR": "=0"
                }
            },
            "performance": {
                "response_time_max": 20.0,
                "token_usage_max": 3000
            }
        },
        "cleanup": {
            "commands": [],
            "reset_context": True
        }
    }
    
    # Emergency multi-turn tests
    if "Emergency" in category:
        json_test["expectations"]["response"]["output_contains"].extend(["120", "急救", "立即"])
        json_test["priority"] = 5
        json_test["expectations"]["performance"]["response_time_max"] = 8.0
    
    return json_test

def create_directory_structure():
    """Create the test definitions directory structure"""
    base_dir = "test_definitions"
    categories = ["humansa_v2", "appointment", "api", "tools", "startup"]
    
    for category in categories:
        os.makedirs(f"{base_dir}/{category}", exist_ok=True)
    
    print(f"Created directory structure in {base_dir}/")

def convert_all_tests():
    """Convert all test cases to JSON format"""
    print("Starting test conversion...")
    
    # Create directories
    create_directory_structure()
    
    # Convert single-turn tests (1-40)
    print(f"\nConverting {len(SINGLE_TURN_TEST_CASES)} single-turn tests...")
    for test_case in SINGLE_TURN_TEST_CASES:
        json_test = convert_single_turn_test(test_case)
        
        # Save to appropriate directory
        category = test_case.get("category", "General")
        if "Identity" in category:
            directory = "humansa_v2"
        elif "Appointment" in category:
            directory = "appointment"
        elif "Medical" in category or "Doctor" in category:
            directory = "humansa_v2"
        elif "Product" in category:
            directory = "humansa_v2"
        else:
            directory = "humansa_v2"
        
        filename = f"test_definitions/{directory}/{json_test['id']}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_test, f, indent=2, ensure_ascii=False)
        
        print(f"Created: {filename}")
    
    # Convert multi-turn tests (41-70)
    print(f"\nConverting {len(MULTI_TURN_TEST_CASES)} multi-turn tests...")
    for test_case in MULTI_TURN_TEST_CASES:
        json_test = convert_multi_turn_test(test_case)
        
        filename = f"test_definitions/humansa_v2/{json_test['id']}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_test, f, indent=2, ensure_ascii=False)
        
        print(f"Created: {filename}")
    
    print(f"\n✅ Conversion complete!")
    print(f"Total tests converted: {len(SINGLE_TURN_TEST_CASES) + len(MULTI_TURN_TEST_CASES)}")
    print(f"Files created in test_definitions/ directories")

if __name__ == "__main__":
    convert_all_tests()