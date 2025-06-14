#!/bin/bash

# Start the ML server on port 5001
echo "Starting ML server on port 5001..."
cd /app
python -m uvicorn src.main:app --host 0.0.0.0 --port 5001
