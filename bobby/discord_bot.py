#!/usr/bin/env python3
"""
Bobby Discord Bot

Discord integration for Bobby. Provides slash commands for triggering agent tasks
and monitors agent progress, posting updates as Discord embeds with detail threads.

Phase 1: Text-based slash commands + progress monitoring (no voice yet).
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import discord
from dotenv import load_dotenv

from bobby.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_GUILD_ID,
    DISCORD_CHANNEL_ID,
    PROGRESS_FILE,
    TRANSCRIPT_FILE,
    WORKSPACE_DIR,
)
from bobby.agent_runner import (
    launch_agent,
    resume_agent,
    get_recent_context,
    detect_trigger,
    extract_answer,
    write_session_header,
)

# Load .env for bot token
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = discord.Bot(intents=intents)

# Slash command group
bobby_cmds = bot.create_group("bobby", "Bobby AI meeting assistant")

# Agent state
_agent_running = False
_agent_task = None  # asyncio.Task for the running agent


@bot.event
async def on_ready():
    print(f"Bobby bot connected as {bot.user}")
    print(f"Guilds: {[g.name for g in bot.guilds]}")
    # Read env vars directly (config.py may have loaded before dotenv ran)
    guild_id = DISCORD_GUILD_ID or os.getenv("DISCORD_GUILD_ID", "")
    channel_id = DISCORD_CHANNEL_ID or os.getenv("DISCORD_CHANNEL_ID", "")
    if guild_id:
        guild = bot.get_guild(int(guild_id))
        if guild:
            print(f"Target guild: {guild.name}")
        else:
            print(f"Warning: Guild {guild_id} not found")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            print(f"Target channel: #{channel.name}")
        else:
            print(f"Warning: Channel {channel_id} not found")
    print("Bobby is ready.")


# --- Progress Monitoring ---

def read_latest_progress(last_position):
    """
    Read new lines from agent_progress.txt since last_position.

    Returns:
        tuple: (new_lines: list[str], new_position: int)
    """
    try:
        if not PROGRESS_FILE.exists():
            return [], last_position

        with open(PROGRESS_FILE, 'r') as f:
            # Handle file truncation
            f.seek(0, 2)
            file_size = f.tell()
            if file_size < last_position:
                last_position = 0

            f.seek(last_position)
            new_content = f.read()
            new_position = f.tell()

        if not new_content:
            return [], new_position

        lines = [line.strip() for line in new_content.strip().split('\n') if line.strip()]
        return lines, new_position

    except Exception as e:
        print(f"Error reading progress file: {e}")
        return [], last_position


def build_progress_embed(task_name, lines, status="in_progress"):
    """Build a Discord embed showing agent progress."""
    colors = {
        "in_progress": discord.Color.blue(),
        "complete": discord.Color.green(),
        "error": discord.Color.red(),
        "question": discord.Color.orange(),
    }

    embed = discord.Embed(
        title=f"Bobby — {task_name[:200]}",
        color=colors.get(status, discord.Color.greyple()),
    )

    # Build status text from progress lines
    if lines:
        status_lines = []
        for line in lines[-8:]:  # Show last 8 lines max
            if line.startswith("PROGRESS:"):
                msg = line.replace("PROGRESS:", "").strip()
                status_lines.append(msg)
            elif line.startswith("COMPLETE:"):
                msg = line.replace("COMPLETE:", "").strip()
                status_lines.append(f"**Done:** {msg}")
            elif line.startswith("QUESTION:"):
                msg = line.replace("QUESTION:", "").strip()
                status_lines.append(f"**Question:** {msg}")
            elif line.startswith("ERROR:"):
                msg = line.replace("ERROR:", "").strip()
                status_lines.append(f"**Error:** {msg}")
            elif line.startswith("==="):
                continue  # Skip session headers
            else:
                status_lines.append(line)

        embed.description = "\n".join(status_lines) if status_lines else "Starting..."
    else:
        embed.description = "Launching agent..."

    embed.set_footer(text="Bobby AI Meeting Assistant")
    embed.timestamp = discord.utils.utcnow()

    return embed


async def monitor_progress(channel, thread, task_name, status_msg=None):
    """
    Monitor agent_progress.txt and update Discord embed + thread.

    Runs as an async task. Polls the file every 3 seconds and updates
    the embed only when content changes.
    """
    global _agent_running

    # Seek to end of progress file to only show new content
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            f.seek(0, 2)
            last_position = f.tell()
    else:
        last_position = 0

    all_lines = []
    last_embed_content = ""

    # If no status_msg was passed, send an initial embed
    if status_msg is None:
        embed = build_progress_embed(task_name, all_lines)
        status_msg = await channel.send(embed=embed)

    while _agent_running:
        await asyncio.sleep(3)

        new_lines, last_position = read_latest_progress(last_position)
        if not new_lines:
            continue

        all_lines.extend(new_lines)

        # Post new lines to the thread (strip protocol prefixes for clean display)
        for line in new_lines:
            if line.startswith("==="):
                continue  # Skip session headers
            # Strip the protocol prefix, keep the human-readable part
            display = line
            for prefix in ("PROGRESS:", "COMPLETE:", "QUESTION:", "ERROR:"):
                if line.startswith(prefix):
                    display = line[len(prefix):].strip()
                    break
            try:
                await thread.send(f"> {display}")
            except Exception as e:
                print(f"Error posting to thread: {e}")

        # Determine status
        status = "in_progress"
        for line in new_lines:
            if line.startswith("COMPLETE:"):
                status = "complete"
            elif line.startswith("QUESTION:"):
                status = "question"
            elif line.startswith("ERROR:"):
                status = "error"

        # Update embed only if content changed
        embed = build_progress_embed(task_name, all_lines, status)
        current_content = embed.description
        if current_content != last_embed_content:
            try:
                await status_msg.edit(embed=embed)
                last_embed_content = current_content
            except Exception as e:
                print(f"Error updating embed: {e}")

        if status in ("complete", "error"):
            break

    # Final update after agent finishes
    if all_lines:
        status = "complete"
        for line in all_lines:
            if line.startswith("ERROR:"):
                status = "error"
                break
        embed = build_progress_embed(task_name, all_lines, status)
        try:
            await status_msg.edit(embed=embed)
        except Exception:
            pass

    # Archive the thread
    try:
        await thread.edit(archived=True)
    except Exception:
        pass


# --- Agent Execution ---

async def run_agent(channel, task_name, context):
    """
    Launch the Claude Code agent and monitor its progress.

    Runs the blocking agent subprocess in a background thread via asyncio.to_thread,
    while the progress monitor runs as a concurrent async task.
    """
    global _agent_running, _agent_task

    _agent_running = True

    # Send initial embed and create a thread off it for detailed logs
    embed = build_progress_embed(task_name, [], "in_progress")
    try:
        status_msg = await channel.send(embed=embed)
        thread = await status_msg.create_thread(
            name=f"Bobby: {task_name[:80]}",
            auto_archive_duration=60,
        )
    except Exception as e:
        print(f"Error creating thread: {e}")
        status_msg = None
        thread = channel

    # Start progress monitor as async task
    monitor_task = asyncio.create_task(
        monitor_progress(channel, thread, task_name, status_msg=status_msg)
    )

    # Run the blocking agent in a background thread
    try:
        return_code = await asyncio.to_thread(
            launch_agent, context, WORKSPACE_DIR, PROGRESS_FILE
        )
        print(f"Agent finished with return code: {return_code}")
    except Exception as e:
        print(f"Agent error: {e}")
        try:
            await channel.send(f"Agent error: {e}")
        except Exception:
            pass
    finally:
        _agent_running = False
        _agent_task = None

    # Wait for monitor to finish its final update
    try:
        await asyncio.wait_for(monitor_task, timeout=10)
    except asyncio.TimeoutError:
        monitor_task.cancel()


# --- Slash Commands ---

@bobby_cmds.command(description="Ask Bobby to build something")
async def build(
    ctx: discord.ApplicationContext,
    task: discord.Option(str, "What should Bobby build?", required=True),
):
    """Launch a Claude Code agent to build the requested feature."""
    global _agent_running, _agent_task

    if _agent_running:
        await ctx.respond("Bobby is already working on something. Wait for it to finish or check `/bobby status`.")
        return

    await ctx.respond(f"On it! Building: **{task}**", ephemeral=True)

    # For slash commands, the task description IS the context
    # (unlike voice triggers which use transcript context)
    context = f"Task requested via Discord: {task}"

    _agent_task = asyncio.create_task(
        run_agent(ctx.channel, task, context)
    )


@bobby_cmds.command(description="Check Bobby's current status")
async def status(ctx: discord.ApplicationContext):
    """Check if Bobby is currently working on something."""
    if _agent_running:
        # Read latest progress
        lines = []
        if PROGRESS_FILE.exists():
            try:
                content = PROGRESS_FILE.read_text().strip()
                if content:
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
            except Exception:
                pass

        latest = lines[-1] if lines else "Working..."
        await ctx.respond(f"Bobby is working. Latest: {latest}")
    else:
        await ctx.respond("Bobby is idle. Use `/bobby build <task>` to start a task.")


def run_bot():
    """Start the Discord bot."""
    token = DISCORD_BOT_TOKEN or os.getenv("DISCORD_BOT_TOKEN")
    if not token or token == "your_discord_bot_token_here":
        print("ERROR: DISCORD_BOT_TOKEN not set!")
        print("Please add your bot token to .env")
        print("See .env.example for template")
        return

    # Register commands to specific guild for instant availability during dev
    guild_id = DISCORD_GUILD_ID or os.getenv("DISCORD_GUILD_ID")
    if guild_id:
        guild_ids = [int(guild_id)]
        print(f"Registering commands to guild {guild_id} (instant)")
    else:
        guild_ids = None
        print("No DISCORD_GUILD_ID set — commands will register globally (may take up to 1 hour)")

    # Apply guild_ids to command group
    if guild_ids:
        bobby_cmds.guild_ids = guild_ids

    bot.run(token)


if __name__ == "__main__":
    run_bot()
