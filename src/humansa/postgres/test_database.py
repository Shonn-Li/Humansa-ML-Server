"""
Test database connection for Humansa that uses environment-based configuration.
This module provides a database connection that properly handles test environment.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_test_db_config() -> Dict[str, Any]:
    """Get database configuration based on environment."""
    is_test = os.getenv("ENVIRONMENT") == "test"
    
    if is_test:
        # For test environment, use specific configuration
        return {
            "host": "127.0.0.1",  # Use IPv4 explicitly
            "port": 5454,
            "user": "postgres",
            "password": "031203",
            "dbname": "youwoai_test"
        }
    else:
        # Production configuration
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "youwo"),
            "password": os.getenv("DB_PASSWORD", "youwo123"),
            "dbname": os.getenv("DB_NAME", "youwoai")
        }

def test_connection():
    """Test the database connection."""
    config = get_test_db_config()
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) as count FROM humansa_doctor")
        result = cursor.fetchone()
        logger.info(f"✅ Test connection successful. Doctor count: {result['count']}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Test connection failed: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_connection()