#!/usr/bin/env python3
"""Test terminal-notifier integration"""
import subprocess
import time
import sys

def test_terminal_notifier():
    """Test if terminal-notifier works"""

    print("🧪 Testing terminal-notifier...")
    print()

    # Check if installed
    result = subprocess.run(['which', 'terminal-notifier'], capture_output=True)
    if result.returncode != 0:
        print("❌ terminal-notifier not found. Installing...")
        subprocess.run(['brew', 'install', 'terminal-notifier'])
    else:
        print("✅ terminal-notifier is installed")
        print(f"   Location: {result.stdout.decode().strip()}")

    print()
    print("=" * 60)
    print("📢 NOTIFICATION TEST STARTING")
    print("=" * 60)
    print()
    print("Watch your screen for notifications!")
    print("They should appear in the top-right corner.")
    print()

    # Test 1: Basic notification
    print("1️⃣  Sending basic notification...")
    subprocess.run([
        'terminal-notifier',
        '-title', 'Bobby Test',
        '-message', 'If you see this, notifications are working! 🎉',
        '-sender', 'com.apple.Terminal'
    ])
    time.sleep(3)

    # Test 2: Progress notification
    print("2️⃣  Sending progress notification...")
    subprocess.run([
        'terminal-notifier',
        '-title', 'Bobby Progress',
        '-message', '→ Testing progress notification...',
        '-group', 'bobby-progress'
    ])
    time.sleep(2)

    # Test 3: Question notification (with sound)
    print("3️⃣  Sending question notification (with sound)...")
    subprocess.run([
        'terminal-notifier',
        '-title', 'Bobby Question',
        '-message', '❓ Does this notification appear?',
        '-sound', 'default',
        '-group', 'bobby-progress'
    ])
    time.sleep(2)

    # Test 4: Complete notification
    print("4️⃣  Sending complete notification...")
    subprocess.run([
        'terminal-notifier',
        '-title', 'Bobby Complete',
        '-message', '✅ All tests passing!',
        '-group', 'bobby-progress'
    ])
    time.sleep(2)

    # Test 5: Error notification
    print("5️⃣  Sending error notification...")
    subprocess.run([
        'terminal-notifier',
        '-title', 'Bobby Error',
        '-message', '❌ Test error message',
        '-group', 'bobby-progress'
    ])

    print()
    print("=" * 60)
    print("✅ TEST COMPLETE!")
    print("=" * 60)
    print()
    print("Did you see 5 notifications?")
    print("  1. 'If you see this...'")
    print("  2. 'Testing progress notification...'")
    print("  3. 'Does this notification appear?' (with sound)")
    print("  4. 'All tests passing!'")
    print("  5. 'Test error message'")
    print()
    print("✅ If YES → Success! Notifications are working!")
    print("⚠️  If NO → Check System Settings → Notifications → Terminal")
    print()
    print("To enable notifications:")
    print("  1. Open System Settings")
    print("  2. Go to Notifications")
    print("  3. Find 'Terminal' in the list")
    print("  4. Enable notifications with 'Banners' style")
    print("=" * 60)

if __name__ == "__main__":
    test_terminal_notifier()
