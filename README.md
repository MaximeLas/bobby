# Bobby

AI meeting assistant that executes code tasks in real-time. Say "Hey Bobby, please build this" during a meeting and Bobby launches a Claude Code agent to build the feature while the conversation continues.

Bobby can run in two participant modes — **local mode** (mic capture + terminal UI) and **Discord mode** (joins a voice channel as a bot participant) — plus a silent **sidecar mode** (`BOBBY_SIDECAR=1`): live diarized transcription only, with speaker labels, sub-2s partial updates, and an event log, for meetings where Bobby assists one person privately instead of joining the room. The full map of what these modes are (and aren't) lives in [docs/modes.md](docs/modes.md).

## Features

- **Real-time code execution** — Bobby listens to the meeting, detects trigger phrases, and launches a Claude Code agent that builds features while the conversation continues
- **Conversational** — "Hey Bobby, \<anything else\>" gets a short spoken answer grounded in the meeting transcript (and in build progress, mid-build in Discord mode)
- **Voice in, voice out** — Speaks with an Eastern European accent (ElevenLabs TTS) to acknowledge triggers, ask clarifying questions, and announce completions — in both modes
- **Question/answer loop** — If the agent needs clarification, it asks via voice and text. Answer naturally and say "Thank you, Bobby" to resume
- **Proactive suggestions** (opt-in, `BOBBY_PROACTIVE=1`) — Bobby offers to build concrete features he hears the team discussing, heavily rate-limited so he never spams the meeting
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
  prompts.py        Bobby's personality, voice lines, and all prompt templates
  discord_bot.py    Discord mode — slash commands, voice, progress embeds
  discord_sink.py   Discord audio → Assembly AI (per-speaker transcription)
  agent_runner.py   Shared agent logic (trigger detection, launch, resume)
  brain.py          Conversational answers (Anthropic API fast path, CLI fallback)
  suggestions.py    Proactive suggestion engine (BOBBY_PROACTIVE=1)
  orchestrator.py   Local mode — transcript watcher + agent management
  audio_capture.py  Local mode — mic → Assembly AI
  progress_watcher.py Local mode — Rich UI, notifications, spoken updates
  voice.py          Local-mode speech helper (mic coordination)
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

Optional environment variables:

- `BOBBY_DEV_URL` — dev-server URL the agent deploys to and announces (default `http://localhost:5173`; set `http://localhost:3000` for Next.js)
- `ANTHROPIC_API_KEY` — enables the fast API path for conversational answers (`uv sync --extra brain`); without it, answers go through the `claude` CLI
- `BOBBY_PROACTIVE=1` — enables proactive suggestions (off by default)
- `BOBBY_LEAN_AGENT=0` — restores full config inheritance for Bobby's agents (lean launches are on by default: agents skip the launching user's personal MCP servers/skills for faster, cheaper starts)
- `BOBBY_SPEAKER_LABELS=1` — `[A]/[B]` diarization labels in the local-mode transcript (display-only; name speakers via `BOBBY_SPEAKER_NAMES="A=Max,B=David"` or a `speaker_names.txt` in the workspace)
- `BOBBY_SIDECAR=1` — silent sidecar mode (see [docs/modes.md](docs/modes.md))
- `BOBBY_AGENT_MAX_BUDGET_USD` — hard per-run spend ceiling for agent launches

See [CLAUDE.md](CLAUDE.md) for full architecture details and conventions.

## Status & direction

Bobby is in active development. Current state, the near-term plan, and the
longer-horizon ideas (per-workspace config, end-to-end pipeline tests, a
permission bridge, post-meeting mode) are tracked in [docs/NEXT.md](docs/NEXT.md);
the conceptual map of operating modes is [docs/modes.md](docs/modes.md).
