#!/bin/bash
# Update all test scripts to use port 5002 instead of 5001

echo "Updating test scripts to use port 5002..."

# Find all Python test files and update the port
find tests -name "*.py" -type f -exec sed -i '' 's/localhost:5001/localhost:5002/g' {} \;
find tests -name "*.py" -type f -exec sed -i '' 's/127.0.0.1:5001/127.0.0.1:5002/g' {} \;
find tests -name "*.py" -type f -exec sed -i '' 's/http:\/\/localhost:5001/http:\/\/localhost:5002/g' {} \;

# Also update the main test file
sed -i '' 's/localhost:5001/localhost:5002/g' test_clean_output.py 2>/dev/null

echo "✅ Updated all test files to use port 5002"
echo ""
echo "Files updated:"
grep -l "5002" tests/*.py 2>/dev/null | head -10
echo "..."

echo ""
echo "To start the test server:"
echo "  ./start_test_server_5002.sh"