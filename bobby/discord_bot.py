#!/usr/bin/env python3
"""
Bobby Discord Bot

Discord integration for Bobby. Provides slash commands for triggering agent tasks
and monitors agent progress, posting updates as Discord embeds with detail threads.

Phase 1: Text-based slash commands + progress monitoring.
Phase 2: Voice receive — Bobby joins voice channels and transcribes via Assembly AI.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

import discord
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy Discord internals (gateway handshake, HTTP, opus decode errors)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("discord.opus").setLevel(logging.WARNING)

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

# Load opus library for voice receive (Pycord can't find it automatically on macOS)
if not discord.opus.is_loaded():
    try:
        discord.opus.load_opus("/opt/homebrew/lib/libopus.dylib")
        print("Loaded libopus from Homebrew")
    except Exception as e:
        print(f"Warning: Could not load libopus: {e}")
        print("Voice receive will not work. Install with: brew install opus")

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

# Voice state
_voice_sink = None  # AssemblyAISink instance (active during voice recording)
_transcript_watcher_task = None  # async task watching transcript for voice triggers


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

        # Announce completion in voice
        if return_code == 0:
            await _speak_in_voice("Done. The task is complete.")
        else:
            await _speak_in_voice("Something went wrong. Check the progress for details.")

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


# --- Voice Output ---

async def _speak_in_voice(text):
    """
    Generate TTS audio and play it in the Discord voice channel.

    No-op if the bot is not connected to a voice channel.
    Tries ElevenLabs first, falls back to macOS 'say' if unavailable.
    """
    # Find our voice client across all guilds
    vc = None
    for voice_client in bot.voice_clients:
        if voice_client.is_connected():
            vc = voice_client
            break

    if vc is None:
        print(f"Bobby says (no voice channel): {text}")
        return

    temp_file = "/tmp/bobby_discord_speech.mp3"

    try:
        from bobby.tts import generate_audio

        print(f"Bobby speaking in voice (ElevenLabs): {text}")
        audio_bytes = await asyncio.to_thread(generate_audio, text)

        with open(temp_file, "wb") as f:
            f.write(audio_bytes)

    except Exception as e:
        # Extract just the useful error message, not the full HTTP headers
        error_msg = str(e)
        if hasattr(e, 'body') and isinstance(e.body, dict):
            detail = e.body.get('detail', {})
            if isinstance(detail, dict):
                error_msg = detail.get('message', error_msg)
        print(f"ElevenLabs failed: {error_msg} — falling back to macOS say")
        # macOS 'say' can output to AIFF file, which FFmpeg can decode
        temp_file = "/tmp/bobby_discord_speech.aiff"
        try:
            import subprocess
            await asyncio.to_thread(
                subprocess.run,
                ["say", "-o", temp_file, text],
                check=True,
                timeout=10,
            )
        except Exception as fallback_error:
            print(f"Fallback TTS also failed: {fallback_error}")
            return

    try:
        if vc.is_playing():
            vc.stop()

        source = discord.FFmpegPCMAudio(temp_file)
        vc.play(source)

        while vc.is_playing():
            await asyncio.sleep(0.5)

        print("Bobby finished speaking")

    except Exception as e:
        print(f"Voice playback error: {e}")


# --- Voice Commands ---

async def _recording_finished_callback(sink, channel):
    """Called by Pycord when stop_recording() is invoked. No-op for us."""
    print("Recording finished callback fired")


async def _watch_transcript_for_triggers(text_channel):
    """
    Watch meeting_transcript.txt for voice triggers.

    Runs as an async task while Bobby is in a voice channel. Polls the
    transcript file for new content and checks for trigger phrases using
    the shared detect_trigger() function. Manages debounce state and
    file position locally.
    """
    global _agent_running, _agent_task

    import time

    # Start reading from end of file
    if TRANSCRIPT_FILE.exists():
        with open(TRANSCRIPT_FILE, "r") as f:
            f.seek(0, 2)
            last_position = f.tell()
    else:
        last_position = 0

    last_launch_time = 0
    DEBOUNCE_SECONDS = 10

    print("Transcript watcher started — listening for voice triggers")

    while True:
        await asyncio.sleep(2)

        if not TRANSCRIPT_FILE.exists():
            continue

        try:
            with open(TRANSCRIPT_FILE, "r") as f:
                f.seek(0, 2)
                file_size = f.tell()
                if file_size < last_position:
                    last_position = 0
                f.seek(last_position)
                new_content = f.read()
                last_position = f.tell()
        except Exception:
            continue

        if not new_content.strip():
            continue

        trigger = detect_trigger(new_content)
        if trigger is None:
            continue

        if trigger == "launch":
            # Debounce launch triggers (prevents transcript echo double-fires)
            now = time.time()
            if now - last_launch_time < DEBOUNCE_SECONDS:
                print(f"Launch trigger debounced ({now - last_launch_time:.0f}s < {DEBOUNCE_SECONDS}s)")
                continue
            last_launch_time = now

            if _agent_running:
                print("Voice trigger detected but agent already running")
                await _speak_in_voice("I'm already working on something. Hold on.")
                continue

            print("Voice trigger detected: launching agent")
            await _speak_in_voice("On it. Let me work on that.")
            context = get_recent_context(TRANSCRIPT_FILE, lines=15)
            task_name = "Voice-triggered task"

            _agent_task = asyncio.create_task(
                run_agent(text_channel, task_name, context)
            )

        elif trigger == "resume":
            # Phase 4 will implement resume via voice
            print("Resume trigger detected (not yet implemented in Discord mode)")


@bobby_cmds.command(description="Join your voice channel and start listening")
async def join(ctx: discord.ApplicationContext):
    """Join the user's voice channel and start transcribing."""
    global _voice_sink, _transcript_watcher_task

    # Check if user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.respond("You need to be in a voice channel first!", ephemeral=True)
        return

    voice_channel = ctx.author.voice.channel

    # Check if already connected
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.respond("I'm already in a voice channel! Use `/bobby leave` first.", ephemeral=True)
        return

    await ctx.respond(f"Joining **{voice_channel.name}** and starting transcription...", ephemeral=True)

    try:
        # Connect to voice channel
        vc = await voice_channel.connect()

        # Create and start the custom sink
        from bobby.discord_sink import AssemblyAISink

        _voice_sink = AssemblyAISink(guild=ctx.guild)
        if not _voice_sink.start_transcription():
            await ctx.followup.send("Failed to start transcription — check ASSEMBLYAI_API_KEY.", ephemeral=True)
            await vc.disconnect()
            _voice_sink = None
            return

        # Start recording with the custom sink
        vc.start_recording(_voice_sink, _recording_finished_callback, ctx.channel)

        # Write session header to transcript
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(TRANSCRIPT_FILE, "a") as f:
            f.write(f"\n[{timestamp}] === Bobby joined Discord voice: {voice_channel.name} ===\n\n")

        # Start watching transcript for voice triggers
        _transcript_watcher_task = asyncio.create_task(
            _watch_transcript_for_triggers(ctx.channel)
        )

        print(f"Joined voice channel: {voice_channel.name}")
        print(f"Recording + transcription active")

    except Exception as e:
        print(f"Error joining voice channel: {e}")
        await ctx.followup.send(f"Error joining voice channel: {e}", ephemeral=True)
        _voice_sink = None


@bobby_cmds.command(description="Leave the voice channel and stop listening")
async def leave(ctx: discord.ApplicationContext):
    """Leave the voice channel and stop transcribing."""
    global _voice_sink, _transcript_watcher_task

    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await ctx.respond("I'm not in a voice channel.", ephemeral=True)
        return

    await ctx.respond("Leaving voice channel...", ephemeral=True)

    try:
        # Stop the transcript watcher
        if _transcript_watcher_task:
            _transcript_watcher_task.cancel()
            _transcript_watcher_task = None

        # Stop recording (triggers cleanup on the sink)
        if ctx.voice_client.recording:
            ctx.voice_client.stop_recording()

        # Stop transcription explicitly (in case cleanup didn't run)
        if _voice_sink:
            _voice_sink.stop_transcription()
            _voice_sink = None

        # Disconnect from voice
        await ctx.voice_client.disconnect()

        # Write session footer to transcript
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(TRANSCRIPT_FILE, "a") as f:
            f.write(f"\n[{timestamp}] === Bobby left Discord voice ===\n\n")

        print("Left voice channel, transcription stopped")

    except Exception as e:
        print(f"Error leaving voice channel: {e}")
        await ctx.followup.send(f"Error: {e}", ephemeral=True)


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
