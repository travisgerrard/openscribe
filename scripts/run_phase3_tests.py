#!/usr/bin/env python3
"""
Phase 3 Test Runner

Runs all Phase 3 advanced testing components and provides a comprehensive summary.
"""

import subprocess
import time
import sys
import os


def run_test_suite(test_name: str, test_path: str) -> bool:
    """Run a test suite and return success status"""
    print(f"🧪 Running {test_name}...")
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, test_path], capture_output=True, text=True, timeout=300
        )
        end_time = time.time()

        if result.returncode == 0:
            print(f"✅ {test_name}: PASSED ({end_time - start_time:.1f}s)")
            return True
        else:
            print(f"❌ {test_name}: FAILED ({end_time - start_time:.1f}s)")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()[:200]}...")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name}: TIMEOUT (>300s)")
        return False
    except Exception as e:
        print(f"💥 {test_name}: ERROR ({e})")
        return False


def main():
    """Run all Phase 3 tests"""
    print("=== PHASE 3 ADVANCED TESTING SUMMARY ===\n")

    # Change to project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    # Define test suites
    test_suites = [
        (
            "End-to-End Integration Tests",
            "tests/integration/test_end_to_end_dictation.py",
        ),
        ("Performance Benchmark Tests", "tests/performance/test_latency_benchmarks.py"),
    ]

    # Run all test suites
    passed = 0
    total = len(test_suites)

    for test_name, test_path in test_suites:
        if os.path.exists(test_path):
            if run_test_suite(test_name, test_path):
                passed += 1
        else:
            print(f"⚠️ {test_name}: FILE NOT FOUND ({test_path})")
        print()

    # Summary
    print("=" * 50)
    print(f"📊 PHASE 3 RESULTS: {passed}/{total} test suites passed")

    if passed == total:
        print("🎉 Phase 3 Advanced Testing: COMPLETE!")
        print("✅ End-to-end integration validation working")
        print("✅ Performance monitoring infrastructure ready")
        print("✅ Advanced testing framework established")

        print("\n🚀 Ready for Phase 4: CI/CD Pipeline Setup")
        return 0
    else:
        print("⚠️ Some Phase 3 components need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
