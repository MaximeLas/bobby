#!/usr/bin/env python3
"""
Bobby Notification Test (Manual)

Fires 5 macOS notifications to verify terminal-notifier works.
Requires: brew install terminal-notifier

Usage: uv run python3 tests/manual/test_notifications.py

WHAT TO VERIFY:
  - 5 notifications appear in the top-right corner of your screen
  - Notification #3 (Question) plays a sound
  - If nothing appears, check System Settings > Notifications > Terminal
"""

import subprocess
import time


def main():
    # Check if terminal-notifier is installed
    result = subprocess.run(['which', 'terminal-notifier'], capture_output=True)
    if result.returncode != 0:
        print("terminal-notifier not found. Install with: brew install terminal-notifier")
        return

    print("=" * 60)
    print("  Bobby Notification Test")
    print("=" * 60)
    print()
    print("  Sending 5 notifications. Watch the top-right of your screen.")
    print()

    notifications = [
        ("Bobby Test", "1/5: Basic notification working"),
        ("Bobby Progress", "2/5: Progress update notification"),
        ("Bobby Question", "3/5: Question notification (with sound)"),
        ("Bobby Complete", "4/5: Task complete notification"),
        ("Bobby Error", "5/5: Error notification"),
    ]

    for i, (title, message) in enumerate(notifications):
        cmd = [
            'terminal-notifier',
            '-title', title,
            '-message', message,
            '-group', f'bobby-test-{i}',
        ]
        if 'Question' in title:
            cmd.extend(['-sound', 'default'])

        print(f"  Sending: {title} - {message}")
        subprocess.run(cmd, capture_output=True)
        time.sleep(2)

    print()
    print("=" * 60)
    print("  VERIFY: Did you see 5 notifications?")
    print("  If not: System Settings > Notifications > Terminal > Enable")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
