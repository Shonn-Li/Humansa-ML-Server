#!/usr/bin/env python3
"""
Cleanup Script for Outdated Test Files and Orchestrators
========================================================

This script removes outdated files and reorganizes the codebase.
Run with --dry-run first to see what will be deleted.
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import json

# Files to delete (high priority)
FILES_TO_DELETE = [
    # Debug/temporary test files
    "test_orchestrator_debug.py",
    "test_minimal_format.py", 
    "test_quick_identity.py",
    "test_azure_openai_issue.py",
    "test_react_minimal.py",
    "test_form_simple.py",
    "test_pattern2_mock.py",
    "test_pattern2_single.py",
    "test_react_fix_simple.py",
    "test_form_api_direct.py",
    "test_v2_correct_endpoint.py",
    "test_tool_selection.py",
    
    # Duplicate orchestrators
    "src/humansa/v2/orchestrator_agent_fix.py",
    "src/humansa/v2/orchestrator_agent_subagent.py",
    "src/humansa/v2/workflows/orchestrator_backup.py",
    "src/humansa/v2/workflows/orchestrator_workaround.py",
    "src/humansa/v2/workflows/debug_orchestrator.py",
    "src/humansa/v2/workflows/orchestrator_simple_debug.py",
    "src/humansa/v2/workflows/orchestrator_fixed.py",
    
    # Old workflow tests
    "test_workflow_poc.py",
    "test_workflow_direct.py",
    "test_v2_workflow_focus.py",
    "test_v2_workflow_product.py",
    "test_workflow_streaming.py",
    
    # Old response tests
    "test_response_agent_fix.py",
    "test_response_forking_scenarios.py",
    
    # Duplicate appointment tests
    "test_appointment_quick.py",
    "test_appointment_agent_direct.py",
    "test_appointment_db_direct.py",
    "test_form_filling_process.py",
    "test_form_flow_simple.py",
    "test_form_db_integration.py",
    
    # Old product tests
    "test_product_agent_simple.py",
    "test_product_agent_csv.py",
    "test_product_simple_direct.py",
    "test_product_direct_workflow.py",
    "test_csv_products_simple.py",
    
    # Subagent tests (deprecated)
    "test_subagent_architecture.py",
    "test_subagent_simple.py",
    "test_humansa_v2_70_cases_subagent.py"
]

# Files to archive (move to archive/)
FILES_TO_ARCHIVE = [
    "test_HUMANSA_v2_70_cases_multiturn.py",
    "test_HUMANSA_v2_comprehensive_enhanced.py",
    "test_long_conversation_suite.py",
    "test_humansa_v2_with_reasoning.py",
    "test_reasoning_stream_comparison.py"
]

# Files to consolidate (keep for now but mark for future consolidation)
FILES_TO_CONSOLIDATE = {
    "appointment_tests": [
        "test_appointment_approval_flow.py",
        "test_appointment_realistic.py",
        "test_form_appointment_flow.py"
    ],
    "product_tests": [
        "test_product_agent_staged.py",
        "test_enhanced_product_agent.py"
    ],
    "pattern2_tests": [
        "test_pattern2_orchestrator.py",
        "test_pattern2_form_complete.py", 
        "test_pattern2_memory.py",
        "test_pattern2_quick_appointment.py"
    ]
}


def create_archive_dir():
    """Create archive directory if it doesn't exist"""
    archive_dir = Path("archive/old_tests")
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def cleanup_files(dry_run=False):
    """Remove outdated files"""
    results = {
        "deleted": [],
        "archived": [],
        "not_found": [],
        "errors": []
    }
    
    print("🧹 Starting cleanup process...")
    
    # Delete files
    print("\n📁 Deleting outdated files...")
    for file_path in FILES_TO_DELETE:
        full_path = Path(file_path)
        if full_path.exists():
            if not dry_run:
                try:
                    full_path.unlink()
                    results["deleted"].append(str(full_path))
                    print(f"  ✅ Deleted: {file_path}")
                except Exception as e:
                    results["errors"].append(f"{file_path}: {str(e)}")
                    print(f"  ❌ Error deleting {file_path}: {e}")
            else:
                results["deleted"].append(str(full_path))
                print(f"  🔍 Would delete: {file_path}")
        else:
            results["not_found"].append(str(full_path))
            print(f"  ⚠️  Not found: {file_path}")
    
    # Archive files
    print("\n📦 Archiving old test files...")
    archive_dir = create_archive_dir()
    
    for file_path in FILES_TO_ARCHIVE:
        full_path = Path(file_path)
        if full_path.exists():
            archive_path = archive_dir / full_path.name
            if not dry_run:
                try:
                    shutil.move(str(full_path), str(archive_path))
                    results["archived"].append(str(full_path))
                    print(f"  ✅ Archived: {file_path} → archive/old_tests/")
                except Exception as e:
                    results["errors"].append(f"{file_path}: {str(e)}")
                    print(f"  ❌ Error archiving {file_path}: {e}")
            else:
                results["archived"].append(str(full_path))
                print(f"  🔍 Would archive: {file_path} → archive/old_tests/")
        else:
            results["not_found"].append(str(full_path))
            print(f"  ⚠️  Not found: {file_path}")
    
    # Report on files to consolidate
    print("\n📋 Files marked for future consolidation:")
    for category, files in FILES_TO_CONSOLIDATE.items():
        print(f"\n  {category}:")
        for file_path in files:
            if Path(file_path).exists():
                print(f"    - {file_path}")
    
    # Save cleanup report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "results": results,
        "consolidation_plan": FILES_TO_CONSOLIDATE
    }
    
    report_path = f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print("\n" + "="*60)
    print("🎯 CLEANUP SUMMARY")
    print("="*60)
    print(f"Files deleted: {len(results['deleted'])}")
    print(f"Files archived: {len(results['archived'])}")
    print(f"Files not found: {len(results['not_found'])}")
    print(f"Errors: {len(results['errors'])}")
    print(f"\nReport saved to: {report_path}")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN - no files were actually modified")
        print("Run without --dry-run to perform actual cleanup")
    
    return results


def create_consolidation_plan():
    """Create detailed plan for test consolidation"""
    plan = {
        "phase1_immediate": {
            "delete_count": len(FILES_TO_DELETE),
            "archive_count": len(FILES_TO_ARCHIVE),
            "files": FILES_TO_DELETE + FILES_TO_ARCHIVE
        },
        "phase2_consolidation": FILES_TO_CONSOLIDATE,
        "phase3_standardization": {
            "target_structure": {
                "tests/modular/": "All standardized test cases",
                "tests/framework/": "Test framework code",
                "tests/data/": "Test data and fixtures",
                "archive/": "Old tests for reference"
            },
            "naming_convention": "CATEGORY_###_description.yaml",
            "total_target": 1000
        }
    }
    
    with open("test_consolidation_plan.json", 'w') as f:
        json.dump(plan, f, indent=2)
    
    print(f"\n📋 Consolidation plan saved to: test_consolidation_plan.json")


def main():
    parser = argparse.ArgumentParser(description="Cleanup outdated test files")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--create-plan", action="store_true",
                       help="Create consolidation plan without cleanup")
    
    args = parser.parse_args()
    
    if args.create_plan:
        create_consolidation_plan()
    else:
        cleanup_files(dry_run=args.dry_run)


if __name__ == "__main__":
    main()