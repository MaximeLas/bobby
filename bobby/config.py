"""
Bobby Configuration

Centralized path and environment configuration.
All file paths derive from BOBBY_WORKSPACE, which defaults to ./sandbox
but can be overridden via environment variable to target any workspace.

Usage:
    BOBBY_WORKSPACE=~/Projects/my-app python start_bobby.py
"""

import os
from pathlib import Path

# Project root (one level up from this file's directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Target workspace - the project Bobby operates on
# Defaults to the sandbox test app, but can be pointed at any workspace
WORKSPACE_DIR = Path(
    os.environ.get("BOBBY_WORKSPACE", str(PROJECT_ROOT / "sandbox"))
).resolve()

# Dev-server URL the agent is told to deploy to and report in COMPLETE: lines.
# Vite (sandbox) serves on 5173; Next.js projects like Publico use 3000 —
# override alongside BOBBY_WORKSPACE when targeting a non-Vite workspace:
#     BOBBY_WORKSPACE=~/Projects/publico-demo BOBBY_DEV_URL=http://localhost:3000 ...
DEV_SERVER_URL = os.environ.get("BOBBY_DEV_URL", "http://localhost:5173")

# Runtime state files (created in the target workspace during sessions)
TRANSCRIPT_FILE = WORKSPACE_DIR / "meeting_transcript.txt"
PROGRESS_FILE = WORKSPACE_DIR / "agent_progress.txt"
PAUSE_FLAG_FILE = WORKSPACE_DIR / "pause_transcription.flag"
BOBBY_SPEECH_FILE = WORKSPACE_DIR / "bobby_last_speech.txt"

# Proactive suggestions — Bobby listens for buildable feature ideas in the
# conversation and offers to build them without being asked. OFF by default:
# a live demo must never have Bobby butting in uninvited. Opt in per meeting:
#     BOBBY_PROACTIVE=1 uv run python start_discord.py
PROACTIVE_ENABLED = os.environ.get("BOBBY_PROACTIVE", "").strip().lower() in (
    "1", "true", "yes",
)

# Minimum seconds between two proactive offers (the strongest anti-annoyance
# gate — one suggestion per five minutes by default)
PROACTIVE_COOLDOWN_SECONDS = int(
    os.environ.get("BOBBY_PROACTIVE_COOLDOWN", "300")
)

# Lean agent launches — ON by default. A Bobby agent is a headless `claude -p`
# run that inherits whoever launched Bobby: measured 17 Aug 2026 at ~120 global
# skills and a dozen personal MCP servers, ~59k wasted cache tokens and ~5s of
# extra startup latency per launch, none of which a sandbox React edit needs.
# Lean mode drops all of it (--strict-mcp-config --setting-sources ''
# --disable-slash-commands). Rollback if a task ever does need a personal skill
# or MCP server — nothing else changes:
#     BOBBY_LEAN_AGENT=0 ./start_bobby.sh
LEAN_AGENT_ENABLED = os.environ.get("BOBBY_LEAN_AGENT", "1").strip().lower() in (
    "1", "true", "yes",
)

# Hard ceiling on one agent run's API spend (claude --max-budget-usd, which
# only applies in print mode — Bobby always launches with -p). Unset = no cap.
AGENT_MAX_BUDGET_USD = os.environ.get("BOBBY_AGENT_MAX_BUDGET_USD", "").strip() or None

# --- Sidecar mode (transcription-only; docs/2026-08-05-sidecar-v2-design.md) ---
# BOBBY_SIDECAR=1 switches audio_capture to the v2 pipeline: partials consumed,
# diarization on, every websocket event logged to EVENTS_FILE (source of
# truth), TRANSCRIPT_FILE becomes a derived view that can be amended when the
# server retroactively revises speaker labels. Wake-word modes (orchestrator,
# Discord) are unaffected by this flag.
SIDECAR_MODE = os.environ.get("BOBBY_SIDECAR", "") == "1"
SIDECAR_MAX_SPEAKERS = int(os.environ.get("BOBBY_MAX_SPEAKERS", "2"))
EVENTS_FILE = WORKSPACE_DIR / "events.jsonl"
# Optional label→name mapping, applied at render time only (the event log
# keeps raw A/B labels for provenance). Two sources, merged at each render so
# it can be set live mid-call: BOBBY_SPEAKER_NAMES="A=Max,B=Steven" env var,
# and SPEAKER_NAMES_FILE in the workspace (one "A=Max" per line).
SPEAKER_NAMES = dict(
    pair.split("=", 1)
    for pair in os.environ.get("BOBBY_SPEAKER_NAMES", "").split(",")
    if "=" in pair
)
SPEAKER_NAMES_FILE = WORKSPACE_DIR / "speaker_names.txt"

# Speaker labels in the WAKE-WORD (non-sidecar) local mode. OFF by default:
# that path stays lean on purpose — every extra streaming parameter is one more
# thing that can shift transcription behavior mid-demo, and the trigger phrase
# does not care who said it. Turn it on when two people share one mic and the
# agent needs to know who asked for what:
#     BOBBY_SPEAKER_LABELS=1 BOBBY_SPEAKER_NAMES="A=Max,B=David" ./start_bobby.sh
# Labels are display-only — diarization is added, partials are NOT, so the
# finalized-turn gate that triggers builds is unchanged. Sidecar mode ignores
# this flag (it always diarizes).
SPEAKER_LABELS_ENABLED = os.environ.get("BOBBY_SPEAKER_LABELS", "").strip().lower() in (
    "1", "true", "yes",
)

# Discord configuration (only used in Discord mode)
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")
DISCORD_VOICE_CHANNEL_ID = os.environ.get("DISCORD_VOICE_CHANNEL_ID", "")

# --- AssemblyAI streaming config (shared by local + Discord modes) ---
# Universal-3.5 Pro Realtime (launched 2026-06-23) is the accuracy-first
# streaming model. Set explicitly — do NOT rely on the server default, which
# the docs describe inconsistently. Identifier verified against the installed
# SDK's SpeechModel enum (assemblyai 0.64.x: "universal-3-5-pro").
STREAMING_SPEECH_MODEL = "universal-3-5-pro"

# Natural-language context primes the model on the meeting so the trigger
# phrase and technical questions transcribe more accurately (cheap accuracy
# win; ~$0.05/hr beta add-on on Universal-3.5 Pro). Not a command list.
# Overridable per meeting via BOBBY_STREAMING_PROMPT — a transcription-only
# session (no Bobby triggers) should prime the model with that meeting's
# speakers and vocabulary instead of the wake phrase.
STREAMING_PROMPT = os.environ.get(
    "BOBBY_STREAMING_PROMPT",
    "A live software product meeting. A participant says "
    "'Hey Bobby, please build this' to trigger a coding assistant, then "
    "discusses features and asks technical questions.",
)

# Keyterm biasing toward Bobby's wake word so the launch trigger transcribes
# reliably (free on Universal-3.5 Pro). "Bobby" is a common word, so this can
# in theory cause occasional over-correction — but missing the wake word kills
# the trigger entirely, which is the worse failure for a live demo. The full
# 5-word launch phrase guards against stray-"Bobby" false launches, and resume
# is gated on an outstanding question. Drop/extend this list after rehearsal.
# Overridable per meeting via BOBBY_STREAMING_KEYTERMS (comma-separated).
STREAMING_KEYTERMS = [
    t.strip()
    for t in os.environ.get("BOBBY_STREAMING_KEYTERMS", "Bobby").split(",")
    if t.strip()
]
