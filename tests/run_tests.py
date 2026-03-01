#!/usr/bin/env python3
"""
Bobby Test Runner

Runs all automated tests and validates that interactive test scripts load correctly.
Use this as the single entry point for verifying the test suite.

Usage:
    uv run python3 tests/run_tests.py           # Run all automated tests
    python3 tests/run_tests.py                   # Also works without uv run

Interactive tests (run manually):
    uv run python3 tests/test_tts.py             # Voice output test (needs API key)
    uv run python3 tests/test_orchestrator.py    # Trigger simulation (needs 2 terminals)
    uv run python3 tests/test_progress_watcher.py # Progress display (needs 2 terminals)
    uv run python3 tests/test_integration.py     # Full pipeline (needs mic + API key)
    uv run python3 tests/test_notifications.py   # macOS notifications
    ./tests/demo_orchestrator.sh                 # Shell demo for orchestrator
    ./tests/demo_progress_watcher.sh             # Shell demo for progress watcher
"""

import importlib.util
import sys
import os
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.config import TRANSCRIPT_FILE, PROGRESS_FILE, PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE

# Files created during tests that should be cleaned up
TEST_ARTIFACTS = [TRANSCRIPT_FILE, PROGRESS_FILE, PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE]


def run_section(title):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def cleanup_test_artifacts():
    """Remove any files created during test runs."""
    cleaned = []
    for path in TEST_ARTIFACTS:
        if path.exists():
            path.unlink()
            cleaned.append(path.name)
    return cleaned


def test_imports():
    """Validate that all Python test files load without errors."""
    run_section("Import Validation")

    test_files = sorted(Path(__file__).parent.glob("*.py"))
    test_files = [f for f in test_files if f.name != "run_tests.py"]

    passed = 0
    failed = 0

    for test_file in test_files:
        try:
            spec = importlib.util.spec_from_file_location("test_module", test_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            print(f"  OK   {test_file.name}")
            passed += 1
        except SystemExit:
            print(f"  OK   {test_file.name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {test_file.name}: {e}")
            failed += 1

    print(f"\n  Imports: {passed} OK, {failed} failed")
    return failed == 0


def test_verify_orchestrator():
    """Run the automated orchestrator verification suite."""
    run_section("Orchestrator Verification (6 tests)")

    # Import and run verify_orchestrator
    spec = importlib.util.spec_from_file_location(
        "verify_orchestrator",
        Path(__file__).parent / "verify_orchestrator.py"
    )
    mod = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(mod)
        result = mod.main()
        return result == 0
    except SystemExit as e:
        return e.code == 0
    except Exception as e:
        print(f"  FAIL - Unexpected error: {e}")
        return False


def test_config_paths():
    """Verify config paths resolve correctly."""
    run_section("Config Path Validation")

    from bobby.config import PROJECT_ROOT, WORKSPACE_DIR

    checks = [
        ("PROJECT_ROOT exists", PROJECT_ROOT.exists()),
        ("WORKSPACE_DIR parent exists", WORKSPACE_DIR.parent.exists()),
        ("bobby package exists", (PROJECT_ROOT / "bobby" / "__init__.py").exists()),
        ("config.py exists", (PROJECT_ROOT / "bobby" / "config.py").exists()),
    ]

    all_ok = True
    for name, result in checks:
        status = "OK" if result else "FAIL"
        if not result:
            all_ok = False
        print(f"  {status:4s} {name}")

    return all_ok


def main():
    """Run the full test suite."""
    print()
    print("Bobby Test Suite")
    print("~~~~~~~~~~~~~~~~")

    # Track artifacts that exist before tests run
    pre_existing = {p for p in TEST_ARTIFACTS if p.exists()}

    results = {}

    # Run test sections
    results["Config paths"] = test_config_paths()
    results["Import validation"] = test_imports()
    results["Orchestrator verification"] = test_verify_orchestrator()

    # Summary
    run_section("Results")

    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  {status}  {name}")

    # Cleanup: only remove artifacts that didn't exist before tests ran
    new_artifacts = {p for p in TEST_ARTIFACTS if p.exists()} - pre_existing
    if new_artifacts:
        print()
        print("  Cleaning up test artifacts...")
        for path in new_artifacts:
            path.unlink()
            print(f"    Removed {path.name}")

    # Final verdict
    print()
    if all_passed:
        print("  All tests passed.")
    else:
        print("  Some tests failed. See details above.")
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
