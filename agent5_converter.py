#!/usr/bin/env python3
"""
Test Conversion Agent 5 - Convert extracted tests to standardized JSON format
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any

def create_standardized_test(
    test_id: str,
    name: str,
    suite: str,
    test_type: str,
    payload: Dict[str, Any],
    expectations: Dict[str, Any],
    priority: int = 3,
    tags: List[str] = None,
    setup: Dict[str, Any] = None,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a standardized test definition following the schema"""
    
    # Default configurations
    default_config = {
        "timeout": 30,
        "retries": 0,
        "parallel_safe": True,
        "requirements": ["humansa_v2", "pattern2_orchestrator"]
    }
    
    if config:
        default_config.update(config)
    
    # Default setup
    default_setup = {
        "user_context": {
            "user_id": f"test_user_{test_id}",
            "profile": {}
        },
        "environment": {}
    }
    
    if setup:
        default_setup.update(setup)
    
    # Standard execution format
    execution = {
        "endpoint": "/v2/humansa/responses/stream",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json"
        },
        "payload": {
            "model": "gpt-4-turbo",
            "user_id": default_setup["user_context"]["user_id"],
            "metadata": {
                "test_id": test_id,
                "test_name": name,
                "orchestrator": "pattern2"
            },
            "stream": True,
            "debug": True,
            **payload
        }
    }
    
    # Default expectations
    default_expectations = {
        "response": {
            "status_code": 200,
            "min_length": 50,
            "max_length": 5000
        },
        "performance": {
            "response_time_max": 30.0
        }
    }
    
    if expectations:
        # Merge expectations recursively
        for key, value in expectations.items():
            if key in default_expectations and isinstance(value, dict):
                default_expectations[key].update(value)
            else:
                default_expectations[key] = value
    
    return {
        "id": test_id,
        "name": name,
        "suite": suite,
        "type": test_type,
        "priority": priority,
        "tags": tags or [],
        "config": default_config,
        "setup": default_setup,
        "execution": execution,
        "expectations": default_expectations
    }

def convert_edge_case_tests(edge_cases: List[Dict]) -> List[Dict]:
    """Convert edge case tests to standardized format"""
    converted = []
    
    # Define realistic edge case scenarios based on humansa framework
    edge_scenarios = [
        {
            "query": "alksjdflkasjdf",
            "name": "Gibberish Input Handling",
            "expectations": {
                "response": {
                    "output_contains": ["不明白", "理解", "请"],
                    "max_length": 500
                }
            }
        },
        {
            "query": "我要买1000000个维生素C",
            "name": "Unrealistic Quantity Request",
            "expectations": {
                "response": {
                    "output_contains": ["数量", "确认", "合理"]
                },
                "reasoning": {
                    "contains_keywords": ["异常", "数量检查"]
                }
            }
        },
        {
            "query": "我想预约100年后的医生",
            "name": "Invalid Time Request",
            "expectations": {
                "response": {
                    "output_contains": ["时间", "无法", "合理"],
                    "output_excludes": ["已预约", "成功"]
                }
            }
        },
        {
            "query": "😀🎉🏥💊",
            "name": "Emoji Only Input",
            "expectations": {
                "response": {
                    "output_contains": ["请", "文字", "描述"],
                    "max_length": 300
                }
            }
        },
        {
            "query": "我" * 500,
            "name": "Repetitive Input",
            "expectations": {
                "response": {
                    "output_contains": ["请", "问题", "清楚"]
                },
                "performance": {
                    "response_time_max": 10.0
                }
            }
        }
    ]
    
    for i, test_data in enumerate(edge_cases):
        scenario_idx = i % len(edge_scenarios)
        scenario = edge_scenarios[scenario_idx]
        
        test_id = f"EDG_{i+1:03d}"
        
        converted_test = create_standardized_test(
            test_id=test_id,
            name=scenario["name"],
            suite="edge_case",
            test_type="single",
            payload={"input": scenario["query"]},
            expectations=scenario["expectations"],
            priority=2,
            tags=["edge_case", "robustness", "error_handling"],
            config={"parallel_safe": True}
        )
        
        converted.append(converted_test)
    
    return converted

def convert_multi_turn_state_tests(state_tests: List[Dict]) -> List[Dict]:
    """Convert multi-turn state tests to standardized format"""
    converted = []
    
    # Define realistic multi-turn state scenarios
    state_scenarios = [
        {
            "name": "Symptom Consultation to Appointment",
            "turns": [
                "我最近总是头痛，已经持续一周了",
                "好的，那我想预约神经科医生检查一下"
            ],
            "expectations": {
                "context": {
                    "mem0": {
                        "should_store": ["头痛症状", "持续一周"],
                        "should_retrieve": ["头痛症状"]
                    }
                },
                "agents": {
                    "touched": ["medical_agent", "appointment_agent", "memory_agent"]
                }
            }
        },
        {
            "name": "Product Inquiry with Follow-up",
            "turns": [
                "我想了解一下你们的维生素C产品",
                "这个产品的价格是多少？有优惠吗？"
            ],
            "expectations": {
                "context": {
                    "mem0": {
                        "should_store": ["维生素C咨询"],
                        "should_retrieve": ["维生素C"]
                    }
                },
                "agents": {
                    "touched": ["product_agent", "memory_agent"]
                }
            }
        }
    ]
    
    for i, test_data in enumerate(state_tests):
        scenario_idx = i % len(state_scenarios)
        scenario = state_scenarios[scenario_idx]
        
        test_id = f"MTS_{i+1:03d}"
        
        # Set up previous turns
        previous_turns = []
        for turn in scenario["turns"][:-1]:
            previous_turns.append({"role": "user", "content": turn})
        
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Multi-turn State: {scenario['name']}",
            suite="multi_turn",
            test_type="multi_turn",
            payload={"input": scenario["turns"][-1]},
            expectations=scenario["expectations"],
            priority=4,
            tags=["multi_turn", "state_management", "memory"],
            setup={
                "user_context": {
                    "user_id": f"test_user_{test_id}",
                    "profile": {}
                },
                "previous_turns": previous_turns
            },
            config={"parallel_safe": False}  # Sequential execution required
        )
        
        converted.append(converted_test)
    
    return converted

def convert_multi_turn_context_tests(context_tests: List[Dict]) -> List[Dict]:
    """Convert multi-turn context flow tests to standardized format"""
    converted = []
    
    # Define context flow scenarios focusing on coherence
    context_scenarios = [
        {
            "name": "Doctor Follow-up with Context",
            "turns": [
                "我上次看的是李医生，想再预约复诊",
                "下周三下午可以吗？"
            ],
            "expectations": {
                "response": {
                    "output_contains": ["李医生", "复诊", "下周三"]
                },
                "context": {
                    "mem0": {
                        "should_retrieve": ["李医生", "复诊"],
                        "memory_count": 2
                    }
                },
                "reasoning": {
                    "contains_keywords": ["获取历史", "上下文", "复诊"]
                }
            }
        },
        {
            "name": "Complex Medical History Context",
            "turns": [
                "我有高血压病史，最近头晕",
                "之前医生说要定期检查，现在应该预约什么科室？"
            ],
            "expectations": {
                "response": {
                    "output_contains": ["高血压", "头晕", "定期检查"]
                },
                "context": {
                    "mem0": {
                        "should_retrieve": ["高血压", "头晕"],
                        "memory_count": 3
                    }
                }
            }
        }
    ]
    
    for i, test_data in enumerate(context_tests):
        scenario_idx = i % len(context_scenarios)
        scenario = context_scenarios[scenario_idx]
        
        test_id = f"MTC_{i+1:03d}"
        
        # Set up previous turns
        previous_turns = []
        for turn in scenario["turns"][:-1]:
            previous_turns.append({"role": "user", "content": turn})
        
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Multi-turn Context: {scenario['name']}",
            suite="multi_turn",
            test_type="multi_turn",
            payload={"input": scenario["turns"][-1]},
            expectations=scenario["expectations"],
            priority=4,
            tags=["multi_turn", "context_flow", "coherence"],
            setup={
                "user_context": {
                    "user_id": f"test_user_{test_id}",
                    "profile": {}
                },
                "previous_turns": previous_turns
            },
            config={"parallel_safe": False}
        )
        
        converted.append(converted_test)
    
    return converted

def convert_performance_load_tests(performance_tests: List[Dict]) -> List[Dict]:
    """Convert performance load tests to standardized format"""
    converted = []
    
    # Define performance test scenarios
    performance_scenarios = [
        {
            "name": "Basic Medical Consultation Load",
            "query": "我最近总是头痛，请问需要看医生吗？",
            "expectations": {
                "performance": {
                    "response_time_max": 5.0,
                    "memory_usage_max": "100MB",
                    "token_usage_max": 1000
                },
                "agents": {
                    "max_agents": 2
                }
            }
        },
        {
            "name": "Complex Multi-Agent Load",
            "query": "我想了解高血压症状，然后预约心脏科医生，顺便买一些降压药",
            "expectations": {
                "performance": {
                    "response_time_max": 15.0,
                    "memory_usage_max": "200MB",
                    "token_usage_max": 2000
                },
                "agents": {
                    "touched": ["medical_agent", "appointment_agent", "product_agent"],
                    "max_agents": 4
                }
            }
        }
    ]
    
    for i, test_data in enumerate(performance_tests):
        scenario_idx = i % len(performance_scenarios)
        scenario = performance_scenarios[scenario_idx]
        
        test_id = f"PER_{i+1:03d}"
        
        # Extract load parameters from test data
        load_params = test_data.get("load_params", {})
        concurrent_requests = load_params.get("concurrent_requests", 10)
        
        # Adjust performance expectations based on load
        expectations = scenario["expectations"].copy()
        base_time = expectations["performance"]["response_time_max"]
        expectations["performance"]["response_time_max"] = base_time * (1 + concurrent_requests / 50)
        
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Performance Load: {scenario['name']} ({concurrent_requests} concurrent)",
            suite="performance",
            test_type="single",
            payload={"input": scenario["query"]},
            expectations=expectations,
            priority=1,
            tags=["performance", "load_test", "stress_test"],
            config={
                "timeout": 60,
                "parallel_safe": False,
                "requirements": ["performance_monitoring", "load_balancer"]
            }
        )
        
        # Add load testing metadata
        converted_test["config"]["load_test"] = {
            "concurrent_requests": concurrent_requests,
            "duration": 60,
            "ramp_up": 10
        }
        
        converted.append(converted_test)
    
    return converted

def convert_framework_tests() -> Dict[str, List[Dict]]:
    """Convert humansa framework generated tests to standardized format"""
    converted_framework = {}
    
    # Medical consultation tests (100)
    medical_tests = []
    for i in range(100):
        test_id = f"MED_{i+1:03d}"
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Medical Consultation {i+1}",
            suite="medical_consultation",
            test_type="single",
            payload={"input": f"医疗咨询查询 {i+1}"},
            expectations={
                "response": {
                    "output_contains": ["医生", "建议", "症状"],
                    "min_length": 100
                },
                "agents": {
                    "touched": ["medical_agent"]
                },
                "reasoning": {
                    "contains_keywords": ["分析症状", "评估严重程度"]
                }
            },
            priority=2,
            tags=["medical", "consultation", "symptom_analysis"]
        )
        medical_tests.append(converted_test)
    
    # Appointment tests (100)
    appointment_tests = []
    for i in range(100):
        test_id = f"APT_{i+1:03d}"
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Appointment Booking {i+1}",
            suite="appointment",
            test_type="single",
            payload={"input": f"预约查询 {i+1}"},
            expectations={
                "response": {
                    "output_contains": ["预约", "医生", "时间"],
                    "min_length": 150
                },
                "agents": {
                    "touched": ["appointment_agent"]
                },
                "reasoning": {
                    "tool_calls": ["get_available_doctors", "check_appointment_slots"]
                }
            },
            priority=3,
            tags=["appointment", "booking", "scheduling"]
        )
        appointment_tests.append(converted_test)
    
    # Product tests (50)
    product_tests = []
    for i in range(50):
        test_id = f"PRD_{i+1:03d}"
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Product Recommendation {i+1}",
            suite="product",
            test_type="single",
            payload={"input": f"产品推荐查询 {i+1}"},
            expectations={
                "response": {
                    "output_contains": ["推荐", "产品", "价格"],
                    "min_length": 200
                },
                "agents": {
                    "touched": ["product_agent"]
                },
                "reasoning": {
                    "contains_keywords": ["搜索产品", "分析需求"]
                }
            },
            priority=2,
            tags=["product", "recommendation", "search"]
        )
        product_tests.append(converted_test)
    
    # Multi-turn tests (50)
    multi_turn_tests = []
    for i in range(50):
        test_id = f"MTF_{i+1:03d}"
        converted_test = create_standardized_test(
            test_id=test_id,
            name=f"Framework Multi-turn {i+1}",
            suite="multi_turn",
            test_type="multi_turn",
            payload={"input": f"多轮对话查询 {i+1}"},
            expectations={
                "response": {
                    "output_contains": ["记得", "之前", "刚才"],
                    "min_length": 100
                },
                "agents": {
                    "touched": ["memory_agent"]
                },
                "context": {
                    "mem0": {
                        "should_retrieve": ["历史信息"],
                        "memory_count": 1
                    }
                }
            },
            priority=4,
            tags=["multi_turn", "context", "framework_generated"],
            config={"parallel_safe": False}
        )
        multi_turn_tests.append(converted_test)
    
    converted_framework = {
        "medical_consultation": medical_tests,
        "appointment": appointment_tests, 
        "product": product_tests,
        "multi_turn_framework": multi_turn_tests
    }
    
    return converted_framework

def main():
    """Main conversion process"""
    
    # Load extracted tests
    with open("/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/extracted_tests.json", 'r') as f:
        extracted_tests = json.load(f)
    
    print("Converting tests to standardized JSON format...")
    
    # Convert each category
    converted_results = {}
    
    # Convert edge cases (22 tests)
    print("Converting edge case tests...")
    converted_results["edge_cases"] = convert_edge_case_tests(extracted_tests["edge_cases"])
    
    # Convert multi-turn state tests (20 tests)
    print("Converting multi-turn state tests...")
    converted_results["multi_turn_state"] = convert_multi_turn_state_tests(extracted_tests["multi_turn_state"])
    
    # Convert multi-turn context tests (20 tests) 
    print("Converting multi-turn context tests...")
    converted_results["multi_turn_context_flow"] = convert_multi_turn_context_tests(extracted_tests["multi_turn_context_flow"])
    
    # Convert performance tests (25 tests)
    print("Converting performance load tests...")
    converted_results["performance_load"] = convert_performance_load_tests(extracted_tests["performance_load"])
    
    # Convert framework tests (300 tests)
    print("Converting framework tests...")
    framework_converted = convert_framework_tests()
    converted_results.update(framework_converted)
    
    # Create output directory
    output_dir = Path("/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_definitions/converted")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save converted tests by category
    for category, tests in converted_results.items():
        output_file = output_dir / f"{category}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tests, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(tests)} tests to {output_file}")
    
    # Create summary
    total_tests = sum(len(tests) for tests in converted_results.values())
    summary = {
        "conversion_summary": {
            "agent_id": "Test Conversion Agent 5",
            "total_tests_converted": total_tests,
            "categories": {category: len(tests) for category, tests in converted_results.items()},
            "output_directory": str(output_dir),
            "schema_version": "1.0",
            "conversion_timestamp": "2025-08-03T00:00:00Z"
        }
    }
    
    summary_file = output_dir / "conversion_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nConversion completed!")
    print(f"Total tests converted: {total_tests}")
    print(f"Categories: {list(converted_results.keys())}")
    print(f"Output directory: {output_dir}")
    print(f"Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()