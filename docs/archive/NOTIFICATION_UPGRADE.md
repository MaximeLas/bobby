# Bobby Notification System Upgrade

**Date:** 2025-10-25
**Status:** ✅ Complete
**Component:** Progress Watcher (Component 4)

## What Changed

Upgraded Bobby's notification system from `osascript` to `terminal-notifier` for reliable macOS notifications.

### Before (osascript)

```python
# Used AppleScript - didn't appear on Max's system
script = f'display notification "{message}" with title "{title}"'
subprocess.run(['osascript', '-e', script], ...)
```

**Problems:**

- Notifications not appearing on macOS
- No "Script Editor" in System Settings → Notifications
- Permission issues with osascript
- Unreliable delivery

### After (terminal-notifier)

```python
# Uses proper macOS notification tool
subprocess.run([
    'terminal-notifier',
    '-title', title,
    '-message', message,
    '-sender', 'com.apple.Terminal',
    '-group', 'bobby-progress'
], ...)
```

**Benefits:**

- ✅ Notifications appear reliably
- ✅ Shows as "Terminal" in System Settings → Notifications
- ✅ Proper macOS notification center integration
- ✅ Supports sounds (for questions)
- ✅ Groups notifications together
- ✅ User can control notification style in System Settings

## Files Changed

### Updated

1. **bobby/progress_watcher.py** - Line 61-100
   - Replaced `send_notification()` method
   - Now uses terminal-notifier instead of osascript
   - Added sound for question notifications
   - Better error handling

### New Files

2. **test_terminal_notifier.py** - Comprehensive test suite

   - Tests all 5 notification types
   - Verifies installation
   - Provides troubleshooting guidance

3. **bobby/setup_notifications.sh** - Easy setup script
   - Installs terminal-notifier via Homebrew
   - Sends test notification
   - Provides troubleshooting tips

### Documentation Updated

4. **QUICKSTART_PROGRESS_WATCHER.md**
   - Added terminal-notifier to requirements
   - Updated troubleshooting section
   - Added installation instructions

## Installation

**Install terminal-notifier:**

```bash
brew install terminal-notifier
```

**Or use the setup script:**

```bash
./bobby/setup_notifications.sh
```

## Testing

**Test notifications:**

```bash
python3 test_terminal_notifier.py
```

You should see 5 notifications:

1. Basic test notification
2. Progress notification
3. Question notification (with sound)
4. Complete notification
5. Error notification

**Test with progress watcher:**

```bash
# Terminal 1
python3 bobby/progress_watcher.py

# Terminal 2
echo "QUESTION: Can you see this?" >> agent_progress.txt
echo "COMPLETE: Testing done!" >> agent_progress.txt
```

## Features

### Notification Types

| Type     | Title            | Sound | Group          |
| -------- | ---------------- | ----- | -------------- |
| PROGRESS | "Bobby Progress" | No    | bobby-progress |
| QUESTION | "Bobby Question" | Yes ✓ | bobby-progress |
| COMPLETE | "Bobby Complete" | No    | bobby-progress |
| ERROR    | "Bobby Error"    | No    | bobby-progress |

### Sound on Questions

Questions play the default macOS sound to grab attention:

```python
if 'question' in title.lower():
    cmd.extend(['-sound', 'default'])
```

### Grouped Notifications

All Bobby notifications are grouped with `-group bobby-progress`:

- Shows as one conversation in Notification Center
- User can clear all Bobby notifications at once
- Cleaner notification history

### Sender ID

Notifications show as "Terminal" in System Settings:

```python
'-sender', 'com.apple.Terminal'
```

This means:

- Users can control Bobby's notification style
- Can enable/disable in System Settings → Notifications → Terminal
- Proper macOS integration

## Troubleshooting

### Notifications not appearing?

**1. Check if terminal-notifier is installed:**

```bash
which terminal-notifier
# Should output: /opt/homebrew/bin/terminal-notifier
```

**2. Check System Settings:**

1. Open System Settings → Notifications
2. Find "Terminal" in the list
3. Make sure:
   - Allow Notifications is ON
   - Notification style is "Banners" or "Alerts"
   - Show previews is enabled

**3. Check Focus/Do Not Disturb:**

- Make sure Do Not Disturb is OFF
- Check in macOS Control Center

**4. Test manually:**

```bash
terminal-notifier -title "Test" -message "Hello!" -sender com.apple.Terminal
```

### Permission issues?

Terminal-notifier should work immediately after installation. If not:

1. Open System Settings → Notifications
2. Enable notifications for Terminal
3. Restart the progress watcher

### Still not working?

Run the comprehensive test:

```bash
python3 test_terminal_notifier.py
```

Follow the on-screen instructions.

## Code Changes Details

### send_notification() Method

**Key improvements:**

1. **Cleaner command building:**

   - No string escaping needed (uses list arguments)
   - More readable code
   - Less error-prone

2. **Enhanced features:**

   - Sound for questions
   - Notification grouping
   - Proper sender ID

3. **Better error handling:**
   - FileNotFoundError → helpful install message
   - TimeoutExpired → specific timeout message
   - General exceptions → clear error reporting

**Full implementation:**

```python
def send_notification(self, title, message):
    """
    Send macOS notification using terminal-notifier

    Args:
        title: Notification title
        message: Notification message
    """
    try:
        # Build terminal-notifier command
        cmd = [
            'terminal-notifier',
            '-title', title,
            '-message', message,
            '-sender', 'com.apple.Terminal',
            '-group', 'bobby-progress'
        ]

        # Add sound for questions
        if 'question' in title.lower():
            cmd.extend(['-sound', 'default'])

        # Execute terminal-notifier
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=5,
            check=False
        )

        # Log notification sent
        if RICH_AVAILABLE:
            self.console.print(f"[dim]   📢 Notification sent: {title}[/dim]")

    except FileNotFoundError:
        print("⚠️  terminal-notifier not found. Install with: brew install terminal-notifier")
    except subprocess.TimeoutExpired:
        print(f"⚠️  Notification timed out: {title}")
    except Exception as e:
        print(f"⚠️  Notification error: {e}")
```

## Testing Checklist

- [x] Install terminal-notifier via homebrew
- [x] Update send_notification() method
- [x] Test with test script - notifications appear ✓
- [x] Create test_terminal_notifier.py
- [x] Create setup_notifications.sh
- [x] Update QUICKSTART_PROGRESS_WATCHER.md
- [x] Verify all notification types work
- [x] Test with progress_watcher.py
- [x] Document the change

## Success Criteria

✅ **All met:**

1. terminal-notifier installed
2. Notifications appear on screen
3. "Terminal" appears in System Settings → Notifications
4. All 5 notification types tested
5. Sound works for questions
6. Documentation updated
7. Test scripts created

## Next Steps

1. **For development:**

   - Progress watcher now works reliably
   - Ready for integration with orchestrator
   - Notifications will show during meetings

2. **For demo with Kevin & Michelle:**

   - Make sure System Settings → Notifications → Terminal is enabled
   - Test before the meeting
   - Consider enabling "Banners" style (non-intrusive)

3. **Future enhancements (optional):**
   - Custom app icon for Bobby notifications
   - Different sounds for different notification types
   - Click actions (e.g., click notification to open terminal)

## Summary

**Before:** Notifications didn't work (osascript permission issues)
**After:** Notifications work perfectly (terminal-notifier integration)
**Result:** Bobby can now properly notify users during meetings! 🎉

---

**This upgrade makes Bobby production-ready for the Kevin & Michelle demo!**
