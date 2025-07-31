#!/usr/bin/env python3
"""
Test tool selection logic
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from humansa.tools.consolidated_tools import ConsolidatedHumansaTools, DynamicToolLoader

# Test queries
test_queries = [
    ("我想预约明天的医生", "Should select appointment_manager"),
    ("我头疼怎么办", "Should select medical_advisor"),
    ("我想买保健品", "Should select product_recommender"),
    ("诊所的营业时间是什么", "Should select information_lookup"),
    ("我胸痛很厉害，呼吸困难", "Should select emergency_handler"),
    ("你是谁？", "Should select base tools only"),
]

def test_tool_selection():
    print("\n" + "="*60)
    print("  Tool Selection Logic Test")
    print("="*60 + "\n")
    
    # Initialize tool manager
    tool_manager = ConsolidatedHumansaTools()
    dynamic_loader = DynamicToolLoader(tool_manager)
    
    # Get all available tools
    all_tools = tool_manager.get_llamaindex_tools()
    print(f"Total available tools: {len(all_tools)}")
    print(f"Tool names: {[t.metadata.name for t in all_tools]}")
    print("\n" + "-"*60 + "\n")
    
    # Test each query
    for query, expected in test_queries:
        print(f"Query: {query}")
        print(f"Expected: {expected}")
        
        # Select tools
        selected_tools = dynamic_loader.select_tools_for_query(query)
        tool_names = [t.metadata.name for t in selected_tools]
        
        print(f"Selected {len(selected_tools)} tools: {tool_names}")
        
        # Check if expected tool is selected
        if "appointment_manager" in expected and "appointment_manager" in tool_names:
            print("✅ Correct - appointment_manager selected")
        elif "medical_advisor" in expected and "medical_advisor" in tool_names:
            print("✅ Correct - medical_advisor selected")
        elif "product_recommender" in expected and "product_recommender" in tool_names:
            print("✅ Correct - product_recommender selected")
        elif "information_lookup" in expected and "information_lookup" in tool_names:
            print("✅ Correct - information_lookup selected")
        elif "emergency_handler" in expected and "emergency_handler" in tool_names:
            print("✅ Correct - emergency_handler selected")
        elif "base tools only" in expected and len(tool_names) == 2:
            print("✅ Correct - only base tools selected")
        else:
            print("❌ Incorrect tool selection")
        
        print("\n" + "-"*60 + "\n")
    
    print("Test complete!\n")

if __name__ == "__main__":
    test_tool_selection()