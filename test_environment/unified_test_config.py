"""
Unified Test Environment Configuration
=====================================

This file contains the SINGLE SOURCE OF TRUTH for all test environment settings.
All test scripts should import and use these configurations.

IMPORTANT: The actual running test environment is:
- Container: youwoai_test_db (NOT humansa_test_postgres)
- Port: 5454
- Password: 12931 (NOT 031203 from docker-compose.yml)
- Databases: test4 (primary), youwoai_test (secondary)
"""

import os
from typing import Dict, Any

# Test Environment Database Configuration
TEST_DB_CONFIG = {
    "host": "localhost",
    "port": 5454,  # Actual running container port
    "user": "postgres",
    "password": "12931",  # Actual working password
    "database": "test4",  # Primary test database
    "container_name": "youwoai_test_db",
    "alternate_db": "youwoai_test"  # Also available in container
}

# Test ML Server Configuration
TEST_ML_SERVER = {
    "host": "localhost",
    "port": 6001,  # Test ML server port
    "base_url": "http://localhost:6001"
}

# Test Environment Variables
TEST_ENV_VARS = {
    "ENVIRONMENT": "test",
    "DB_HOST": TEST_DB_CONFIG["host"],
    "DB_PORT": str(TEST_DB_CONFIG["port"]),
    "DB_USER": TEST_DB_CONFIG["user"],
    "DB_PASSWORD": TEST_DB_CONFIG["password"],
    "DB_NAME": TEST_DB_CONFIG["database"],
    "ML_SERVER_PORT": str(TEST_ML_SERVER["port"]),
    "HUMANSA_ENHANCED_LOGGING": "true",
    # Memory configuration
    "MEM0_SCHEMA": "mem0_humansa_test",
    # Test data flags
    "USE_TEST_DATA": "true",
    "TEST_MODE": "true"
}

# Test User IDs (all as strings for consistency)
TEST_USER_IDS = {
    "memory_test": "test_user_10001",
    "doctor_test": "test_user_doctor_001",
    "general_test": "test_user_general_001",
    "humansa_v2": "test_user_humansa_v2_001"
}

# Azure OpenAI Configuration (for Mem0)
AZURE_CONFIG = {
    "endpoint": "https://youwoai-dev-resource.openai.azure.com/",
    "deployment_gpt4": "gpt-4.1",
    "deployment_embedding": "text-embedding-ada-002",
    "api_version": "2023-05-15"
}

def get_test_db_url() -> str:
    """Get the test database URL"""
    cfg = TEST_DB_CONFIG
    return f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"

def setup_test_environment() -> None:
    """Set up all test environment variables"""
    for key, value in TEST_ENV_VARS.items():
        os.environ[key] = value
    
    # Map Azure credentials if available
    if os.getenv("AZURE_INFERENCE_CREDENTIAL"):
        os.environ["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_INFERENCE_CREDENTIAL")
        os.environ["AZURE_OPENAI_ENDPOINT"] = AZURE_CONFIG["endpoint"]

def get_test_psql_command(query: str = "") -> str:
    """Get a psql command configured for the test database"""
    cfg = TEST_DB_CONFIG
    base_cmd = f"PGPASSWORD={cfg['password']} psql -h {cfg['host']} -p {cfg['port']} -U {cfg['user']} -d {cfg['database']}"
    if query:
        return f"{base_cmd} -c \"{query}\""
    return base_cmd

def verify_test_database() -> bool:
    """Verify the test database is accessible"""
    import subprocess
    try:
        cmd = get_test_psql_command("SELECT 1;")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

# Docker Compose Override Configuration
# This shows what SHOULD be in docker-compose.yml to match reality
DOCKER_COMPOSE_CORRECT = """
services:
  youwoai-test-db:
    image: pgvector/pgvector:pg15
    container_name: youwoai_test_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: 12931  # Correct password
      POSTGRES_DB: test4        # Primary test database
    ports:
      - "5454:5432"
    volumes:
      - youwoai_test_postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./sql/test_data.sql:/docker-entrypoint-initdb.d/02-test-data.sql
"""

# Export all configurations
__all__ = [
    'TEST_DB_CONFIG',
    'TEST_ML_SERVER', 
    'TEST_ENV_VARS',
    'TEST_USER_IDS',
    'AZURE_CONFIG',
    'get_test_db_url',
    'setup_test_environment',
    'get_test_psql_command',
    'verify_test_database'
]