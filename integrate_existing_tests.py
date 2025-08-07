#!/usr/bin/env python3
"""
Integration Script for Existing HUMANSA Tests
============================================

This script integrates all existing HUMANSA test cases into the new comprehensive
test framework, allowing them to be run with parallel execution, standardized
reporting, and unified monitoring.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import importlib.util
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from humansa_test_framework import (
    TestCase,
    TestCategory,
    TestExpectation,
    TestCaseManager,
    TestExecutor,
    ParallelTestRunner,
    TestReporter
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExistingTestImporter:
    """Import test cases from existing test files"""
    
    def __init__(self, manager: TestCaseManager):
        self.manager = manager
        self.imported_count = 0
    
    def import_from_70_cases(self):
        """Import the 70 test cases from test_HUMANSA_v2_70_cases_multiturn.py"""
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(
                "test_70_cases",
                "/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_HUMANSA_v2_70_cases_multiturn.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Import single-turn test cases
            if hasattr(module, 'SINGLE_TURN_TEST_CASES'):
                for case in module.SINGLE_TURN_TEST_CASES:
                    test_case = self._convert_legacy_test_case(case, is_multi_turn=False)
                    self.manager.add_test_case(test_case)
                    self.imported_count += 1
            
            # Import multi-turn test cases
            if hasattr(module, 'MULTI_TURN_TEST_CASES'):
                for case in module.MULTI_TURN_TEST_CASES:
                    test_case = self._convert_legacy_test_case(case, is_multi_turn=True)
                    self.manager.add_test_case(test_case)
                    self.imported_count += 1
            
            logger.info(f"Imported {self.imported_count} test cases from 70 cases file")
            
        except Exception as e:
            logger.error(f"Failed to import 70 cases: {e}")
    
    def import_from_comprehensive_enhanced(self):
        """Import test cases from test_HUMANSA_v2_comprehensive_enhanced.py"""
        try:
            spec = importlib.util.spec_from_file_location(
                "test_comprehensive",
                "/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_HUMANSA_v2_comprehensive_enhanced.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Import different test case categories
            test_categories = [
                ('IDENTITY_TEST_CASES', TestCategory.IDENTITY),
                ('DOCTOR_SEARCH_TEST_CASES', TestCategory.MEDICAL_CONSULTATION),
                ('APPOINTMENT_TEST_CASES', TestCategory.APPOINTMENT),
                ('PRODUCT_TEST_CASES', TestCategory.PRODUCT_RECOMMENDATION),
                ('MEMORY_TEST_CASES', TestCategory.MULTI_TURN),
                ('EMERGENCY_TEST_CASES', TestCategory.EMERGENCY)
            ]
            
            for attr_name, category in test_categories:
                if hasattr(module, attr_name):
                    cases = getattr(module, attr_name)
                    for case in cases:
                        test_case = self._convert_legacy_test_case(case, category=category)
                        self.manager.add_test_case(test_case)
                        self.imported_count += 1
            
            logger.info(f"Imported additional test cases from comprehensive enhanced file")
            
        except Exception as e:
            logger.error(f"Failed to import comprehensive enhanced: {e}")
    
    def _convert_legacy_test_case(self, 
                                 legacy_case: Dict[str, Any], 
                                 is_multi_turn: bool = False,
                                 category: Optional[TestCategory] = None) -> TestCase:
        """Convert legacy test case format to new TestCase format"""
        
        # Determine category
        if category is None:
            category_str = legacy_case.get('category', 'General').lower()
            category_map = {
                'identity': TestCategory.IDENTITY,
                'doctor search': TestCategory.MEDICAL_CONSULTATION,
                'appointment': TestCategory.APPOINTMENT,
                'product': TestCategory.PRODUCT_RECOMMENDATION,
                'medical consultation': TestCategory.MEDICAL_CONSULTATION,
                'clinic': TestCategory.APPOINTMENT,
                'memory': TestCategory.MULTI_TURN,
                'emergency': TestCategory.EMERGENCY,
                'edge case': TestCategory.EDGE_CASE,
                'stress': TestCategory.STRESS_TEST
            }
            category = category_map.get(category_str, TestCategory.INTEGRATION)
        
        # Extract expected keywords
        keywords = legacy_case.get('expected_keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]
        
        # Build expectations
        expectations = TestExpectation(
            keywords=keywords,
            agents_touched=legacy_case.get('expected_agents', []),
            emergency_flags=legacy_case.get('emergency_flags', []),
            min_response_length=legacy_case.get('min_response_length', 50),
            response_time_max=legacy_case.get('max_response_time', 30.0)
        )
        
        # Handle multi-turn cases
        previous_turns = []
        if is_multi_turn and 'turns' in legacy_case:
            # For multi-turn, the main query is the last turn
            turns = legacy_case['turns']
            if len(turns) > 1:
                previous_turns = [{"query": turn} for turn in turns[:-1]]
                query = turns[-1]
            else:
                query = turns[0] if turns else legacy_case.get('query', '')
        else:
            query = legacy_case.get('query', '')
        
        # Create test case
        test_case = TestCase(
            id=f"legacy_{legacy_case.get('id', 'unknown')}",
            name=legacy_case.get('name', f"Legacy Test {legacy_case.get('id', '')}"),
            category=category,
            query=query,
            expectations=expectations,
            user_context=legacy_case.get('user_context', {}),
            previous_turns=previous_turns,
            metadata={
                'source': 'legacy_import',
                'original_id': legacy_case.get('id')
            },
            priority=3,
            tags=['legacy', category.value]
        )
        
        return test_case


class ExistingTestRunner:
    """Run existing test scripts and integrate results"""
    
    def __init__(self, output_dir: str = "integrated_test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_shell_script(self, script_path: str) -> Dict[str, Any]:
        """Run a shell script and capture results"""
        script_name = Path(script_path).name
        logger.info(f"Running shell script: {script_name}")
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'ENVIRONMENT': 'test',
                'ML_SERVER_PORT': '6001',
                'HUMANSA_ENHANCED_LOGGING': 'true'
            })
            
            # Run script
            process = await asyncio.create_subprocess_exec(
                'bash', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse results
            results = {
                'script': script_name,
                'exit_code': process.returncode,
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8', errors='ignore'),
                'stderr': stderr.decode('utf-8', errors='ignore')
            }
            
            # Try to find and parse JSON results
            for line in stdout.decode('utf-8', errors='ignore').split('\n'):
                if 'results_' in line and '.json' in line:
                    # Extract results file path
                    parts = line.split()
                    for part in parts:
                        if 'results_' in part and '.json' in part:
                            results_file = part.strip()
                            if Path(results_file).exists():
                                with open(results_file, 'r') as f:
                                    results['test_results'] = json.load(f)
                            break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to run {script_name}: {e}")
            return {
                'script': script_name,
                'success': False,
                'error': str(e)
            }
    
    async def run_python_test(self, test_file: str) -> Dict[str, Any]:
        """Run a Python test file and capture results"""
        test_name = Path(test_file).name
        logger.info(f"Running Python test: {test_name}")
        
        try:
            # Run Python test
            process = await asyncio.create_subprocess_exec(
                'python3', test_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            results = {
                'test_file': test_name,
                'exit_code': process.returncode,
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8', errors='ignore'),
                'stderr': stderr.decode('utf-8', errors='ignore')
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to run {test_name}: {e}")
            return {
                'test_file': test_name,
                'success': False,
                'error': str(e)
            }


async def run_all_existing_tests():
    """Run all existing tests through the framework"""
    
    # Initialize components
    manager = TestCaseManager(base_dir="integrated_test_cases")
    importer = ExistingTestImporter(manager)
    runner = ExistingTestRunner()
    
    # Import existing test cases
    logger.info("Importing existing test cases...")
    importer.import_from_70_cases()
    importer.import_from_comprehensive_enhanced()
    
    # Get all imported test cases
    test_cases = manager.get_test_cases()
    logger.info(f"Total imported test cases: {len(test_cases)}")
    
    # Run tests through new framework
    logger.info("Running tests through new framework...")
    parallel_runner = ParallelTestRunner(max_workers=4)
    results = await parallel_runner.run_tests(test_cases, batch_size=20)
    
    # Generate comprehensive report
    reporter = TestReporter(output_dir="integrated_test_reports")
    report_path = reporter.generate_report(test_cases, results, "integrated_test_run")
    
    # Also run original shell scripts for comparison
    logger.info("\nRunning original shell scripts for comparison...")
    shell_scripts = [
        "run_HUMANSA_v2_test_70_cases.sh",
        "run_HUMANSA_comprehensive_test.sh",
        "run_HUMANSA_v2_test_40_cases_enhanced.sh"
    ]
    
    shell_results = []
    for script in shell_scripts:
        script_path = f"/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/{script}"
        if Path(script_path).exists():
            result = await runner.run_shell_script(script_path)
            shell_results.append(result)
    
    # Generate comparison report
    comparison = {
        'framework_results': {
            'total_tests': len(test_cases),
            'executed': len(results),
            'passed': sum(1 for r in results if r.success),
            'report': report_path
        },
        'shell_script_results': shell_results,
        'imported_test_count': importer.imported_count
    }
    
    comparison_path = runner.output_dir / "test_comparison_report.json"
    with open(comparison_path, 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    
    logger.info(f"\nComparison report saved to: {comparison_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("INTEGRATION SUMMARY")
    print("="*60)
    print(f"Imported test cases: {importer.imported_count}")
    print(f"Framework test execution: {len(results)} tests")
    print(f"Success rate: {(sum(1 for r in results if r.success)/len(results)*100):.1f}%")
    print(f"Reports generated in: integrated_test_reports/")
    print(f"Comparison report: {comparison_path}")


async def demonstrate_framework_capabilities():
    """Demonstrate how the framework handles existing tests"""
    
    print("\n" + "="*60)
    print("HUMANSA TEST FRAMEWORK - EXISTING TEST INTEGRATION")
    print("="*60)
    
    print("\nCapabilities:")
    print("1. ✅ Import all 70+ test cases from existing files")
    print("2. ✅ Run tests in parallel with configurable batch size")
    print("3. ✅ Generate standardized reports")
    print("4. ✅ Real-time monitoring support")
    print("5. ✅ Compare with original test results")
    
    print("\nExisting Test Files Found:")
    print("- test_HUMANSA_v2_70_cases_multiturn.py (70 cases)")
    print("- test_HUMANSA_v2_comprehensive_enhanced.py (40+ cases)")
    print("- test_pattern2_70_cases.py (reuses 70 cases)")
    print("- 7 shell scripts for running tests")
    
    print("\nHow it works:")
    print("1. The framework imports test cases from existing Python files")
    print("2. Converts them to standardized TestCase format")
    print("3. Runs them through parallel execution engine")
    print("4. Validates results against expectations")
    print("5. Generates comprehensive reports")
    
    print("\nTo run all existing tests:")
    print("  python integrate_existing_tests.py")
    
    print("\nTo monitor in real-time:")
    print("  python humansa_test_monitor.py demo")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demonstrate_framework_capabilities())
    else:
        # Ensure test environment is set up
        os.environ['ENVIRONMENT'] = 'test'
        os.environ['ML_SERVER_PORT'] = '6001'
        
        # Run all tests
        asyncio.run(run_all_existing_tests())