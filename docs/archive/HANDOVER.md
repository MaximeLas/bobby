# Handover Notes - End of Session (Oct 27, 2025)

> **Note:** Historical handover from Oct 2025, written before the project was restructured into its own repo. Some paths reference the old `~/Projects/Unicorn/test-workspace/` layout. See `CLAUDE.md` in the project root for current state.

## What Works Right Now ✅

### Core System (Functional!)
- **Audio Capture**: `test-workspace/bobby/audio_capture.py` - captures mic → Assembly AI → transcript
  - Currently using **default microphone** (USE_DEFAULT_MIC=True)
  - Pauses transcription when Bobby speaks

- **Orchestrator**: `bobby/orchestrator.py` - watches transcript, launches agents
  - Detects trigger: **"Hey Bobby, please build this"**
  - Voice acknowledgment: Says "On it, building now" immediately
  - Launches Claude Code agents with meeting context

- **Progress Watcher**: `bobby/progress_watcher.py` - displays agent progress
  - Rich terminal UI with colors
  - macOS notifications for updates

- **Scripts**: Start/stop everything easily
  - `./start_bobby.sh` - launches all 3 components in tmux
  - `./stop_bobby.sh` - kills the session

### Test Environment
- `test-workspace/` - FlowTask landing page (Vite + React)
- Has working examples of Bobby building features from conversation

---

## What's NOT Done Yet ❌

### Audio Setup
- **BlackHole not configured** - currently using default mic
- **Aggregate Device not created** - needed for Zoom meetings (mic + BlackHole)
- **Multi-Output Device** - optional for hearing system audio while capturing

### TTS (Voice)
- Using macOS `say` command (temp solution)
- **ElevenLabs not integrated** - would sound much better

### Project Organization
- **18 markdown files** (many outdated/duplicate)
- Files split between root and test-workspace
- Two venvs (root + test-workspace)
- Old test files, recordings lying around

---

## Critical Issues to Address

### 1. **Project Cleanup (URGENT)**
The repo is a mess. Needs:
- Consolidate/delete redundant markdown files
- Move files to consistent locations
- Single venv (or document why two are needed)
- Remove old recordings, test files
- Update outdated docs

### 2. **Audio Routing for Production**
Current setup only works for **testing alone** (your mic).

For **Zoom meetings**, need:
1. Create **Aggregate Device** (Audio MIDI Setup)
   - MacBook Air Microphone (your voice)
   - BlackHole 2ch (Zoom audio)
2. Set Zoom output to BlackHole
3. Set `USE_DEFAULT_MIC = False` in audio_capture.py

See: [AUDIO_ROUTING_GUIDE.md](AUDIO_ROUTING_GUIDE.md)

### 3. **ElevenLabs TTS**
Replace macOS `say` with ElevenLabs for natural voice.
Placeholder code already in `bobby/tts.py`

---

## File Organization Suggestions

### Keep (Important):
- `CLAUDE.md` - Project instructions
- `ARCHITECTURE.md` - System design
- `PROGRESS.md` - Build status (needs update)
- `AUDIO_ROUTING_GUIDE.md` - Audio setup guide
- `TMUX_GUIDE.md` - How to use tmux

### Delete or Consolidate:
- `COMPONENT4_DELIVERY.md` - outdated
- `DELIVERY_NOTIFICATION_FIX.md` - outdated
- `IMPLEMENTATION_SUMMARY.md` - redundant
- `ORCHESTRATOR_GUIDE.md` - merge into ARCHITECTURE
- `QUICKSTART.md` - redundant with CLAUDE.md
- `QUICKSTART_PROGRESS_WATCHER.md` - outdated
- `NOTIFICATION_UPGRADE.md` - outdated
- `NOTIFICATIONS_QUICK_REF.md` - outdated
- `INSTALLATION.md` - outdated
- `LAUNCH_OPTIONS.md` - redundant
- `TRANSCRIPTION_README.md` - outdated
- `next-steps.md` - outdated
- `Oct 25.md` - session notes (archive or delete)

### Organize:
```
/Users/maximelas/Projects/Unicorn/
├── CLAUDE.md              (keep)
├── ARCHITECTURE.md        (keep, update)
├── PROGRESS.md            (keep, update)
├── AUDIO_ROUTING_GUIDE.md (keep)
├── TMUX_GUIDE.md          (keep)
├── bobby/                 (all Python scripts)
├── test-workspace/        (test environment)
└── docs/                  (NEW - archive old docs here)
```

---

## Recommended Next Steps (Priority Order)

### 1️⃣ **Project Cleanup** (1-2 hours)
Clean up this mess so it's maintainable:
- Delete/consolidate markdown files
- Organize code into proper locations
- Clean up venv situation
- Remove old test files

### 2️⃣ **Update Documentation** (30 min)
Update PROGRESS.md to reflect current state:
- Audio capture ✅ (with default mic)
- Orchestrator ✅
- Voice acknowledgment ✅
- Still TODO: BlackHole setup, ElevenLabs, cleanup

### 3️⃣ **Finalize Audio Setup** (1-2 hours)
Set up aggregate device for Zoom meetings:
- Create aggregate device in Audio MIDI Setup
- Test with Zoom
- Update audio_capture.py to use it

### 4️⃣ **Integrate ElevenLabs TTS** (1 hour)
Replace macOS say with proper TTS:
- Get ElevenLabs API key
- Update `bobby/tts.py`
- Test voice quality

### 5️⃣ **End-to-End Testing** (1 hour)
Full flow with real meeting simulation

### 6️⃣ **Demo Prep** (1 hour)
Prepare for Kevin & Michelle demo

---

## Quick Start (for next agent)

```bash
# Start Bobby
./start_bobby.sh

# Say into your mic:
"Hey Bobby, please build this. Add a contact form to the homepage."

# Bobby will:
1. Say "On it, building now"
2. Launch agent
3. Build the feature
4. Report completion
```

**Current trigger:** "Hey Bobby, please build this"
**Answer trigger:** "Thank you, Bobby"

---

## Important Notes

- **Assembly AI API key** in environment variable (working)
- **Renamed Bob → Bobby** throughout (better speech recognition)
- **Orchestrator starts from END of file** (doesn't process old triggers)
- **Transcription pauses when Bobby speaks** (pause_transcription.flag)
- **tmux session name:** `bobby` (not `bob`)

---

## Questions to Clarify with Max

1. Keep test-workspace as-is, or move it somewhere else?
2. Single venv or keep two separate?
3. Which markdown files are still useful?
4. Priority: cleanup first or audio setup first?

---

**Status:** Bobby works for solo testing with mic. Needs cleanup + Zoom audio setup for production use.

**Last session:** Oct 27, 2025 - Fixed transcription, added voice, renamed to Bobby
