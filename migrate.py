#!/usr/bin/env python3
"""
Migration script to switch from old main.py to new modular structure.

This script will:
1. Backup the current main.py
2. Replace it with the new modular version
3. Provide rollback instructions
"""

import os
import shutil
from datetime import datetime

def migrate_to_modular_structure():
    """Migrate from monolithic main.py to modular structure"""
    
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    old_main = os.path.join(current_dir, "main.py")
    new_main = os.path.join(current_dir, "main_new.py")
    backup_main = os.path.join(current_dir, f"main_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
    
    print("🚀 YouWoAI ML Server - Modular Migration")
    print("=" * 50)
    
    # Check if files exist
    if not os.path.exists(old_main):
        print("❌ Error: main.py not found")
        return False
    
    if not os.path.exists(new_main):
        print("❌ Error: main_new.py not found")
        return False
    
    # Create backup
    print(f"📦 Creating backup: {backup_main}")
    shutil.copy2(old_main, backup_main)
    
    # Replace main.py
    print("🔄 Replacing main.py with modular version...")
    shutil.copy2(new_main, old_main)
    
    print("✅ Migration completed successfully!")
    print("\n📁 New structure:")
    print("├── main.py                 (Entry point)")
    print("├── routes/                 (Controllers)")
    print("│   ├── health.py           (Health endpoints)")
    print("│   ├── jobs.py             (Job management)")
    print("│   ├── embeddings.py       (Embedding operations)")
    print("│   └── search.py           (Search endpoints)")
    print("├── services/               (Business logic)")
    print("│   ├── job_service.py      (Background jobs)")
    print("│   ├── embedding_service.py (Embedding logic)")
    print("│   └── search_service.py   (Search logic)")
    print("├── models/                 (Data models)")
    print("│   ├── job.py              (Job models)")
    print("│   └── response.py         (API responses)")
    print("└── utility/                (Existing utilities)")
    
    print(f"\n🔙 To rollback: cp {backup_main} main.py")
    print("\n🎯 Benefits:")
    print("- ✅ Separation of concerns")
    print("- ✅ Better maintainability") 
    print("- ✅ Easier testing")
    print("- ✅ Modular structure like NestJS")
    print("- ✅ Background job system")
    print("- ✅ No more timeout issues")
    
    return True

def verify_structure():
    """Verify that all required files exist"""
    required_files = [
        "routes/__init__.py",
        "routes/health.py",
        "routes/jobs.py", 
        "routes/embeddings.py",
        "routes/search.py",
        "services/__init__.py",
        "services/job_service.py",
        "services/embedding_service.py",
        "services/search_service.py",
        "models/__init__.py",
        "models/job.py",
        "models/response.py"
    ]
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    missing_files = []
    
    for file_path in required_files:
        full_path = os.path.join(current_dir, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ All required files exist")
    return True

if __name__ == "__main__":
    print("1. Verifying modular structure...")
    if not verify_structure():
        print("❌ Please ensure all modular files are created first")
        exit(1)
    
    print("\n2. Starting migration...")
    if migrate_to_modular_structure():
        print("\n🎉 Migration successful! You can now start the server.")
        print("   python src/main.py")
    else:
        print("❌ Migration failed")
        exit(1)
