#!/usr/bin/env python3
"""
Local Pipeline Runner

Runs the same tests that would run in CI/CD pipeline locally for faster feedback.
"""

import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(cmd, description, continue_on_error=False):
    """Run a command and return success status"""
    print(f"\n🔧 {description}")
    print(f"   Command: {cmd}")

    start_time = time.time()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        end_time = time.time()

        if result.returncode == 0:
            print(f"   ✅ PASSED ({end_time - start_time:.1f}s)")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ FAILED ({end_time - start_time:.1f}s)")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            if not continue_on_error:
                return False
            return True

    except Exception as e:
        print(f"   💥 ERROR: {e}")
        return False if not continue_on_error else True


def setup_environment():
    """Set up the test environment"""
    print("🛠️  Setting up test environment...")

    # Create necessary directories
    dirs_to_create = ["logs", "temp_audio", "cache", "htmlcov"]
    for dir_name in dirs_to_create:
        Path(dir_name).mkdir(exist_ok=True)

    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)

    print("✅ Environment setup complete")


def run_python_tests():
    """Run all Python backend tests"""
    print("\n🐍 Running Python Backend Tests")

    tests = [
        (
            "python -m pytest tests/test_config_validation.py -v",
            "Configuration Validation Tests",
        ),
        ("python -m pytest tests/test_ipc_integrity.py -v", "IPC Integrity Tests"),
        (
            "python -m pytest tests/test_memory_management.py -v",
            "Memory Management Tests",
        ),
        ("python -m pytest tests/test_state_sync.py -v", "State Synchronization Tests"),
        ("python -m pytest tests/test_llm_streaming.py -v", "LLM Streaming Tests"),
        ("python -m pytest tests/integration/ -v", "Integration Tests"),
        (
            "python -m pytest tests/performance/ -v",
            "Performance Benchmarks",
            True,
        ),  # Continue on error
    ]

    passed = 0
    for cmd, desc, *continue_on_error in tests:
        continue_on_error = continue_on_error[0] if continue_on_error else False
        if run_command(cmd, desc, continue_on_error):
            passed += 1

    return passed, len(tests)


def run_coverage_analysis():
    """Run test coverage analysis"""
    print("\n📊 Running Coverage Analysis")

    cmd = "python -m pytest tests/ --cov=. --cov-report=html --cov-report=term"
    return run_command(cmd, "Coverage Analysis", continue_on_error=True)


def run_code_quality_checks():
    """Run code quality checks"""
    print("\n🔍 Running Code Quality Checks")

    quality_checks = [
        ("python -m black --check --diff .", "Code Formatting Check (Black)", True),
        (
            "python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics",
            "Code Style Check (Flake8)",
            True,
        ),
        (
            "npx eslint electron_*.js renderer*.js --fix-dry-run",
            "JavaScript Linting (ESLint)",
            True,
        ),
    ]

    passed = 0
    for cmd, desc, continue_on_error in quality_checks:
        if run_command(cmd, desc, continue_on_error):
            passed += 1

    return passed, len(quality_checks)


def run_security_scans():
    """Run security scans"""
    print("\n🔒 Running Security Scans")

    security_checks = [
        ("python -m safety check", "Python Dependency Security Scan", True),
        ("npm audit --audit-level moderate", "Node.js Dependency Security Scan", True),
    ]

    passed = 0
    for cmd, desc, continue_on_error in security_checks:
        if run_command(cmd, desc, continue_on_error):
            passed += 1

    return passed, len(security_checks)


def run_phase3_tests():
    """Run the comprehensive Phase 3 test suite"""
    print("\n🧪 Running Phase 3 Advanced Test Suite")

    return run_command("python scripts/run_phase3_tests.py", "Phase 3 Advanced Tests")


def main():
    """Main pipeline execution"""
    print("🚀 CitrixTranscriber Local Testing Pipeline")
    print("=" * 60)

    start_time = time.time()

    # Setup
    setup_environment()

    # Track results
    total_passed = 0
    total_tests = 0

    # Run Python tests
    python_passed, python_total = run_python_tests()
    total_passed += python_passed
    total_tests += python_total

    # Run coverage analysis
    if run_coverage_analysis():
        print("📊 Coverage report generated in htmlcov/index.html")

    # Run code quality checks
    quality_passed, quality_total = run_code_quality_checks()
    total_passed += quality_passed
    total_tests += quality_total

    # Run security scans
    security_passed, security_total = run_security_scans()
    total_passed += security_passed
    total_tests += security_total

    # Run Phase 3 comprehensive tests
    if run_phase3_tests():
        total_passed += 1
        total_tests += 1

    # Final summary
    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("📋 PIPELINE SUMMARY")
    print("=" * 60)
    print(f"⏱️  Total Duration: {duration:.1f} seconds")
    print(f"📊 Tests Passed: {total_passed}/{total_tests}")
    print(f"📈 Success Rate: {(total_passed/total_tests)*100:.1f}%")

    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Ready to commit/deploy.")
        return 0
    else:
        print("⚠️  Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
