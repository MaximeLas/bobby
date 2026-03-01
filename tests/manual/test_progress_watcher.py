#!/usr/bin/env python3
"""
Bobby Progress Watcher Interactive Test (Manual)

Writes simulated agent progress lines so you can observe the watcher
rendering them with Rich colors and macOS notifications.

Requires: Two terminals (one for watcher, one for this script)

Usage:
    Terminal 1: uv run python3 -m bobby.progress_watcher
    Terminal 2: uv run python3 tests/manual/test_progress_watcher.py

WHAT TO VERIFY:
  - PROGRESS lines appear in cyan (in-progress) or green (completed with checkmark)
  - QUESTION line appears in yellow bold
  - COMPLETE line appears in green bold
  - ERROR line appears in red bold
  - macOS notifications fire for each update
"""

import time
import os
import sys
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from bobby.config import PROGRESS_FILE

# Test updates - simulates what agent would write
test_updates = [
    "PROGRESS: → Reading meeting transcript...",
    "PROGRESS:   ✓ Found meeting context",
    "PROGRESS: → Analyzing codebase structure...",
    "PROGRESS:   ✓ Identified src/components/ directory",
    "PROGRESS: → Creating PricingTable component...",
    "PROGRESS:   ✓ Component created",
    "QUESTION: Should pricing default to monthly or annual?",
    "PROGRESS: → Implementing monthly pricing as default...",
    "PROGRESS:   ✓ Pricing logic implemented",
    "PROGRESS: → Adding component to Landing page...",
    "PROGRESS:   ✓ Imported in Landing.jsx",
    "PROGRESS: → Testing component rendering...",
    "PROGRESS:   ✓ Component renders correctly",
    "COMPLETE: Pricing table added. Visible on localhost:5173",
]

# Test with an error
test_with_error = [
    "PROGRESS: → Running build...",
    "PROGRESS:   ✓ Build started",
    "ERROR: Build failed - missing dependency 'react-icons'",
]


def clear_progress_file():
    """Clear the progress file"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        f.write('')
    print(f"✓ Cleared {PROGRESS_FILE}\n")


def write_update(update, delay=2.0):
    """Write a single update to progress file"""
    with open(PROGRESS_FILE, 'a') as f:
        f.write(update + '\n')
    print(f"✏️  Added: {update}")
    time.sleep(delay)


def run_success_scenario():
    """Run successful task scenario"""
    print("🎬 Running SUCCESS scenario...")
    print("=" * 60)
    print("This simulates Bobby successfully completing a task.\n")

    clear_progress_file()
    time.sleep(1)

    print("📝 Writing progress updates (2 seconds between each)...\n")

    for update in test_updates:
        write_update(update)

    print("\n✅ Success scenario complete!")
    print("Check the progress watcher terminal for colored output.")
    print("Check macOS notifications - you should have received several!\n")


def run_error_scenario():
    """Run error scenario"""
    print("🎬 Running ERROR scenario...")
    print("=" * 60)
    print("This simulates Bobby encountering an error.\n")

    clear_progress_file()
    time.sleep(1)

    print("📝 Writing progress updates with error...\n")

    for update in test_with_error:
        write_update(update)

    print("\n❌ Error scenario complete!")
    print("You should see a red error message in the watcher.\n")


def run_interactive_mode():
    """Interactive mode - type your own updates"""
    print("🎮 INTERACTIVE MODE")
    print("=" * 60)
    print("Type updates to send to the watcher.")
    print("Prefix with PROGRESS:, QUESTION:, COMPLETE:, or ERROR:")
    print("Examples:")
    print("  PROGRESS: → Doing something...")
    print("  QUESTION: What color should the button be?")
    print("  COMPLETE: Task finished!")
    print("  ERROR: Something went wrong")
    print("\nType 'quit' to exit.\n")

    clear_progress_file()

    while True:
        try:
            update = input("Update: ").strip()

            if update.lower() == 'quit':
                print("\n👋 Exiting interactive mode")
                break

            if update:
                with open(PROGRESS_FILE, 'a') as f:
                    f.write(update + '\n')
                print(f"✓ Sent: {update}\n")

        except KeyboardInterrupt:
            print("\n\n👋 Exiting interactive mode")
            break


def main():
    """Main test menu"""
    print("\n🧪 Progress Watcher Test Script")
    print("=" * 60)
    print()
    print("Make sure progress_watcher.py is running in another terminal!")
    print()
    print("Choose a test scenario:")
    print("  1. Success scenario (complete task)")
    print("  2. Error scenario (task fails)")
    print("  3. Interactive mode (type your own)")
    print("  4. Quick test (one of each type)")
    print("  q. Quit")
    print()

    choice = input("Enter choice (1-4 or q): ").strip()

    if choice == '1':
        run_success_scenario()
    elif choice == '2':
        run_error_scenario()
    elif choice == '3':
        run_interactive_mode()
    elif choice == '4':
        print("\n🚀 Quick test - one of each type...\n")
        clear_progress_file()
        time.sleep(0.5)
        write_update("PROGRESS: → Starting task...", delay=1.5)
        write_update("QUESTION: Need clarification on something?", delay=1.5)
        write_update("PROGRESS:   ✓ Got answer, continuing...", delay=1.5)
        write_update("COMPLETE: Task finished successfully!", delay=1.5)
        print("\n✅ Quick test complete!")
    elif choice.lower() == 'q':
        print("👋 Bye!")
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()
