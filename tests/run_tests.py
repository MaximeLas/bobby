#!/usr/bin/env python3
"""
Bobby Test Runner

Discovers and runs all automated tests. Each test module in tests/ exposes an
ALL_TESTS list of (name, function) tuples. This runner collects them all,
runs them, and reports results.

Usage:
    uv run python3 tests/run_tests.py         # Run all automated tests
    python3 tests/run_tests.py                 # Also works directly

Manual tests (require human verification) live in tests/manual/:
    uv run python3 tests/manual/test_tts.py
    uv run python3 tests/manual/test_notifications.py
    uv run python3 tests/manual/test_orchestrator.py
    uv run python3 tests/manual/test_progress_watcher.py
    uv run python3 tests/manual/test_integration.py
    ./tests/manual/demo_orchestrator.sh
    ./tests/manual/demo_progress_watcher.sh
"""

import importlib.util
import sys
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.config import TRANSCRIPT_FILE, PROGRESS_FILE, PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE

# Files that tests might create — cleaned up after each run
TEST_ARTIFACTS = [TRANSCRIPT_FILE, PROGRESS_FILE, PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE]

# Test modules to discover (each must expose ALL_TESTS)
TEST_MODULES = [
    "test_config",
    "test_orchestrator",
    "test_progress_watcher",
]


def load_tests():
    """Load ALL_TESTS from each test module."""
    tests_dir = Path(__file__).parent
    all_tests = []

    for module_name in TEST_MODULES:
        module_path = tests_dir / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        module_tests = getattr(mod, "ALL_TESTS", [])
        for name, func in module_tests:
            all_tests.append((module_name, name, func))

    return all_tests


def run_tests():
    """Run all tests and return results."""
    tests = load_tests()
    results = []
    current_module = None

    for module_name, test_name, test_func in tests:
        if module_name != current_module:
            current_module = module_name
            print()
            print(f"  {module_name}")
            print(f"  {'-' * len(module_name)}")

        try:
            test_func()
            print(f"    PASS  {test_name}")
            results.append((test_name, True, None))
        except Exception as e:
            print(f"    FAIL  {test_name}")
            print(f"          {e}")
            results.append((test_name, False, str(e)))

    return results


def main():
    """Run the full test suite."""
    print()
    print("=" * 60)
    print("  Bobby Automated Test Suite")
    print("=" * 60)

    # Track pre-existing artifacts so we don't delete them
    pre_existing = {p for p in TEST_ARTIFACTS if p.exists()}

    # Run tests
    results = run_tests()

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)

    print()
    print("=" * 60)

    if failed:
        print(f"  {passed}/{total} passed, {failed} FAILED")
        print()
        print("  Failed tests:")
        for name, ok, err in results:
            if not ok:
                print(f"    - {name}: {err}")
    else:
        print(f"  All {total} tests passed.")

    # Cleanup: remove artifacts created during this run
    new_artifacts = {p for p in TEST_ARTIFACTS if p.exists()} - pre_existing
    if new_artifacts:
        print()
        print("  Cleaned up test artifacts:")
        for path in sorted(new_artifacts):
            path.unlink()
            print(f"    {path.name}")

    print("=" * 60)
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
