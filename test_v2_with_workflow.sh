#!/bin/bash
# Test V2 with workflow orchestrator enabled

echo "Testing V2 with Workflow Orchestrator..."

# Set environment variables
export HUMANSA_USE_WORKFLOW_ORCHESTRATOR=true
export HUMANSA_ENHANCED_LOGGING=true

# Run the test
source youwo-ml-venv/bin/activate
python test_v2_workflow_focus.py