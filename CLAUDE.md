# Bobby - AI Meeting Assistant

## What Bobby Is

Bobby is an AI assistant that joins product meetings and executes code tasks in real-time. During a meeting, say "Hey Bobby, please build this" and Bobby detects the trigger from the live transcript, launches a Claude Code agent to build the feature, and announces completion via text-to-speech — all while the meeting continues.

The novel part: not just transcription or note-taking, but actual code execution during live meetings.

## Current State

**Two operating modes:**
- **Discord mode** (primary) — Bobby joins a Discord voice channel as a bot participant. Per-speaker transcription, progress embeds in text channels, voice output into the call. Full question/answer/resume loop.
- **Local mode** — Captures audio from mic (or BlackHole virtual audio device). Rich terminal UI with macOS notifications. Useful for testing without Discord.

**What works in both modes:**
- Real-time transcription via Assembly AI streaming v3
- Trigger detection ("Hey Bobby, please build this") with debounce
- Claude Code agent launch with meeting context
- Resume trigger ("Thank you, Bobby") to answer agent questions
- Conversational brain: "Hey Bobby, \<anything else\>" gets a spoken, transcript-grounded answer (`bobby/brain.py` — Anthropic API fast path when `ANTHROPIC_API_KEY` is set, `claude` CLI fallback)
- Proactive suggestions (opt-in, `BOBBY_PROACTIVE=1`): Bobby offers to build features he hears discussed (`bobby/suggestions.py`)
- Text-to-speech via ElevenLabs (Eastern European Borat-style voice) with macOS `say` fallback
- Full voice loop: acknowledgements, questions, completions, and errors are spoken in both modes (local mode speaks via `bobby/voice.py`; progress watcher takes `--no-voice` to disable)

**Discord-specific features:**
- Per-speaker audio routing (each user gets their own Assembly AI session)
- Auto-join/leave voice channel via `DISCORD_VOICE_CHANNEL_ID`
- Progress embeds with dynamic task names, bold question labels, thread detail logs
- Voice output into Discord (ElevenLabs → FFmpegPCMAudio)
- Converse works mid-build ("Hey Bobby, how is it going?" reads agent progress); in local mode the orchestrator blocks during builds, so converse only answers while idle

**What's not done:**
- BlackHole aggregate device for capturing Zoom/Meet audio in local mode
- Multi-meeting support (parallel projects in different channels)

## Architecture

### Discord Mode

Single process. Pycord asyncio event loop + background threads for Assembly AI and agent subprocess.

```
Discord Voice Channel
       |
  [discord_bot.py]  ──→  [discord_sink.py]  ──→  Assembly AI (per-user)
       |                                              |
       |                                    meeting_transcript.txt
       |                                              |
       |                                    [trigger detection]
       |                                      (agent_runner.py)
       |                                              |
       |                                    Claude Code Agent
       |                                              |
       |                                    agent_progress.txt
       |                                              |
  [discord_bot.py]  ←── reads progress ←──────────────┘
       |
  Text channel: embeds + threads
  Voice channel: ElevenLabs TTS playback
```

### Local Mode

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
                                          + spoken questions/completions
```

Both local components speak through `bobby/voice.py`, which coordinates
with audio capture (pause flag + self-speech filtering) so Bobby doesn't
transcribe his own voice.

### Key Design Decisions

- **File-based IPC** — `meeting_transcript.txt` and `agent_progress.txt` are the interface between components. Both modes produce/consume these files. This keeps the modes decoupled and makes debugging easy (just read the file).
- **Per-user Assembly AI sessions** — In Discord mode, each speaking user gets their own AAI streaming session via `discord_sink.py`. This gives speaker-labeled transcripts (`[Max] said X`) so the agent understands who wants what. Dead sessions are auto-cleaned from the dict so the next audio chunk creates a fresh one.
- **Threading model** — Pycord runs on asyncio. Assembly AI's `client.stream()` is blocking, so it runs in background threads (one per user). Agent subprocess runs via `asyncio.to_thread()`. File reads for polling are fast enough for the event loop.

## Key Conventions

### Workspace configuration

All file paths are centralized in `bobby/config.py`. Bobby defaults to operating on `./sandbox` but can target any workspace:

```bash
BOBBY_WORKSPACE=~/Projects/my-app ./start_bobby.sh
```

When the target workspace's dev server isn't Vite on 5173, set the URL the agent deploys to and reports (e.g. Next.js on 3000):

```bash
BOBBY_WORKSPACE=~/Projects/publico-demo BOBBY_DEV_URL=http://localhost:3000 uv run python start_discord.py
```

All modules import paths from config rather than hardcoding them.

### Running Bobby

```bash
# --- Discord Mode ---
uv sync --extra discord
cp .env.example .env
# Edit .env: ASSEMBLYAI_API_KEY, ELEVENLABS_API_KEY, DISCORD_BOT_TOKEN,
# DISCORD_GUILD_ID, DISCORD_CHANNEL_ID, DISCORD_VOICE_CHANNEL_ID
uv run python start_discord.py

# --- Local Mode ---
uv sync
./start_bobby.sh
# Or: ./start_bobby.sh --test-voice (no agent execution)
```

Discord mode requires: `brew install ffmpeg opus`

### Triggers

- **"Hey Bobby, please build this"** — Launches a new Claude Code agent with recent meeting context
- **"Thank you, Bobby"** — Resumes an agent that asked a question
- **"Hey Bobby, \<anything else\>"** — Spoken, transcript-grounded answer from the brain (`bobby/brain.py`). Precedence: the launch phrase contains "hey bobby", so launch/resume are checked first.
- **No trigger needed** (opt-in): with `BOBBY_PROACTIVE=1`, Bobby offers to build concrete, small features he hears discussed (`bobby/suggestions.py` — heavily debounced, one offer per 5 min, never mid-build)

### Agent protocol

The agent writes progress to `agent_progress.txt`:

```
TASK: Short description of what's being built
PROGRESS: → Starting task
PROGRESS:   ✓ Completed step
QUESTION: Your question here
COMPLETE: Summary at http://localhost:5173
```

TASK: is the agent's first write — it updates the embed title and thread name in Discord mode. The prompt template lives in `bobby/prompts.py`.

## Commit Messages

Look at `git log` to match the style of existing commits. The key principle: write for someone reading the log in 3 months who needs to understand what changed and why.

**Include:** features, architectural decisions, new/changed files with what they do, what was tested.

**Omit:** implementation micro-fixes (logger levels, timeout tweaks, arrow character changes), anything that's just "how" rather than "what" or "why". If a detail only matters while actively debugging that code, it belongs in a code comment, not the commit message.

The right granularity depends on the change. A single-purpose bug fix needs one sentence. A multi-faceted phase like this project's Discord integration needs structured sections (summary, new files, changes, tested). But even in long messages, each file's entry should capture the intent — not enumerate every fix.

## For Agents Working on This Codebase

- All file paths come from `bobby/config.py` — never hardcode workspace paths (nor dev-server URLs: use `config.DEV_SERVER_URL`)
- `bobby/prompts.py` is the single source of truth for Bobby's personality (Borat-style Eastern European accent), all voice lines, and every prompt template (agent, brain, proactive). Don't hardcode voice strings elsewhere.
- All local-mode speech goes through `bobby/voice.py` (`speak_in_meeting`) — it owns the pause-flag/self-speech coordination with audio capture. Discord mode speaks via `discord_bot._speak_in_voice` instead (no mic feedback there).
- Bobby's voice uses ElevenLabs with voice ID `lIaJUjvN2nyLPU9wRIa0` (requires paid plan; macOS `say` is the fallback)
- Audio capture in local mode defaults to `USE_DEFAULT_MIC = True` in `audio_capture.py` — set to `False` for BlackHole/production
- TTS uses `subprocess.run()` for audio playback — never use `os.system()` (shell injection risk)
- The orchestrator and transcript watcher start reading from the END of the transcript file to avoid replaying old triggers
- **Critical async pattern:** Question voice in Discord mode MUST fire as `asyncio.create_task()` (not `await`) in monitor_progress, otherwise it blocks the embed update loop for 30s during TTS playback and the agent exits before the embed shows the question
- **Plan files** are stored in `~/.claude/plans/`, NOT in the project's `.claude/plans/` directory
