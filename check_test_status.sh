#!/bin/bash
# Quick test status check

echo "================================"
echo "HUMANSA V2 Sub-Agent Test Status"
echo "Time: $(date)"
echo "================================"

if [ -f test_results_subagent_full.log ]; then
    echo ""
    echo "📊 Progress:"
    echo "   Tests Passed: $(grep -c '✅ PASSED' test_results_subagent_full.log 2>/dev/null || echo 0)"
    echo "   Tests Failed: $(grep -c '❌ FAILED' test_results_subagent_full.log 2>/dev/null || echo 0)"
    echo "   Categories Done: $(grep -c 'Summary:' test_results_subagent_full.log 2>/dev/null || echo 0)/7"
    
    echo ""
    echo "📁 Category Results:"
    grep "Summary:" test_results_subagent_full.log 2>/dev/null || echo "No summaries yet"
    
    if grep -q "FINAL TEST SUMMARY" test_results_subagent_full.log 2>/dev/null; then
        echo ""
        echo "✅ TEST COMPLETED!"
        echo ""
        grep -A 20 "FINAL TEST SUMMARY" test_results_subagent_full.log
    else
        # Check if still running
        if pgrep -f "test_humansa_v2_70_cases_subagent.py" > /dev/null; then
            echo ""
            echo "⏳ Test still running..."
        else
            echo ""
            echo "⚠️  Test process stopped but not completed"
        fi
    fi
else
    echo "❌ Log file not found"
fi