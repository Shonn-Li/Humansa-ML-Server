#!/bin/bash

# Test Dashboard - Single Launch Script
# Everything in one Python file, one URL

# Kill any existing process on port 6002
lsof -ti:6002 | xargs kill -9 2>/dev/null || true

# Use virtual environment if available
if [ -d "test_dashboard/backend/venv" ]; then
    source test_dashboard/backend/venv/bin/activate
fi

# Run the dashboard
ML_DIGIT=${ML_DIGIT:-5} python3 test_dashboard_final.py