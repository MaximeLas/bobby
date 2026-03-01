# Progress Watcher - Quick Start Guide

Component 4 of Bobby - Watch agent progress in real-time with beautiful terminal UI + macOS notifications.

## Instant Test (30 seconds)

```bash
# Terminal 1: Start the watcher
python3 bobby/progress_watcher.py

# Terminal 2: Run automated test
python3 bobby/test_progress_watcher.py
# Choose option 1 (Success scenario)
```

You'll see:

- Colored terminal output with emojis
- macOS notifications popping up
- Progress, questions, and completion messages

## What It Does

Watches `agent_progress.txt` and displays updates TWO ways:

1. **Rich Terminal UI**

   - Color-coded by type (blue/cyan/yellow/green/red)
   - Emojis for visual clarity (🔍 ✅ ❓ ❌)
   - Timestamps for each update
   - Real-time updates (0.5s polling)

2. **macOS Notifications**
   - EVERY update triggers a notification
   - Different titles for each type
   - Non-intrusive but visible

## Update Types

```
PROGRESS: → Doing something...      (cyan with 🔍)
PROGRESS:   ✓ Completed step        (green with ✅)
QUESTION: Your question here?       (yellow with ❓)
COMPLETE: Task finished!            (green with ✅)
ERROR: Something failed             (red with ❌)
```

## Manual Testing

```bash
# Terminal 1: Start watcher
python3 bobby/progress_watcher.py

# Terminal 2: Add updates manually
echo "PROGRESS: → Reading code..." >> agent_progress.txt
echo "PROGRESS:   ✓ Found the file" >> agent_progress.txt
echo "QUESTION: Should I use React?" >> agent_progress.txt
echo "COMPLETE: Feature deployed!" >> agent_progress.txt
```

## Demo Mode

Watch a complete simulated task:

```bash
./demo_progress_watcher.sh
```

This runs a full scenario showing all update types.

## Verification

Check everything works:

```bash
./verify_progress_watcher.sh
```

## Files Created

| File                             | Purpose                         |
| -------------------------------- | ------------------------------- |
| `bobby/progress_watcher.py`      | Main watcher (8.5KB, 315 lines) |
| `bobby/test_progress_watcher.py` | Interactive test script (4.9KB) |
| `verify_progress_watcher.sh`     | Verification script             |
| `demo_progress_watcher.sh`       | Automated demo                  |
| `requirements.txt`               | Python dependencies             |
| `INSTALLATION.md`                | Setup guide                     |

## Requirements

**Required:**

- Python 3.8+
- macOS (for notifications)
- `terminal-notifier` (for proper macOS notifications)

**Optional:**

- `rich` library (for beautiful colors - has fallback without it)

**Install terminal-notifier:**

```bash
brew install terminal-notifier
# Or run the setup script:
./bobby/setup_notifications.sh
```

## Installation

**Option 1: No installation needed** (basic mode)

```bash
python3 bobby/progress_watcher.py
# Works immediately, basic formatting
```

**Option 2: Install rich for beautiful colors**

```bash
python3 -m venv venv
source venv/bin/activate
pip install rich
python bobby/progress_watcher.py
```

See `INSTALLATION.md` for more options.

## Integration

The progress watcher integrates with:

**Component 3 (Agent):**

- Agent writes to `agent_progress.txt`
- Watcher reads and displays updates
- Works automatically - no configuration needed

**Future TTS:**

- When voice is added, watcher will also speak updates
- For now: visual terminal + notifications only

## Stopping

Press `Ctrl+C` - the watcher handles shutdown gracefully.

## Troubleshooting

**No updates appearing:**

- Check `agent_progress.txt` exists
- Verify you're in the right directory
- Make sure updates use correct format (PROGRESS:, QUESTION:, etc.)

**No notifications:**

- Check System Settings → Notifications → Terminal
- Make sure notifications are enabled with "Banners" style
- Disable Focus/Do Not Disturb mode
- Run the test: `python3 test_terminal_notifier.py`
- Install terminal-notifier if missing: `brew install terminal-notifier`

**Import error:**

- If `rich` not installed, watcher uses fallback mode
- Everything still works, just simpler formatting

## Next Steps

1. Run the watcher: `python3 bobby/progress_watcher.py`
2. Test it: `python3 bobby/test_progress_watcher.py`
3. Integrate with orchestrator (Component 2)
4. Run full Bobby system (orchestrator + watcher + agent)

## Documentation

- `bobby/README.md` - Component details
- `ARCHITECTURE.md` - System design
- `PROGRESS.md` - Build status
- `INSTALLATION.md` - Setup guide

---

**Quick Summary:** Run `python3 bobby/progress_watcher.py` in one terminal, then `python3 bobby/test_progress_watcher.py` in another. Choose option 1. Watch the magic happen!
