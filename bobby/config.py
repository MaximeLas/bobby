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

# Runtime state files (created in the target workspace during sessions)
TRANSCRIPT_FILE = WORKSPACE_DIR / "meeting_transcript.txt"
PROGRESS_FILE = WORKSPACE_DIR / "agent_progress.txt"
PAUSE_FLAG_FILE = WORKSPACE_DIR / "pause_transcription.flag"
BOBBY_SPEECH_FILE = WORKSPACE_DIR / "bobby_last_speech.txt"

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
