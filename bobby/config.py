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

# Discord configuration (only used in Discord mode)
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")
