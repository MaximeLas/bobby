#!/usr/bin/env python3
"""
Bobby Discord Bot

Discord integration for Bobby. Provides slash commands for triggering agent tasks
and monitors agent progress, posting updates as Discord embeds with detail threads.

Phase 1: Text-based slash commands + progress monitoring.
Phase 2: Voice receive — Bobby joins voice channels and transcribes via Assembly AI.
Phase 3: Voice output — Bobby speaks in Discord via ElevenLabs TTS.
Phase 4: Resume trigger, graceful shutdown, auto-join/leave, personality, AAI recovery.
"""

import asyncio
import logging
import os
import time
from datetime import datetime

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
logging.getLogger("discord.opus").setLevel(logging.ERROR)
# voice_client logs a full traceback for harmless 4000 reconnects — suppress
logging.getLogger("discord.voice_client").setLevel(logging.CRITICAL)
logging.getLogger("discord.player").setLevel(logging.WARNING)

from bobby.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_GUILD_ID,
    DISCORD_CHANNEL_ID,
    DISCORD_VOICE_CHANNEL_ID,
    PROACTIVE_ENABLED,
    PROGRESS_FILE,
    TRANSCRIPT_FILE,
    WORKSPACE_DIR,
)
from bobby.agent_runner import (
    launch_agent,
    resume_agent,
    stop_agent,
    get_recent_context,
    detect_trigger,
    extract_answer,
    write_session_header,
)
from bobby.prompts import (
    VOICE_ACKNOWLEDGE_LAUNCH,
    VOICE_ANNOUNCE_COMPLETION,
    VOICE_ANNOUNCE_ERROR,
    VOICE_AGENT_BUSY,
    VOICE_ACKNOWLEDGE_RESUME,
    VOICE_ANNOUNCE_RESUME_COMPLETE,
    VOICE_ANNOUNCE_QUESTION,
    VOICE_BRAIN_ERROR,
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
_agent_asked_question = False  # True when agent wrote a QUESTION: line
_agent_stopped_by_user = False  # True when /bobby stop killed the agent (suppresses error announcement)

# Voice state
_voice_sink = None  # AssemblyAISink instance (active during voice recording)
_transcript_watcher_task = None  # async task watching transcript for voice triggers

# Proactive suggestions (BOBBY_PROACTIVE=1; see bobby/suggestions.py)
if PROACTIVE_ENABLED:
    from bobby.suggestions import ProactiveEngine
    _proactive_engine = ProactiveEngine()
    print("Proactive suggestions: ENABLED (BOBBY_PROACTIVE=1)")
else:
    _proactive_engine = None


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

    # Auto-join voice channel if configured
    voice_channel_id = DISCORD_VOICE_CHANNEL_ID or os.getenv("DISCORD_VOICE_CHANNEL_ID", "")
    if voice_channel_id:
        await _auto_join_voice(voice_channel_id)


async def _auto_join_voice(voice_channel_id):
    """Auto-join a voice channel on startup and start transcription."""
    global _voice_sink, _transcript_watcher_task

    try:
        channel = bot.get_channel(int(voice_channel_id))
        if not channel:
            print(f"Warning: Voice channel {voice_channel_id} not found, skipping auto-join")
            return

        # Check if anyone is in the channel (don't join empty channels)
        human_members = [m for m in channel.members if not m.bot]
        if not human_members:
            print(f"Voice channel {channel.name} is empty, skipping auto-join")
            return

        print(f"Auto-joining voice channel: {channel.name}")
        vc = await channel.connect()

        # Wait for voice websocket to stabilize — Pycord sometimes drops and
        # reconnects immediately after connect (code 4000). Starting recording
        # too early means it gets lost in the reconnect.
        await asyncio.sleep(2)

        from bobby.discord_sink import AssemblyAISink
        _voice_sink = AssemblyAISink(guild=channel.guild)
        if not _voice_sink.start_transcription():
            print("Failed to start transcription during auto-join")
            await vc.disconnect()
            _voice_sink = None
            return

        vc.start_recording(_voice_sink, _recording_finished_callback, None)

        # Write session header to transcript
        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(TRANSCRIPT_FILE, "a") as f:
            f.write(f"\n[{timestamp}] === Bobby joined Discord voice: {channel.name} ===\n\n")

        # Find the text channel for progress updates
        text_channel_id = DISCORD_CHANNEL_ID or os.getenv("DISCORD_CHANNEL_ID", "")
        text_channel = bot.get_channel(int(text_channel_id)) if text_channel_id else None

        _transcript_watcher_task = asyncio.create_task(
            _watch_transcript_for_triggers(text_channel)
        )

        print(f"Auto-joined {channel.name} — recording + transcription active")

    except Exception as e:
        print(f"Auto-join failed: {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    """Auto-join when someone enters the configured voice channel, auto-leave when empty."""
    # Don't trigger on the bot's own state changes
    if member.id == bot.user.id:
        return

    # --- Auto-join: someone joined the configured voice channel ---
    voice_channel_id = DISCORD_VOICE_CHANNEL_ID or os.getenv("DISCORD_VOICE_CHANNEL_ID", "")
    if (voice_channel_id and after.channel
            and str(after.channel.id) == voice_channel_id
            and (before.channel is None or before.channel != after.channel)):
        # Check if bot is already in voice
        vc = member.guild.voice_client
        if not vc or not vc.is_connected():
            print(f"{member.display_name} joined {after.channel.name}, auto-joining")
            await _auto_join_voice(voice_channel_id)
            return

    # --- Auto-leave: someone left the channel the bot is in ---
    if not before.channel:
        return
    if before.channel == after.channel:
        return

    vc = member.guild.voice_client
    if not vc or vc.channel != before.channel:
        return

    # Check if any humans remain
    human_members = [m for m in before.channel.members if not m.bot]
    if len(human_members) == 0:
        print(f"All humans left {before.channel.name}, auto-leaving")
        await _cleanup_voice(vc)


async def _cleanup_voice(vc=None):
    """Clean up voice connection, sink, and transcript watcher."""
    global _voice_sink, _transcript_watcher_task

    if _transcript_watcher_task:
        _transcript_watcher_task.cancel()
        _transcript_watcher_task = None

    if vc and vc.recording:
        try:
            vc.stop_recording()
        except Exception:
            pass

    if _voice_sink:
        _voice_sink.stop_transcription()
        _voice_sink = None

    if vc and vc.is_connected():
        await vc.disconnect()

    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        with open(TRANSCRIPT_FILE, "a") as f:
            f.write(f"\n[{timestamp}] === Bobby left Discord voice ===\n\n")
    except Exception:
        pass

    print("Left voice channel, transcription stopped")


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

    # Check if agent provided a TASK: line — use it as the title
    title = task_name
    for line in lines:
        if line.startswith("TASK:"):
            title = line.replace("TASK:", "").strip()
            break

    embed = discord.Embed(
        title=f"Bobby — {title[:200]}",
        color=colors.get(status, discord.Color.greyple()),
    )

    # Build status text from progress lines
    if lines:
        status_lines = []
        for line in lines[-8:]:  # Show last 8 lines max
            if line.startswith("TASK:"):
                continue  # Task name is in the title, not the body
            elif line.startswith("PROGRESS:"):
                msg = line.replace("PROGRESS:", "").strip()
                # Normalize ASCII arrow to Unicode (agent doesn't always use →)
                if msg.startswith("-> "):
                    msg = "→ " + msg[3:]
                status_lines.append(msg)
            elif line.startswith("COMPLETE:"):
                msg = line.replace("COMPLETE:", "").strip()
                status_lines.append(f"**Done:** {msg}")
            elif line.startswith("QUESTION:"):
                msg = line.replace("QUESTION:", "").strip()
                status_lines.append(f"\n**Question:** {msg}")
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
    global _agent_running, _agent_asked_question

    # Seek to end of progress file to only show new content
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            f.seek(0, 2)
            last_position = f.tell()
    else:
        last_position = 0

    all_lines = []

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
            if line.startswith("TASK:"):
                # Update thread name with the real task description
                new_name = line.replace("TASK:", "").strip()
                try:
                    await thread.edit(name=f"Bobby: {new_name[:80]}")
                except Exception:
                    pass
                continue
            # Format for thread display
            display = line
            if line.startswith("QUESTION:"):
                msg = line.replace("QUESTION:", "").strip()
                display = f"**Question:** {msg}"
            else:
                for prefix in ("PROGRESS:", "COMPLETE:", "ERROR:"):
                    if line.startswith(prefix):
                        display = line[len(prefix):].strip()
                        break
            # Normalize ASCII arrow
            if display.startswith("-> "):
                display = "→ " + display[3:]
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
                _agent_asked_question = True
                # Speak the question in voice — fire-and-forget so the embed
                # updates immediately instead of waiting 30s for TTS playback
                question_text = line.replace("QUESTION:", "").strip()
                asyncio.create_task(
                    _speak_in_voice(f"{VOICE_ANNOUNCE_QUESTION} {question_text}")
                )
            elif line.startswith("ERROR:"):
                status = "error"

        # Update embed (always — title may change from TASK: even if description doesn't)
        embed = build_progress_embed(task_name, all_lines, status)
        try:
            await status_msg.edit(embed=embed)
        except Exception as e:
            print(f"Error updating embed: {e}")

        if status in ("complete", "error"):
            break

    # Read any remaining lines the monitor missed (agent may have exited
    # between poll cycles, writing lines we never saw)
    final_lines, _ = read_latest_progress(last_position)
    if final_lines:
        all_lines.extend(final_lines)
        for line in final_lines:
            if line.startswith("TASK:"):
                new_name = line.replace("TASK:", "").strip()
                try:
                    await thread.edit(name=f"Bobby: {new_name[:80]}")
                except Exception:
                    pass

    # Final embed update
    if all_lines:
        status = "complete"
        for line in all_lines:
            if line.startswith("ERROR:"):
                status = "error"
                break
            elif line.startswith("QUESTION:"):
                status = "question"
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

def _extract_task_name(context):
    """
    Extract a human-readable task name from transcript context.

    Grabs the last substantive line before the trigger phrase.
    Zero latency — just string processing, no AI call.
    """
    lines = context.strip().split('\n')
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('==='):
            continue
        # Skip lines that contain a trigger phrase (uses the same
        # normalization as detect_trigger — handles commas, punctuation, etc.)
        if detect_trigger(stripped) is not None:
            continue

        # Strip [HH:MM:SS] timestamp prefix
        text = stripped
        if text.startswith('[') and '] ' in text:
            text = text[text.index('] ') + 2:]
        # Strip [Speaker] prefix
        if text.startswith('[') and '] ' in text:
            text = text[text.index('] ') + 2:]

        text = text.strip()
        if text:
            return text[:100]

    return "Voice-triggered task"


async def run_agent(channel, task_name, context):
    """
    Launch the Claude Code agent and monitor its progress.

    Runs the blocking agent subprocess in a background thread via asyncio.to_thread,
    while the progress monitor runs as a concurrent async task.
    """
    global _agent_running, _agent_task, _agent_asked_question, _agent_stopped_by_user

    _agent_running = True
    _agent_asked_question = False
    _agent_stopped_by_user = False

    # Send initial embed and create a thread off it for detailed logs
    embed = build_progress_embed(task_name, [], "in_progress")
    try:
        if channel:
            status_msg = await channel.send(embed=embed)
            thread = await status_msg.create_thread(
                name=f"Bobby: {task_name[:80]}",
                auto_archive_duration=60,
            )
        else:
            status_msg = None
            thread = None
    except Exception as e:
        print(f"Error creating thread: {e}")
        status_msg = None
        thread = None

    # Start progress monitor as async task (only if we have a channel)
    monitor_task = None
    if channel and thread:
        monitor_task = asyncio.create_task(
            monitor_progress(channel, thread, task_name, status_msg=status_msg)
        )

    # Run the blocking agent in a background thread
    try:
        return_code = await asyncio.to_thread(
            launch_agent, context, WORKSPACE_DIR, PROGRESS_FILE
        )
        print(f"Agent finished with return code: {return_code}")

        # Check if agent stopped because it asked a question.
        # The agent exits with code 0 after writing QUESTION:, but that's
        # not a completion — it's waiting for an answer.
        stopped_for_question = False
        if PROGRESS_FILE.exists():
            try:
                plines = PROGRESS_FILE.read_text().strip().split('\n')
                last_meaningful = next(
                    (l for l in reversed(plines) if l.strip() and not l.startswith('===')),
                    ''
                )
                if last_meaningful.strip().startswith('QUESTION:'):
                    stopped_for_question = True
                    _agent_asked_question = True
            except Exception:
                pass

        # Announce result in voice (skip if agent asked a question — either
        # it stopped at QUESTION: or it continued past it)
        if _agent_stopped_by_user:
            print("Agent stopped by user — skipping announcement")
        elif stopped_for_question or _agent_asked_question:
            print("Agent asked a question — skipping completion announcement")
        elif return_code == 0:
            await _speak_in_voice(VOICE_ANNOUNCE_COMPLETION)
        else:
            await _speak_in_voice(VOICE_ANNOUNCE_ERROR)

    except Exception as e:
        print(f"Agent error: {e}")
        if channel:
            try:
                await channel.send(f"Agent error: {e}")
            except Exception:
                pass
    finally:
        _agent_running = False
        _agent_task = None

    # Wait for monitor to finish its final update
    if monitor_task:
        try:
            await asyncio.wait_for(monitor_task, timeout=10)
        except asyncio.TimeoutError:
            monitor_task.cancel()


async def run_resume_agent(channel, answer):
    """
    Resume the Claude Code agent with an answer and monitor progress.
    """
    global _agent_running, _agent_task, _agent_asked_question, _agent_stopped_by_user

    _agent_running = True
    _agent_asked_question = False
    _agent_stopped_by_user = False

    task_name = "Resuming with answer"

    # Send embed + thread for resume progress (only if we have a channel)
    monitor_task = None
    if channel:
        embed = build_progress_embed(task_name, [], "in_progress")
        try:
            status_msg = await channel.send(embed=embed)
            thread = await status_msg.create_thread(
                name="Bobby: resume",
                auto_archive_duration=60,
            )
            monitor_task = asyncio.create_task(
                monitor_progress(channel, thread, task_name, status_msg=status_msg)
            )
        except Exception as e:
            print(f"Error creating resume thread: {e}")

    try:
        return_code = await asyncio.to_thread(
            resume_agent, answer, WORKSPACE_DIR
        )
        print(f"Agent resume finished with return code: {return_code}")

        if _agent_stopped_by_user:
            print("Agent stopped by user — skipping announcement")
        elif return_code == 0:
            await _speak_in_voice(VOICE_ANNOUNCE_RESUME_COMPLETE)
        else:
            await _speak_in_voice(VOICE_ANNOUNCE_ERROR)

    except Exception as e:
        print(f"Agent resume error: {e}")
        if channel:
            try:
                await channel.send(f"Agent resume error: {e}")
            except Exception:
                pass
    finally:
        _agent_running = False
        _agent_task = None

    if monitor_task:
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


@bobby_cmds.command(description="Answer Bobby's question and resume the agent")
async def resume(
    ctx: discord.ApplicationContext,
    answer: discord.Option(str, "Your answer to Bobby's question", required=True),
):
    """
    Manually resume the agent with a typed answer.

    Demo safety net for the voice resume trigger: if "Thank you, Bobby" is
    misheard or the answer is extracted badly from the transcript, this gives
    an exact, typed answer instead. Unlike the voice path it also works when
    no QUESTION: line was detected (forced resume of the last agent session).
    """
    global _agent_task

    if _agent_running:
        await ctx.respond("Bobby is still working — wait for the question or use `/bobby stop` first.")
        return

    note = "" if _agent_asked_question else "\n-# No outstanding question — resuming the last agent session anyway."
    await ctx.respond(f"Resuming with answer: **{answer}**{note}", ephemeral=True)

    _agent_task = asyncio.create_task(
        run_resume_agent(ctx.channel, answer)
    )


@bobby_cmds.command(description="Stop the currently running agent")
async def stop(ctx: discord.ApplicationContext):
    """
    Kill the running agent subprocess.

    Demo safety net for a runaway or mis-triggered build: terminates the
    `claude` process; run_agent's normal cleanup then resets state. The
    _agent_stopped_by_user flag suppresses the error voice announcement.
    """
    global _agent_stopped_by_user

    if not _agent_running:
        await ctx.respond("Bobby is idle — nothing to stop.")
        return

    _agent_stopped_by_user = True
    stopped = await asyncio.to_thread(stop_agent)
    if not stopped and _agent_running:
        # Startup window: run_agent sets _agent_running before launch_agent
        # spawns the subprocess, so a very fast /stop can find no process yet.
        # Wait a beat and try once more.
        await asyncio.sleep(1)
        stopped = await asyncio.to_thread(stop_agent)

    if stopped:
        await ctx.respond("🛑 Stopped the running agent.")
    elif _agent_running:
        _agent_stopped_by_user = False
        await ctx.respond("Couldn't stop it — the agent is still starting up. Try `/bobby stop` again.")
    else:
        # The agent finished naturally just as stop was pressed. Leave the
        # flag set so the now-moot announcement stays suppressed (resetting it
        # here races run_agent's announcement check — it reads the flag after
        # this coroutine resumes). run_agent resets the flag on the next run.
        await ctx.respond("The agent finished just as you pressed stop.")


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
        print(f"[VOICE skip] Not in voice channel. Text: {text[:80]}")
        return

    temp_file = "/tmp/bobby_discord_speech.mp3"

    try:
        from bobby.tts import generate_audio

        print(f"[VOICE] Generating ElevenLabs audio ({len(text)} chars)...")
        audio_bytes = await asyncio.to_thread(generate_audio, text)

        with open(temp_file, "wb") as f:
            f.write(audio_bytes)
        print(f"[VOICE] ElevenLabs audio ready ({len(audio_bytes)} bytes)")

    except Exception as e:
        # Extract just the useful error message, not the full HTTP headers
        error_msg = str(e)
        if hasattr(e, 'body') and isinstance(e.body, dict):
            detail = e.body.get('detail', {})
            if isinstance(detail, dict):
                error_msg = detail.get('message', error_msg)
        print(f"[VOICE] ElevenLabs failed: {error_msg} — falling back to macOS say")
        # macOS 'say' can output to AIFF file, which FFmpeg can decode
        temp_file = "/tmp/bobby_discord_speech.aiff"
        try:
            import subprocess
            await asyncio.to_thread(
                subprocess.run,
                ["say", "-o", temp_file, text],
                check=True,
                timeout=30,
            )
            print(f"[VOICE] macOS say audio ready")
        except Exception as fallback_error:
            print(f"[VOICE FAILED] macOS say also failed: {fallback_error}")
            return

    try:
        if vc.is_playing():
            print("[VOICE] Stopping current playback")
            vc.stop()

        source = discord.FFmpegPCMAudio(temp_file)
        vc.play(source)
        print(f"[VOICE] Playing in Discord...")

        while vc.is_playing():
            await asyncio.sleep(0.5)

        print("[VOICE] Playback complete")

    except Exception as e:
        print(f"[VOICE FAILED] Playback error: {e}")


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
    global _agent_running, _agent_task, _agent_asked_question

    # Start reading from end of file
    if TRANSCRIPT_FILE.exists():
        with open(TRANSCRIPT_FILE, "r") as f:
            f.seek(0, 2)
            last_position = f.tell()
    else:
        last_position = 0

    last_launch_time = 0
    last_converse_time = 0
    DEBOUNCE_SECONDS = 10
    disconnect_count = 0  # Tolerate brief disconnects (Pycord auto-reconnects)

    print("Transcript watcher started — listening for voice triggers")

    while True:
        await asyncio.sleep(2)

        # Stop if bot is no longer in a voice channel — but tolerate brief
        # disconnects (Pycord reconnects automatically, ~1-2 seconds)
        if not bot.voice_clients or not any(vc.is_connected() for vc in bot.voice_clients):
            disconnect_count += 1
            if disconnect_count >= 5:  # 10 seconds of no connection
                print("Transcript watcher stopping — bot disconnected for too long")
                break
            continue
        disconnect_count = 0

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
            # Trigger-free discussion feeds the proactive engine (if enabled).
            # try_begin runs only cheap gates; the LLM analysis + speech is
            # fire-and-forget so the watcher never blocks.
            if _proactive_engine is not None:
                _proactive_engine.accumulate(new_content)
                excerpt = _proactive_engine.try_begin(
                    time.time(), agent_running=_agent_running
                )
                if excerpt:
                    asyncio.create_task(_handle_proactive(text_channel, excerpt))
            continue

        # Someone engaged Bobby explicitly — no butting in for a while
        if _proactive_engine is not None:
            _proactive_engine.note_activity(time.time())

        if trigger == "launch":
            # Debounce launch triggers (prevents transcript echo double-fires)
            now = time.time()
            if now - last_launch_time < DEBOUNCE_SECONDS:
                print(f"Launch trigger debounced ({now - last_launch_time:.0f}s < {DEBOUNCE_SECONDS}s)")
                continue
            last_launch_time = now

            if _agent_running:
                print("Voice trigger detected but agent already running")
                await _speak_in_voice(VOICE_AGENT_BUSY)
                continue

            print("Voice trigger detected: launching agent")
            await _speak_in_voice(VOICE_ACKNOWLEDGE_LAUNCH)
            context = get_recent_context(TRANSCRIPT_FILE, lines=15)
            task_name = _extract_task_name(context)

            _agent_task = asyncio.create_task(
                run_agent(text_channel, task_name, context)
            )

        elif trigger == "resume":
            if _agent_running:
                print("Resume trigger detected but agent is still running")
                continue

            if not _agent_asked_question:
                print("Resume trigger detected but agent didn't ask a question — ignoring")
                continue

            print("Voice trigger detected: resuming agent with answer")
            await _speak_in_voice(VOICE_ACKNOWLEDGE_RESUME)

            # Get recent transcript to extract the answer
            recent = get_recent_context(TRANSCRIPT_FILE, lines=10)
            answer = extract_answer(recent)
            print(f"Extracted answer: {answer}")

            _agent_task = asyncio.create_task(
                run_resume_agent(text_channel, answer)
            )

        elif trigger == "converse":
            # "Hey Bobby, <anything else>" — answer from meeting context.
            # Allowed while an agent is building (that's the point: "Hey
            # Bobby, how's it going?" reads the progress file).
            now = time.time()
            if now - last_converse_time < DEBOUNCE_SECONDS:
                print(f"Converse trigger debounced ({now - last_converse_time:.0f}s < {DEBOUNCE_SECONDS}s)")
                continue
            last_converse_time = now

            print("Converse trigger detected: asking the brain")
            # Fire-and-forget so the watcher keeps polling during the
            # 5-15s brain call + TTS playback (same critical pattern as
            # question announcements in monitor_progress).
            asyncio.create_task(_handle_conversation(text_channel))


async def _handle_proactive(text_channel, excerpt):
    """Run one proactive analysis; speak + post the offer if one comes back."""
    suggestion = await asyncio.to_thread(
        _proactive_engine.analyze, excerpt, time.time()
    )
    if not suggestion:
        return

    print(f"Proactive suggestion: {suggestion['feature']}")
    if text_channel:
        try:
            await text_channel.send(f"💡 {suggestion['voice_line']}")
        except Exception as e:
            print(f"Error posting suggestion to channel: {e}")
    await _speak_in_voice(suggestion["voice_line"])


async def _handle_conversation(text_channel):
    """Answer a 'Hey Bobby, ...' utterance: brain call -> voice + text."""
    from bobby.brain import ask_brain

    context = get_recent_context(TRANSCRIPT_FILE, lines=20)

    # If an agent is building, give the brain the progress tail so status
    # questions ("how's it going?") get real answers.
    progress_tail = None
    if _agent_running and PROGRESS_FILE.exists():
        try:
            plines = PROGRESS_FILE.read_text().strip().split('\n')
            progress_tail = '\n'.join(plines[-6:])
        except Exception:
            pass

    answer = await asyncio.to_thread(ask_brain, context, progress_tail)

    if not answer:
        await _speak_in_voice(VOICE_BRAIN_ERROR)
        return

    print(f"Brain answer: {answer}")
    # Voice first (the meeting hears it), text as a persistent record.
    if text_channel:
        try:
            await text_channel.send(f"💬 {answer}")
        except Exception as e:
            print(f"Error posting brain answer to channel: {e}")
    await _speak_in_voice(answer)


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
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await ctx.respond("I'm not in a voice channel.", ephemeral=True)
        return

    await ctx.respond("Leaving voice channel...", ephemeral=True)

    try:
        await _cleanup_voice(ctx.voice_client)
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

    try:
        bot.run(token)
    finally:
        # Synchronous cleanup after bot.run() returns (Ctrl+C or error).
        # Voice client is already disconnected by Pycord's shutdown.
        # We just need to stop Assembly AI threads.
        if _voice_sink:
            print("Stopping Assembly AI sessions...")
            _voice_sink.stop_transcription()
        print("Bobby shutdown complete.")


if __name__ == "__main__":
    run_bot()
