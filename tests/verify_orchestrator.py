#!/usr/bin/env python3
"""
Quick verification that orchestrator imports and basic functions work
"""

import os
import sys
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.config import TRANSCRIPT_FILE

def test_import():
    """Test that orchestrator can be imported"""
    print("Testing import...")
    try:
        from bobby import orchestrator
        print("  OK - orchestrator module imported successfully")
        return True
    except Exception as e:
        print(f"  FAIL - Could not import: {e}")
        return False


def test_class_instantiation():
    """Test that Orchestrator class can be instantiated"""
    print("\nTesting class instantiation...")
    try:
        from bobby.orchestrator import Orchestrator
        orch = Orchestrator()
        print("  OK - Orchestrator class instantiated successfully")
        return True
    except Exception as e:
        print(f"  FAIL - Could not instantiate: {e}")
        return False


def test_get_context():
    """Test get_recent_context method"""
    print("\nTesting get_recent_context()...")
    try:
        from bobby.orchestrator import Orchestrator

        # Create test transcript at the config-defined path
        TRANSCRIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRANSCRIPT_FILE, 'w') as f:
            f.write("[00:00:00] Speaker A: Line 1\n")
            f.write("[00:00:01] Speaker B: Line 2\n")
            f.write("[00:00:02] Speaker A: Line 3\n")

        orch = Orchestrator()
        context = orch.get_recent_context(lines=2)

        if "Line 2" in context and "Line 3" in context:
            print("  OK - Context extraction works")
            return True
        else:
            print(f"  FAIL - Context doesn't match expected. Got: {context}")
            return False

    except Exception as e:
        print(f"  FAIL - Error: {e}")
        return False
    finally:
        # Clean up
        if TRANSCRIPT_FILE.exists():
            TRANSCRIPT_FILE.unlink()


def test_extract_answer():
    """Test extract_answer method"""
    print("\nTesting extract_answer()...")
    try:
        from bobby.orchestrator import Orchestrator

        orch = Orchestrator()

        # Test case 1: Simple answer
        text = "[00:00:00] Speaker A: The answer is blue\n[00:00:01] Speaker A: Thank you, Bobby"
        answer = orch.extract_answer(text)

        if "blue" in answer:
            print("  OK - Answer extraction works")
            return True
        else:
            print(f"  FAIL - Answer doesn't match. Got: {answer}")
            return False

    except Exception as e:
        print(f"  FAIL - Error: {e}")
        return False


def test_speak_bob():
    """Test speak_bob method"""
    print("\nTesting speak_bob()...")
    try:
        from bobby.orchestrator import Orchestrator

        orch = Orchestrator()
        orch.speak_bob("Test message")
        print("  OK - speak_bob() executes without error")
        return True

    except Exception as e:
        print(f"  FAIL - Error: {e}")
        return False


def test_tts_import():
    """Test TTS module import"""
    print("\nTesting TTS module...")
    try:
        from bobby import tts
        tts.speak("Test")
        print("  OK - TTS module works (placeholder)")
        return True
    except Exception as e:
        print(f"  FAIL - Could not import tts: {e}")
        return False


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("Bobby Orchestrator - Verification Tests")
    print("=" * 60)
    print()

    tests = [
        test_import,
        test_class_instantiation,
        test_get_context,
        test_extract_answer,
        test_speak_bob,
        test_tts_import,
    ]

    results = []
    for test in tests:
        results.append(test())

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\nAll verification tests passed!")
        print("Orchestrator is ready to use.")
        return 0
    else:
        print("\nSome tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
