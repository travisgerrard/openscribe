#!/usr/bin/env python3
"""
Refactor Test Runner

This script runs the essential tests that would have caught the issues
we encountered during the recent file reorganization. Run this before
and after any major refactoring to catch integration problems early.

Test categories:
1. Startup validation (environment, dependencies)
2. Frontend-backend communication
3. Audio pipeline and VAD thresholds
4. File organization integrity

Usage:
    python scripts/run_refactor_tests.py [--quick] [--category=CATEGORY]
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path
import time

def main():
    parser = argparse.ArgumentParser(description='Run refactoring validation tests')
    parser.add_argument('--quick', action='store_true', 
                       help='Run only the fastest essential tests')
    parser.add_argument('--category', choices=['startup', 'communication', 'audio', 'integration'],
                       help='Run only tests from specific category')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🧪 Running Refactor Validation Tests")
    print("=" * 50)
    
    # Define test categories with their priorities
    test_categories = {
        'startup': {
            'name': 'Startup & Environment Validation',
            'tests': ['tests/integration/test_startup_validation.py'],
            'essential': True,
            'description': 'Validates conda environment, dependencies, file structure'
        },
        'communication': {
            'name': 'Frontend-Backend Communication',
            'tests': ['tests/integration/test_frontend_backend_communication.py'],
            'essential': True,
            'description': 'Validates IPC messaging, GUI initialization, tray state'
        },
        'audio': {
            'name': 'Audio Pipeline & VAD Thresholds',
            'tests': ['tests/unit/test_audio_vad_thresholds.py'],
            'essential': True,
            'description': 'Validates VAD thresholds, microphone access patterns'
        },
        'integration': {
            'name': 'File Organization Integration',
            'tests': ['tests/integration/test_frontend_backend_integration.py'],
            'essential': False,
            'description': 'Validates file paths, imports, organization integrity'
        }
    }
    
    # Determine which tests to run
    if args.category:
        categories_to_run = [args.category]
    elif args.quick:
        categories_to_run = [cat for cat, info in test_categories.items() if info['essential']]
    else:
        categories_to_run = list(test_categories.keys())
    
    total_tests = len(categories_to_run)
    failed_categories = []
    
    for i, category in enumerate(categories_to_run, 1):
        cat_info = test_categories[category]
        
        print(f"\n📋 [{i}/{total_tests}] {cat_info['name']}")
        print(f"    {cat_info['description']}")
        print("-" * 50)
        
        # Run tests for this category
        for test_file in cat_info['tests']:
            if not Path(test_file).exists():
                print(f"⚠️  Test file not found: {test_file}")
                continue
                
            print(f"🔍 Running {test_file}...")
            
            cmd = ['python', '-m', 'pytest', test_file, '-v']
            if not args.verbose:
                cmd.extend(['--tb=short', '-q'])
                
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ PASSED ({duration:.1f}s)")
            else:
                print(f"❌ FAILED ({duration:.1f}s)")
                failed_categories.append(category)
                
                # Show error details
                if result.stdout:
                    print("STDOUT:")
                    print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 REFACTOR TEST SUMMARY")
    print("=" * 50)
    
    if not failed_categories:
        print("✅ ALL TESTS PASSED!")
        print("🎉 Your refactoring appears to be safe.")
        print("\nNext steps:")
        print("  - Run full test suite: pytest")
        print("  - Test manual functionality")
        print("  - Consider running integration tests")
        return 0
    else:
        print(f"❌ {len(failed_categories)} categories FAILED:")
        for category in failed_categories:
            cat_info = test_categories[category]
            print(f"  - {cat_info['name']}")
            
        print(f"\n🚨 REFACTORING ISSUES DETECTED!")
        print("These tests catch the types of issues we encountered previously:")
        print("  - Environment/dependency problems")
        print("  - Frontend-backend communication breakdown")  
        print("  - Audio pipeline configuration issues")
        print("  - File organization problems")
        print("\nRecommended actions:")
        print("  1. Fix the failing tests before proceeding")
        print("  2. Verify manual functionality")
        print("  3. Check file paths and imports")
        print("  4. Validate configuration files")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 