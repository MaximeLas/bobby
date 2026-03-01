# Bobby - Installation Guide

Quick setup guide for Bobby's components.

## Prerequisites

- macOS (tested on macOS 14+)
- Python 3.8+ (tested with Python 3.13.3)
- pip3

## Option 1: Virtual Environment (Recommended)

This is the cleanest approach and won't conflict with system Python.

```bash
# Navigate to project directory
cd /Users/maximelas/Projects/Unicorn

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run components (while venv is active)
python bobby/progress_watcher.py
```

To deactivate later:

```bash
deactivate
```

## Option 2: System-Wide Install (Not Recommended)

If you prefer system-wide installation:

```bash
# Install with --break-system-packages flag (use with caution)
pip3 install --break-system-packages rich

# Or use Homebrew if available
brew install python-rich
```

## Option 3: No Installation (Basic Fallback)

The progress watcher works without `rich`, it just uses basic formatting:

```bash
# No installation needed - just run it
python3 bobby/progress_watcher.py

# You'll see a warning but it will still work
```

## Testing Installation

Run the verification script:

```bash
./verify_progress_watcher.sh
```

Or test manually:

```bash
# Terminal 1: Start progress watcher
python3 bobby/progress_watcher.py

# Terminal 2: Run test script
python3 bobby/test_progress_watcher.py
```

## Dependencies by Component

### Component 4: Progress Watcher (Ready Now)

- **Required:** Python 3.8+, osascript (macOS built-in)
- **Optional:** rich>=13.0.0 (for beautiful colors)
- **Status:** ✅ Working (tested)

### Component 2: Orchestrator (Already Built)

- **Required:** Python 3.8+
- **Optional:** None
- **Status:** ✅ Working (tested)

### Component 1: Audio Capture (Not Yet Built)

- **Required:** pyaudio>=0.2.13, assemblyai>=0.17.0, BlackHole
- **Status:** ⏳ To be built

### Component 4 (Future): TTS

- **Required:** elevenlabs>=0.2.0 OR openai>=1.0.0
- **Status:** ⏳ To be implemented

## Troubleshooting

### "externally-managed-environment" Error

This is normal on macOS with Homebrew Python. Use Option 1 (virtual environment).

### Notifications Not Appearing

- Check System Preferences → Notifications → Script Editor
- Make sure notifications are enabled
- Test with: `osascript -e 'display notification "test" with title "test"'`

### "rich" Import Error

This is expected if you haven't installed rich. The watcher will use fallback mode with basic formatting.

### Progress Watcher Not Showing Updates

- Make sure `agent_progress.txt` exists in the current directory
- Try running from project root: `cd /Users/maximelas/Projects/Unicorn`
- Check that you're writing updates in the correct format (see README.md)

## Next Steps

After installation, see:

- `bobby/README.md` - Usage instructions
- `ARCHITECTURE.md` - System design
- `PROGRESS.md` - Build status

## Questions?

Check the main CLAUDE.md file or the architecture docs.
