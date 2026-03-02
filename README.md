# Bobby

AI meeting assistant that executes code tasks in real-time. Say "Hey Bobby, please build this" during a meeting and Bobby launches a Claude Code agent to build the feature while the conversation continues.

Bobby can run in two modes: **local mode** (mic capture + terminal UI) or **Discord mode** (joins a voice channel as a bot participant).

## Features

- **Real-time code execution** — Bobby listens to the meeting, detects trigger phrases, and launches a Claude Code agent that builds features while the conversation continues
- **Voice in, voice out** — Speaks with an Eastern European accent (ElevenLabs TTS) to acknowledge triggers, ask clarifying questions, and announce completions
- **Question/answer loop** — If the agent needs clarification, it asks via voice and text. Answer naturally and say "Thank you, Bobby" to resume
- **Per-speaker transcription** — In Discord mode, each participant gets their own Assembly AI session with speaker labels, so Bobby knows who said what
- **Live progress tracking** — Discord embeds update in real-time as the agent works, with a detail thread for the full log
- **Auto-join/leave** — Bobby joins the voice channel when someone enters and leaves when everyone departs

## How It Works

1. Audio streams to Assembly AI for real-time transcription (mic in local mode, Discord voice in Discord mode)
2. Trigger detection watches the transcript for "Hey Bobby, please build this"
3. A Claude Code agent launches with meeting context and builds the requested feature
4. Bobby speaks acknowledgments and completions via ElevenLabs TTS (or macOS `say` fallback)
5. If the agent needs clarification, it asks a question — answer in voice and say "Thank you, Bobby" to resume

## Discord Mode (primary)

Bobby joins a Discord voice channel, listens to the conversation, and posts progress as embeds in a text channel.

```bash
# Prerequisites: Python 3.12+, uv, ffmpeg, opus
brew install ffmpeg opus

# Install dependencies with Discord extras
uv sync --extra discord

# Configure API keys + Discord bot settings
cp .env.example .env
# Edit .env: ASSEMBLYAI_API_KEY, ELEVENLABS_API_KEY,
# DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, DISCORD_CHANNEL_ID,
# DISCORD_VOICE_CHANNEL_ID (optional, enables auto-join)

# Launch
uv run python start_discord.py
```

With `DISCORD_VOICE_CHANNEL_ID` set, Bobby auto-joins when someone enters the channel and auto-leaves when everyone departs. Otherwise, use `/bobby join` and `/bobby leave`.

## Local Mode

Captures audio from your mic (or BlackHole virtual audio device), displays progress in a Rich terminal UI with macOS notifications.

```bash
# Prerequisites: Python 3.12+, uv, tmux, portaudio
brew install portaudio terminal-notifier tmux

# Install dependencies
uv sync

# Configure API keys
cp .env.example .env
# Edit .env: ASSEMBLYAI_API_KEY, ELEVENLABS_API_KEY

# Launch (3 components in tmux panes)
./start_bobby.sh

# Or: voice test mode (no agent execution)
./start_bobby.sh --test-voice
```

## Project Structure

```
bobby/              Python package
  prompts.py        Bobby's personality, voice lines, and agent prompt template
  discord_bot.py    Discord mode — slash commands, voice, progress embeds
  discord_sink.py   Discord audio → Assembly AI (per-speaker transcription)
  agent_runner.py   Shared agent logic (trigger detection, launch, resume)
  orchestrator.py   Local mode — transcript watcher + agent management
  audio_capture.py  Local mode — mic → Assembly AI
  tts.py            ElevenLabs TTS with macOS say fallback
  config.py         Centralized paths and env vars
sandbox/            Test workspace (React/Vite app for Bobby to modify)
tests/              Test and demo scripts
start_discord.py    Discord mode launcher
start_bobby.sh      Local mode tmux launcher
start_bobby.py      Local mode single-terminal launcher
```

## Configuration

Bobby operates on a target workspace (defaults to `./sandbox`). To point it at a different project:

```bash
BOBBY_WORKSPACE=~/Projects/my-app ./start_bobby.sh
```

See [CLAUDE.md](CLAUDE.md) for full architecture details and conventions.
