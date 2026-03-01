#!/usr/bin/env python3
"""
Bobby Orchestrator Interactive Test (Manual)

Writes mock transcript lines and triggers so you can observe the orchestrator
reacting in a second terminal.

Requires: Two terminals (one for orchestrator, one for this script)

Usage:
    Terminal 1: uv run python3 -m bobby.orchestrator
    Terminal 2: uv run python3 tests/manual/test_orchestrator.py

WHAT TO VERIFY:
  - Orchestrator detects "Hey Bobby, please build this" trigger
  - Orchestrator speaks acknowledgment (voice or fallback text)
  - Orchestrator detects "Thank you, Bobby" and extracts the answer
  - Debounce prevents duplicate triggers within 30 seconds
"""

import time
import os
import sys
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from bobby.config import TRANSCRIPT_FILE


def test_launch_trigger():
    """Test 1: Launch agent trigger"""
    print("=" * 60)
    print("TEST 1: Launch Agent Trigger")
    print("=" * 60)

    # Clear or create transcript file
    TRANSCRIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSCRIPT_FILE, 'w') as f:
        f.write("")

    print("\nSetup: Starting with empty transcript")
    print("Action: Run the orchestrator in another terminal:")
    print("  uv run python3 -m bobby.orchestrator")
    print("\nWhen orchestrator is running, press ENTER to add trigger...")
    input()

    # Add meeting context
    with open(TRANSCRIPT_FILE, 'a') as f:
        f.write("[00:00:00] Speaker A: We need a pricing page\n")
        f.write("[00:00:15] Speaker B: Three tiers would be good\n")
        f.write("[00:00:30] Speaker A: Make sure it matches our design system\n")

    print("Added meeting context to transcript")
    time.sleep(1)

    # Add trigger
    with open(TRANSCRIPT_FILE, 'a') as f:
        f.write("[00:00:45] Speaker A: Hey Bobby, please build this\n")

    print("\nAdded trigger: 'Hey Bobby, please build this'")
    print("\nCheck orchestrator output:")
    print("  - Should detect trigger")
    print("  - Should say 'Sure, working on it now'")
    print("  - Should launch Claude agent")
    print("\n" + "=" * 60)


def test_resume_trigger():
    """Test 2: Resume agent trigger"""
    print("\n" + "=" * 60)
    print("TEST 2: Resume Agent Trigger")
    print("=" * 60)

    print("\nSetup: This simulates Bobby asking a question")
    print("Action: Add agent question to agent_progress.txt:")
    print("  echo 'QUESTION: Should pricing be monthly or annual?' >> agent_progress.txt")
    print("\nPress ENTER to continue with answer trigger...")
    input()

    # Add answer and trigger
    with open(TRANSCRIPT_FILE, 'a') as f:
        f.write("[00:03:00] Speaker A: Monthly pricing please\n")
        f.write("[00:03:05] Speaker A: Thank you, Bobby\n")

    print("\nAdded answer and trigger: 'Thank you, Bobby'")
    print("\nCheck orchestrator output:")
    print("  - Should detect trigger")
    print("  - Should extract answer: 'Monthly pricing please'")
    print("  - Should resume Claude agent")
    print("\n" + "=" * 60)


def test_debounce():
    """Test 3: Debounce (should ignore duplicate trigger)"""
    print("\n" + "=" * 60)
    print("TEST 3: Debounce Test")
    print("=" * 60)

    print("\nThis tests that repeated triggers are ignored (30s debounce)")
    print("Press ENTER to add duplicate trigger...")
    input()

    # Add duplicate trigger (should be ignored)
    with open(TRANSCRIPT_FILE, 'a') as f:
        f.write("[00:00:50] Speaker B: Hey Bobby, please build this\n")

    print("\nAdded duplicate trigger within 30 seconds")
    print("\nCheck orchestrator output:")
    print("  - Should ignore trigger (debounced)")
    print("\n" + "=" * 60)


def manual_test():
    """Manual test mode - add lines interactively"""
    print("\n" + "=" * 60)
    print("MANUAL TEST MODE")
    print("=" * 60)

    # Create fresh transcript
    TRANSCRIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSCRIPT_FILE, 'w') as f:
        f.write("")

    print("\nCreated fresh transcript file")
    print("Start orchestrator in another terminal:")
    print("  uv run python3 -m bobby.orchestrator")
    print("\nThen add lines manually by typing them here.")
    print("Type 'quit' to exit.\n")

    while True:
        line = input("Add line > ")

        if line.lower() == 'quit':
            break

        # Add timestamp if not present
        if not line.startswith('['):
            timestamp = time.strftime("%H:%M:%S")
            line = f"[{timestamp}] Speaker A: {line}"

        with open(TRANSCRIPT_FILE, 'a') as f:
            f.write(line + '\n')

        print(f"Added: {line}")


def main():
    """Run tests"""
    print("\n" + "=" * 60)
    print("BOBBY ORCHESTRATOR TEST SUITE")
    print("=" * 60)

    print("\nAvailable tests:")
    print("  1. Launch agent trigger test")
    print("  2. Resume agent trigger test")
    print("  3. Debounce test")
    print("  4. Manual test mode")
    print("  5. Run all automated tests")

    choice = input("\nSelect test (1-5): ").strip()

    if choice == '1':
        test_launch_trigger()
    elif choice == '2':
        test_resume_trigger()
    elif choice == '3':
        test_debounce()
    elif choice == '4':
        manual_test()
    elif choice == '5':
        test_launch_trigger()
        print("\nWait 30 seconds for debounce to reset...")
        time.sleep(30)
        test_resume_trigger()
        test_debounce()
    else:
        print("Invalid choice")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
