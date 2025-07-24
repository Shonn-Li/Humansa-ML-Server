#!/bin/bash
# Ensure Humansa test environment uses port 5456 (not 5454)

echo "🔧 Updating Humansa test environment to use port 5456..."

# Update all Humansa test files to use port 5456
files=(
    "populate_humansa_test_data.py"
    "test_db_connection.py"
    "reset_test_data.sh"
    "setup_test_env.sh"
    "README.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        # Only update in Humansa context (DB_PORT references)
        sed -i '' 's/DB_PORT.*5454/DB_PORT'\''', '\''5456/g' "$file" 2>/dev/null || true
        sed -i '' 's/localhost:5454/localhost:5456/g' "$file" 2>/dev/null || true
        sed -i '' 's/port 5454/port 5456/g' "$file" 2>/dev/null || true
        sed -i '' 's/DB_PORT=5454/DB_PORT=5456/g' "$file" 2>/dev/null || true
        echo "  ✅ Updated $file"
    fi
done

echo ""
echo "📋 Summary:"
echo "  - Main test environment: port 5454 (unchanged)"
echo "  - Humansa test environment: port 5456 (updated)"
echo ""
echo "To use Humansa test environment:"
echo "  export DB_PORT=5456"
echo "  docker-compose -f docker-compose.test.yml up -d"