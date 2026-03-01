# How to Launch Bobby

You have **two options** for running Bobby:

---

## Option 1: Python Launcher (Recommended for Simplicity)

**Single window with colored, labeled output**

```bash
./start_bob.py
```

**Pros:**
- ✅ Single terminal window
- ✅ Color-coded output by component
- ✅ Easy to scroll and copy-paste (normal terminal)
- ✅ Simple to stop (just Ctrl+C)

**Cons:**
- ❌ All output mixed together (can be busy)
- ❌ Can't interact with individual components separately

**Output looks like:**
```
[14:23:15] [AUDIO] 🎤 Audio Capture Starting...
[14:23:16] [ORCH ] 🤖 Orchestrator Starting...
[14:23:16] [WATCH] 👀 Progress Watcher Starting...
[14:23:20] [AUDIO] [14:23:20] Hey, Bobby, please build this.
[14:23:21] [ORCH ] TRIGGER DETECTED: 'Hey Bobby, please build this'
[14:23:22] [WATCH] 🔍 → Examining landing page structure...
```

**To stop:** Just press `Ctrl+C`

---

## Option 2: tmux (Better for Monitoring)

**Split panes showing each component separately**

```bash
./start_bob.sh
```

**Pros:**
- ✅ See all 3 components at once (split screen)
- ✅ Can interact with each separately
- ✅ Can detach and reattach later
- ✅ Professional multi-pane setup

**Cons:**
- ❌ Learning curve for tmux navigation
- ❌ Scrolling/copy-paste is different

**Layout:**
```
┌─────────────────┬─────────────────┐
│ Audio Capture   │ Orchestrator    │
├─────────────────┴─────────────────┤
│ Progress Watcher                  │
└───────────────────────────────────┘
```

**Navigation:**
- Switch panes: `Ctrl+b` then arrow keys
- Scroll up: `Ctrl+b` then `[`, then use arrow keys, press `q` to exit
- Stop: `Ctrl+c` in each pane, or run `./stop_bob.sh`

**See [TMUX_GUIDE.md](TMUX_GUIDE.md) for complete tmux instructions**

---

## Which Should You Use?

| If you want... | Use this |
|----------------|----------|
| **Simple, easy scrolling** | Python launcher (`./start_bob.py`) |
| **See everything at once** | tmux (`./start_bob.sh`) |
| **Quick testing** | Python launcher |
| **Professional monitoring** | tmux |

**My recommendation:** Start with **Python launcher** until you're comfortable, then try tmux later.

---

## Common Tasks

### Start Bobby
```bash
# Python (simple)
./start_bob.py

# tmux (multi-pane)
./start_bob.sh
```

### Stop Bobby
```bash
# Python: Just press Ctrl+C

# tmux: Run this from another terminal
./stop_bob.sh

# Or press Ctrl+c in each tmux pane
```

### View Transcript
```bash
tail -f test-workspace/meeting_transcript.txt
```

### View Progress
```bash
tail -f test-workspace/agent_progress.txt
```

---

## Troubleshooting

**"Nothing is being transcribed"**
- Check audio input in System Settings → Sound → Input
- Make sure `USE_DEFAULT_MIC = True` in audio_capture.py (for testing)
- Speak clearly into your microphone

**"Duplicate transcripts"**
- ✅ Fixed! Update pulled latest changes

**"Can't change audio input while running"**
- Audio devices are locked at startup
- Stop Bobby, change input, restart Bobby

**"Permission denied"**
```bash
chmod +x start_bob.py start_bob.sh stop_bob.sh
```
