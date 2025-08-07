#!/usr/bin/env python
"""Monitor test progress"""

import time
import os
import subprocess

def check_test_progress():
    """Check test progress from log file"""
    log_file = "test_results_subagent_full.log"
    
    if not os.path.exists(log_file):
        print("⏳ Waiting for test to start...")
        return False
        
    # Count test progress
    with open(log_file, 'r') as f:
        content = f.read()
        
    # Count completed tests
    passed_count = content.count("✅ PASSED")
    failed_count = content.count("❌ FAILED")
    total_completed = passed_count + failed_count
    
    # Check if test completed
    if "FINAL TEST SUMMARY" in content:
        print("\n🎉 TEST COMPLETED!")
        return True
        
    # Check categories
    categories_completed = []
    for category in ["产品推荐", "预约挂号", "临床分析", "用药指导", "症状分析", "紧急情况", "一般咨询"]:
        if f"📊 {category} Summary:" in content:
            categories_completed.append(category)
    
    print(f"\n📊 Progress Update:")
    print(f"   Tests Completed: {total_completed}/70")
    print(f"   Tests Passed: {passed_count}")
    print(f"   Tests Failed: {failed_count}")
    print(f"   Categories Done: {len(categories_completed)}/7")
    if categories_completed:
        print(f"   Completed: {', '.join(categories_completed)}")
    
    # Check if process is still running
    result = subprocess.run(["pgrep", "-f", "test_humansa_v2_70_cases_subagent.py"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print("\n⚠️  Test process no longer running!")
        return True
        
    return False

if __name__ == "__main__":
    print("🔍 Monitoring HUMANSA V2 Sub-Agent Test Progress...")
    print("   This will check every 30 seconds")
    
    while True:
        if check_test_progress():
            break
        time.sleep(30)
    
    print("\n📄 Check test_results_subagent_full.log for full results")