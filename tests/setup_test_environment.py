#!/usr/bin/env python3
"""
Setup script to configure ML Server for test environment
Ensures ML server uses test database on port 5454
"""

import os
import sys
import shutil
from pathlib import Path

def setup_test_environment():
    """Configure ML server to use test database"""
    
    print("Setting up ML Server for test environment...")
    
    # Get ML server directory
    ml_server_dir = Path(__file__).parent.parent
    env_file = ml_server_dir / ".env"
    env_test_file = ml_server_dir / ".env.test"
    env_backup_file = ml_server_dir / ".env.prod"
    
    # Check if .env.test was created by our test environment setup
    if not env_test_file.exists():
        print("Creating .env.test file...")
        
        # Read production .env if it exists
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()
        else:
            print("No .env file found. Creating from template...")
            env_content = ""
        
        # Create test environment configuration
        test_env_lines = []
        env_modified = False
        
        for line in env_content.split('\n'):
            if line.startswith('DB_PORT='):
                test_env_lines.append('DB_PORT=5454  # Test database port')
                env_modified = True
            elif line.startswith('DB_ACTIVE_DATABASE='):
                test_env_lines.append('DB_ACTIVE_DATABASE=youwoai_test')
                env_modified = True
            elif line.startswith('DB_PASSWORD='):
                test_env_lines.append('DB_PASSWORD=12931  # Test database password')
                env_modified = True
            else:
                test_env_lines.append(line)
        
        # If DB settings weren't found, add them
        if not env_modified:
            test_env_lines.extend([
                '',
                '# Test Database Configuration',
                'DB_HOST=localhost',
                'DB_PORT=5454',
                'DB_USERNAME=postgres',
                'DB_PASSWORD=12931',
                'DB_ACTIVE_DATABASE=youwoai_test'
            ])
        
        # Write test environment file
        with open(env_test_file, 'w') as f:
            f.write('\n'.join(test_env_lines))
        
        print(f"Created {env_test_file}")
    
    # Backup current .env if not already backed up
    if env_file.exists() and not env_backup_file.exists():
        shutil.copy(env_file, env_backup_file)
        print(f"Backed up current .env to {env_backup_file}")
    
    # Switch to test environment
    if env_test_file.exists():
        shutil.copy(env_test_file, env_file)
        print(f"Switched to test environment configuration")
        print(f"ML Server will now use:")
        print(f"  - Database: youwoai_test")
        print(f"  - Port: 5454")
        print(f"  - Password: 12931")
    
    # Verify test database is running
    print("\nVerifying test database...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5454,
            database="youwoai_test",
            user="postgres",
            password="12931"
        )
        
        # Check test data
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM note_v1 WHERE id >= 10001")
        note_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM embedding_v1 WHERE type_id >= 10001")
        embedding_count = cur.fetchone()[0]
        
        print(f"✅ Test database connected successfully")
        print(f"   - Test notes: {note_count}")
        print(f"   - Test embeddings: {embedding_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Could not connect to test database: {e}")
        print("   Make sure test database is running:")
        print("   cd test_environment && docker-compose up -d")
        return False
    
    print("\n✅ Test environment is ready!")
    print("\nTo restore production environment later:")
    print(f"  cp {env_backup_file} {env_file}")
    
    return True

def restore_production_environment():
    """Restore production environment configuration"""
    ml_server_dir = Path(__file__).parent.parent
    env_file = ml_server_dir / ".env"
    env_backup_file = ml_server_dir / ".env.prod"
    
    if env_backup_file.exists():
        shutil.copy(env_backup_file, env_file)
        print("Restored production environment configuration")
    else:
        print("No production backup found")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_production_environment()
    else:
        setup_test_environment()