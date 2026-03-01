# Bobby - AI Meeting Assistant

## What Bobby Is

Bobby is an AI assistant that joins product meetings and executes code tasks in real-time. During a meeting, say "Hey Bobby, please build this" and Bobby detects the trigger from the live transcript, launches a Claude Code agent to build the feature, and announces completion via text-to-speech — all while the meeting continues.

The novel part: not just transcription or note-taking, but actual code execution during live meetings.

## Current State

**What works:**
- Real-time audio capture via microphone or BlackHole virtual audio device
- Live transcription via Assembly AI streaming v3
- Trigger detection ("Hey Bobby, please build this") with 30s debounce
- Claude Code agent launch with meeting context
- Agent progress monitoring with Rich terminal UI + macOS notifications
- Text-to-speech via ElevenLabs (Eastern European accent voice)
- Transcription auto-pauses while Bobby speaks (prevents self-capture)
- tmux-based multi-pane launcher

**What's not done:**
- BlackHole aggregate device for capturing Zoom/Meet audio (currently uses default mic)
- Discord integration (Bobby as a real meeting participant)
- Progress updates in chat (currently uses macOS notifications)

## Architecture

Four components run as parallel processes, communicating through files:

```
Microphone/BlackHole
       |
  [Audio Capture]  -->  meeting_transcript.txt
                               |
                        [Orchestrator]  -->  Claude Code Agent
                               |                    |
                        (trigger detected)    agent_progress.txt
                               |                    |
                        [TTS / Voice]     [Progress Watcher]
                        Bobby speaks      Rich UI + notifications
```

| Component | Module | Purpose |
|-----------|--------|---------|
| Audio Capture | `bobby.audio_capture` | Streams mic audio to Assembly AI, writes transcript |
| Orchestrator | `bobby.orchestrator` | Watches transcript for triggers, launches/resumes agents |
| Progress Watcher | `bobby.progress_watcher` | Watches agent output, displays Rich UI + notifications |
| TTS | `bobby.tts` | ElevenLabs text-to-speech with macOS fallback |

## Project Structure

```
bobby/
├── bobby/                  # Python package
│   ├── config.py           # Centralized paths (BOBBY_WORKSPACE env var)
│   ├── audio_capture.py    # Component 1: mic → Assembly AI → transcript
│   ├── orchestrator.py     # Component 2: trigger detection, agent management
│   ├── progress_watcher.py # Component 3: Rich UI + macOS notifications
│   └── tts.py              # Component 4: ElevenLabs TTS
├── sandbox/                # Test workspace (FlowTask React/Vite landing page)
├── tests/                  # Test and demo scripts
├── docs/                   # Documentation + archive of build history
├── start_bobby.sh          # tmux launcher (3 panes)
├── start_bobby.py          # Python launcher (single terminal, colored output)
├── stop_bobby.sh           # Kill tmux session
├── pyproject.toml          # Dependencies (managed with uv)
└── .env                    # API keys (gitignored)
```

## Key Conventions

### Workspace configuration

All file paths are centralized in `bobby/config.py`. Bobby defaults to operating on `./sandbox` but can target any workspace:

```bash
# Default: operates on the sandbox test app
./start_bobby.sh

# Point at a different project
BOBBY_WORKSPACE=~/Projects/my-app ./start_bobby.sh
```

The config exports: `WORKSPACE_DIR`, `TRANSCRIPT_FILE`, `PROGRESS_FILE`, `PAUSE_FLAG_FILE`, `BOBBY_SPEECH_FILE`. All modules import paths from config rather than hardcoding them.

### Running Bobby

```bash
# Install dependencies
uv sync

# Set up API keys
cp .env.example .env
# Edit .env with your ASSEMBLYAI_API_KEY and ELEVENLABS_API_KEY

# Launch all components in tmux
./start_bobby.sh

# Or launch in a single terminal with colored output
uv run python start_bobby.py

# Voice test mode (no agent execution, saves API credits)
./start_bobby.sh --test-voice
```

### Triggers

- **"Hey Bobby, please build this"** — Launches a new Claude Code agent with recent meeting context
- **"Thank you, Bobby"** — Resumes an agent that asked a question

### Agent communication

The orchestrator launches `claude -p --dangerously-skip-permissions` with a system prompt that instructs the agent to write progress to `agent_progress.txt` in this format:

```
PROGRESS: -> Starting task
PROGRESS:   ✓ Completed step
QUESTION: Your question here
COMPLETE: Summary at http://localhost:5173
```

The progress watcher reads this file and displays updates in real-time.

## Dependencies

- `assemblyai` — Real-time speech-to-text streaming
- `pyaudio` — Audio device access (requires PortAudio: `brew install portaudio`)
- `elevenlabs` — Text-to-speech API
- `rich` — Terminal UI for progress watcher
- `python-dotenv` — Environment variable loading

External tools:
- `claude` CLI — Claude Code for agent execution
- `terminal-notifier` — macOS notifications (`brew install terminal-notifier`)
- `tmux` — Multi-pane terminal management
- BlackHole — Virtual audio device for capturing meeting audio (`brew install blackhole-2ch`)

Discord mode additionally requires:
- `ffmpeg` — Audio encoding/decoding for Pycord voice (`brew install ffmpeg`)
- `opus` — Audio codec for Discord voice receive (`brew install opus`)
- Install Python deps: `uv sync --extra discord`

## Roadmap

The current setup is a local testing rig (mic → transcript → agent → notifications). The next phase is making Bobby a real meeting participant:

1. **Discord integration** — Bobby joins voice channels, captures audio, sends progress updates in chat
2. **Multi-meeting support** — Bobby can operate on different projects in parallel
3. **Proactive suggestions** — Bobby offers to build things mentioned in discussion without explicit triggers

## For Agents Working on This Codebase

- All file paths come from `bobby/config.py` — never hardcode workspace paths
- Bobby's voice uses ElevenLabs with voice ID `lIaJUjvN2nyLPU9wRIa0` (Eastern European accent)
- Audio capture currently defaults to `USE_DEFAULT_MIC = True` in `audio_capture.py` — set to `False` for BlackHole/production
- The orchestrator starts reading from the END of the transcript file to avoid replaying old triggers
- TTS uses `subprocess.run()` for audio playback — never use `os.system()` (shell injection risk)
- **Plan files** are stored in `~/.claude/plans/`, NOT in the project's `.claude/plans/` directory. After compaction, if a plan file reference appears missing from the project directory, check `~/.claude/plans/` — that's where Claude Code stores them
