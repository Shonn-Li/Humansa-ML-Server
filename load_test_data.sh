#!/bin/bash
# Load Humansa test data into database

echo "Loading Humansa test data..."

# Load environment variables
source .env

# Connect to database and load SQL
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < setup_humansa_test_data.sql

if [ $? -eq 0 ]; then
    echo "✅ Test data loaded successfully!"
else
    echo "❌ Failed to load test data"
    exit 1
fi