# Bobby

AI meeting assistant that executes code tasks in real-time. Say "Hey Bobby, please build this" during a meeting and Bobby launches a Claude Code agent to build the feature while the conversation continues.

## How It Works

1. **Audio Capture** streams meeting audio to Assembly AI for real-time transcription
2. **Orchestrator** watches the transcript for trigger phrases and launches Claude Code agents
3. **Progress Watcher** displays agent progress in a Rich terminal UI with macOS notifications
4. **TTS** makes Bobby speak acknowledgments and completions via ElevenLabs

## Quick Start

```bash
# Prerequisites: Python 3.12+, uv, tmux, portaudio
brew install portaudio terminal-notifier tmux

# Install dependencies
uv sync

# Configure API keys
cp .env.example .env
# Edit .env with your ASSEMBLYAI_API_KEY and ELEVENLABS_API_KEY

# Launch Bobby (3 components in tmux panes)
./start_bobby.sh

# Or: voice test mode (no agent execution)
./start_bobby.sh --test-voice
```

## Project Structure

```
bobby/              Python package (audio capture, orchestrator, progress watcher, TTS)
sandbox/            Test workspace (FlowTask React/Vite app for Bobby to modify)
tests/              Test and demo scripts
docs/               Documentation and build history
start_bobby.sh      tmux launcher
start_bobby.py      Single-terminal launcher with colored output
```

## Configuration

Bobby operates on a target workspace (defaults to `./sandbox`). To point it at a different project:

```bash
BOBBY_WORKSPACE=~/Projects/my-app ./start_bobby.sh
```

See [CLAUDE.md](CLAUDE.md) for full architecture details and conventions.
