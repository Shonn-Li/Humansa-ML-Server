#!/usr/bin/env python3
"""
Fix all references from clinic_id to clinic_code in the database.py file
"""

import re
import sys

def fix_clinic_references(file_path):
    """Replace all clinic_id references with clinic_code"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace patterns
    replacements = [
        # Column references
        (r'\bd\.clinic_id\b', 'd.clinic_code'),
        (r'\bs\.clinic_id\b', 's.clinic_code'),
        (r'\bms\.clinic_id\b', 'ms.clinic_code'),
        (r'\bc\.clinic_id\b', 'c.clinic_code'),
        
        # SELECT statements
        (r'SELECT DISTINCT c\.clinic_id,', 'SELECT DISTINCT c.clinic_code,'),
        (r'GROUP BY c\.clinic_id,', 'GROUP BY c.clinic_code,'),
        
        # JOIN conditions
        (r'ON d\.clinic_id = c\.clinic_id', 'ON d.clinic_code = c.clinic_code'),
        (r'ON s\.clinic_id = c\.clinic_id', 'ON s.clinic_code = c.clinic_code'),
        (r'ON ms\.clinic_id = c\.clinic_id', 'ON ms.clinic_code = c.clinic_code'),
        (r'ON c\.clinic_id = d\.clinic_id', 'ON c.clinic_code = d.clinic_code'),
        (r'ON s\.clinic_id = c\.id', 'ON s.clinic_code = c.clinic_code'),
        
        # Fix any remaining standalone clinic_id in SQL context
        (r'(\s+)clinic_id(\s+|,)', r'\1clinic_code\2'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed clinic references in {file_path}")

if __name__ == "__main__":
    file_path = "/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/src/humansa/postgres/database.py"
    fix_clinic_references(file_path)