#!/usr/bin/env python3
"""
Bobby - Discord Mode Launcher

Starts Bobby as a Discord bot. Requires:
1. Discord bot token in .env (DISCORD_BOT_TOKEN)
2. py-cord installed: uv sync --extra discord
3. ffmpeg installed: brew install ffmpeg

Usage:
    uv run python start_discord.py
"""

from bobby.discord_bot import run_bot

if __name__ == "__main__":
    run_bot()
