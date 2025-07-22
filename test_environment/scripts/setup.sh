#!/bin/bash

# YouWoAI Test Environment Setup Script
# Sets up a complete isolated test database with all data and embeddings

set -e  # Exit on error

echo "🚀 YouWoAI Test Environment Setup"
echo "================================"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Change to test environment directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Check if embeddings have been exported
if [ ! -f "sql/04_embeddings.sql" ]; then
    echo "📤 Exporting embeddings from production database..."
    cd scripts
    
    # Try to find and use Python with psycopg2
    if command -v python3 &> /dev/null && python3 -c "import psycopg2" 2>/dev/null; then
        python3 export_embeddings.py
    elif [ -f "../../YouWoAI-ML-Server/youwo-ml-venv/bin/activate" ]; then
        source ../../YouWoAI-ML-Server/youwo-ml-venv/bin/activate
        python export_embeddings.py
        deactivate
    else
        echo "❌ Python with psycopg2 not found. Please install psycopg2-binary:"
        echo "   pip3 install psycopg2-binary"
        exit 1
    fi
    
    cd ..
fi

echo "✅ Embeddings exported"

# Stop any existing test container
echo "🛑 Stopping any existing test database..."
docker-compose down -v 2>/dev/null || true

# Start the test database
echo "🚀 Starting test database on port 5454..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
RETRIES=30
until docker-compose exec -T postgres-test pg_isready -U postgres -d youwoai_test >/dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo -n "."
    sleep 1
    RETRIES=$((RETRIES-1))
done

if [ $RETRIES -eq 0 ]; then
    echo ""
    echo "❌ Database failed to start. Check Docker logs:"
    echo "   docker-compose logs postgres-test"
    exit 1
fi

echo ""
echo "✅ Database is ready"

# Verify setup
echo "🔍 Verifying test environment..."
docker-compose exec -T postgres-test psql -U postgres -d youwoai_test -c "
SELECT 
    'Extensions' as check,
    COUNT(*) as count 
FROM pg_extension 
WHERE extname IN ('vector', 'pg_trgm')
UNION ALL
SELECT 
    'Tables' as check,
    COUNT(*) as count 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
UNION ALL
SELECT 
    'Test Users' as check,
    COUNT(*) as count 
FROM user_v1 
WHERE id >= 10001
UNION ALL
SELECT 
    'Test Notes' as check,
    COUNT(*) as count 
FROM note_v1 
WHERE id >= 10001
UNION ALL
SELECT 
    'Embeddings' as check,
    COUNT(*) as count 
FROM embedding_v1 
WHERE type_id >= 10001;
"

echo ""
echo "✅ Test environment setup complete!"
echo ""
echo "📋 Connection Details:"
echo "   Host: localhost"
echo "   Port: 5454"
echo "   Database: youwoai_test"
echo "   Username: postgres"
echo "   Password: 031203"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:        docker-compose logs -f postgres-test"
echo "   Connect to DB:    PGPASSWORD=031203 psql -h localhost -p 5454 -U postgres -d youwoai_test"
echo "   Stop database:    docker-compose down"
echo "   Clean up:         docker-compose down -v"
echo ""
echo "📝 Environment file: .env.test"
echo ""