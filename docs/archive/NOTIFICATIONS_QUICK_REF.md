# Bobby Notifications - Quick Reference

**Status:** ✅ Working
**Tool:** terminal-notifier
**Last Updated:** 2025-10-25

---

## Quick Commands

### Install

```bash
brew install terminal-notifier
# Or
./bobby/setup_notifications.sh
```

### Test

```bash
# Quick test (5 notifications)
python3 test_terminal_notifier.py

# Full verification (6 checks)
./verify_notifications.sh

# Manual test
terminal-notifier -title "Test" -message "Hello!" -sender com.apple.Terminal
```

### Use

```bash
# Start progress watcher
python3 bobby/progress_watcher.py

# Add test updates (in another terminal)
echo "QUESTION: Test question?" >> agent_progress.txt
echo "COMPLETE: Task done!" >> agent_progress.txt
```

---

## Notification Types

| Format      | Title          | Sound   | Example               |
| ----------- | -------------- | ------- | --------------------- |
| `PROGRESS:` | Bobby Progress | No      | `→ Reading code...`   |
| `QUESTION:` | Bobby Question | **Yes** | `Should I use React?` |
| `COMPLETE:` | Bobby Complete | No      | `Feature deployed!`   |
| `ERROR:`    | Bobby Error    | No      | `Build failed`        |

---

## System Settings

**Location:** System Settings → Notifications → Terminal

**Required:**

- Allow Notifications: **ON**
- Notification style: **Banners** or Alerts
- Show previews: **On**

**Optional:**

- Play sound: **On** (for questions)
- Badge app icon: Off

---

## Troubleshooting

### Not seeing notifications?

**1. Check installation:**

```bash
which terminal-notifier
# Should output: /opt/homebrew/bin/terminal-notifier
```

**2. Check System Settings:**

- System Settings → Notifications → Terminal
- Make sure "Allow Notifications" is ON

**3. Check Focus mode:**

- Make sure Do Not Disturb is OFF

**4. Run verification:**

```bash
./verify_notifications.sh
```

### Still not working?

**Manual test:**

```bash
terminal-notifier -title "Test" -message "Can you see this?" -sender com.apple.Terminal
```

If this doesn't show:

- System Settings → Notifications → Terminal → Enable notifications
- Restart Terminal app
- Check macOS notification center is accessible

---

## Files

| File                           | Purpose                               |
| ------------------------------ | ------------------------------------- |
| `bobby/progress_watcher.py`    | Main watcher (uses terminal-notifier) |
| `test_terminal_notifier.py`    | Test all notification types           |
| `bobby/setup_notifications.sh` | Install & setup                       |
| `verify_notifications.sh`      | Full system check                     |
| `NOTIFICATION_UPGRADE.md`      | Technical details                     |
| `DELIVERY_NOTIFICATION_FIX.md` | Complete summary                      |

---

## Features

- **Sound on questions:** Grabs attention during meetings
- **Grouped notifications:** All under "bobby-progress"
- **Sender ID:** Shows as "Terminal" in System Settings
- **User control:** Enable/disable in System Settings
- **Reliable:** No permission issues like osascript

---

## For Demo Day

**Before meeting:**

```bash
# Verify everything works
./verify_notifications.sh

# Enable in System Settings
# System Settings → Notifications → Terminal → On
```

**During meeting:**

```bash
# Start progress watcher in separate terminal
python3 bobby/progress_watcher.py
```

**Result:**

- Kevin & Michelle see notifications pop up
- Hear sound when Bobby asks questions
- Visual + audio feedback of Bobby's work!

---

**Quick help:** Run `./verify_notifications.sh` to check everything!
