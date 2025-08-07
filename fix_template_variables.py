#!/usr/bin/env python3
"""
Script to fix template variables in JSON test files.
Replaces template variables like ${id}, ${name}, ${user_context.user_id} with actual values.
"""

import json
import os
import re
from pathlib import Path

def generate_user_id(test_id):
    """Generate a unique user ID based on the test ID."""
    return f"test_user_{test_id.lower()}"

def generate_response_id(test_id):
    """Generate a response ID based on the test ID."""
    return f"resp_{test_id.lower()}"

def generate_session_id(test_id):
    """Generate a session ID based on the test ID."""
    return f"session_{test_id.lower()}"

def generate_conversation_id(test_id):
    """Generate a conversation ID based on the test ID."""
    return f"conv_{test_id.lower()}"

def replace_template_variables(content, test_data):
    """Replace template variables in JSON content with actual values."""
    test_id = test_data.get('id', 'unknown')
    test_name = test_data.get('name', 'Unknown Test')
    
    # Basic replacements
    replacements = {
        '${id}': test_id,
        '${name}': test_name,
        '${test_id}': test_id,
        '${user_context.user_id}': generate_user_id(test_id),
        '${session_id}': generate_session_id(test_id),
        '${response_id}': generate_response_id(test_id),
        '${previous_response_id}': f"prev_{generate_response_id(test_id)}",
        '${previous_response.id}': f"prev_{generate_response_id(test_id)}",
        '${conversation_id}': generate_conversation_id(test_id),
        '${result.id}': f"result_{test_id.lower()}"
    }
    
    # Apply basic replacements
    for template, replacement in replacements.items():
        content = content.replace(template, replacement)
    
    # Handle special case for previous_turns
    if '${setup.previous_turns}' in content:
        # Try to get the actual previous_turns from setup
        if 'setup' in test_data and 'previous_turns' in test_data['setup']:
            previous_turns = json.dumps(test_data['setup']['previous_turns'])
            content = content.replace('"${setup.previous_turns}"', previous_turns)
        else:
            # Default empty array
            content = content.replace('"${setup.previous_turns}"', '[]')
    
    return content

def process_json_file(file_path):
    """Process a single JSON file to replace template variables."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Check if file has template variables
        if '${' not in original_content:
            return False, "No template variables found"
        
        # Parse JSON to get test data
        try:
            test_data = json.loads(original_content)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        
        # Replace template variables
        fixed_content = replace_template_variables(original_content, test_data)
        
        # Verify the result is still valid JSON
        try:
            json.loads(fixed_content)
        except json.JSONDecodeError as e:
            return False, f"Fixed content is not valid JSON: {e}"
        
        # Write back the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        return True, "Fixed successfully"
        
    except Exception as e:
        return False, f"Error processing file: {e}"

def main():
    """Main function to process all JSON files with template variables."""
    test_definitions_dir = Path("/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_definitions")
    
    # Find all JSON files with template variables
    json_files = []
    for root, dirs, files in os.walk(test_definitions_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '${' in content:
                            json_files.append(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    print(f"Found {len(json_files)} JSON files with template variables")
    
    # Process each file
    fixed_count = 0
    for file_path in json_files:
        print(f"Processing: {file_path}")
        success, message = process_json_file(file_path)
        if success:
            fixed_count += 1
            print(f"  ✓ {message}")
        else:
            print(f"  ✗ {message}")
    
    print(f"\nSummary: Fixed {fixed_count} out of {len(json_files)} files")

if __name__ == "__main__":
    main()