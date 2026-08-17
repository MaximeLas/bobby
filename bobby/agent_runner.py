#!/usr/bin/env python3
"""
Bobby Agent Runner - Shared agent logic

Pure agent/trigger logic shared between local mode (orchestrator.py) and
Discord mode (discord_bot.py). No TTS, no pause flags, no notifications —
each mode's controller handles I/O and announcements separately.
"""

import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path


# --- Trigger Detection ---

def normalize_text(text):
    """
    Normalize text for trigger matching.

    Lowercases, strips punctuation (commas, periods), collapses whitespace.
    Example: "Hey, Bobby, please build this." → "hey bobby please build this"
    """
    return ' '.join(text.lower().replace(',', '').replace('.', '').split())


def detect_trigger(text):
    """
    Detect a trigger phrase in text.

    Stateless — does NOT manage debounce or file position. Caller handles that.

    Order matters: the launch phrase contains "hey bobby", so it must be
    checked before the generic converse route.

    Args:
        text: Raw text to check for triggers

    Returns:
        "launch" if "hey bobby please build this" is found,
        "resume" if "thank you bobby" / "thanks bobby" is found,
        "converse" if Bobby is addressed ("hey bobby") without either
            trigger phrase — the utterance goes to the brain for a spoken
            answer (see bobby/brain.py),
        None if no trigger detected
    """
    normalized = normalize_text(text)

    if 'hey bobby please build this' in normalized:
        return "launch"
    elif 'thank you bobby' in normalized or 'thanks bobby' in normalized:
        return "resume"
    elif 'hey bobby' in normalized:
        return "converse"

    return None


# --- Answer Extraction ---

def extract_answer(text):
    """
    Extract answer between question and 'thank you bobby'.

    Finds the last occurrence of "thank you bobby" (or variants) and returns
    the last 1-3 non-empty lines before it.

    Args:
        text: Text containing the answer and trigger phrase

    Returns:
        Extracted answer text
    """
    lower_text = text.lower()

    # Find "thank you bobby" trigger (last occurrence)
    thank_you_variants = ['thank you, bobby', 'thank you bobby', 'thanks bobby']
    trigger_index = -1

    for variant in thank_you_variants:
        idx = lower_text.rfind(variant)
        if idx != -1:
            trigger_index = idx
            break

    if trigger_index == -1:
        return text.strip()

    before_trigger = text[:trigger_index]
    lines = before_trigger.split('\n')
    non_empty = [line.strip() for line in lines if line.strip()]

    answer_lines = non_empty[-3:] if len(non_empty) >= 3 else non_empty
    return '\n'.join(answer_lines).strip()


# --- Context Reading ---

def get_recent_context(transcript_file, lines=15):
    """
    Get last N lines from transcript for agent context.

    Args:
        transcript_file: Path to the transcript file
        lines: Number of recent lines to retrieve

    Returns:
        String containing recent transcript lines
    """
    try:
        with open(transcript_file, 'r') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(recent)
    except FileNotFoundError:
        return ""
    except Exception as e:
        print(f"Error reading transcript: {e}")
        return ""


# --- Agent Prompt ---

def build_agent_prompt(context, dev_url=None):
    """
    Build the system prompt for the Claude Code agent.

    Args:
        context: Recent meeting transcript or task description
        dev_url: Dev-server URL the agent reports in COMPLETE: lines
            (defaults to config.DEV_SERVER_URL / $BOBBY_DEV_URL)

    Returns:
        Complete prompt string
    """
    from bobby.prompts import AGENT_PROMPT_TEMPLATE
    if dev_url is None:
        from bobby.config import DEV_SERVER_URL
        dev_url = DEV_SERVER_URL
    return AGENT_PROMPT_TEMPLATE.format(context=context, dev_url=dev_url)


# --- Agent Launch/Resume ---

def _clean_agent_env():
    """
    Environment for the nested `claude` CLI, with parent-session variables
    stripped.

    If Bobby is started from a terminal that lives inside a Claude Code
    session, vars like ANTHROPIC_BASE_URL and CLAUDE_CODE_* leak into the
    agent subprocess and break its authentication (401) or route it to the
    parent session's endpoint. Stripping them makes the agent authenticate
    with the user's own stored credentials no matter where Bobby was launched.
    """
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("ANTHROPIC_", "CLAUDE_CODE_", "CLAUDE_AGENT_")) or key in (
            "CLAUDECODE",
            "CLAUDE_EFFORT",
        ):
            env.pop(key)
    return env


def _agent_flags():
    """
    Extra `claude` flags shared by the launch and resume paths.

    Read at call time (not import time) so a reloaded/patched config takes
    effect — see bobby.config for what lean mode drops and how to roll it back.

    Returns:
        list[str]: flags to insert before the prompt argument
    """
    from bobby.config import AGENT_MAX_BUDGET_USD, LEAN_AGENT_ENABLED

    flags = []
    if LEAN_AGENT_ENABLED:
        flags += [
            '--strict-mcp-config',      # ignore the launching user's MCP servers
            '--setting-sources', '',    # no user/project/local settings
            '--disable-slash-commands',  # no skills
        ]
    if AGENT_MAX_BUDGET_USD:
        flags += ['--max-budget-usd', str(AGENT_MAX_BUDGET_USD)]
    return flags


# Handle to the currently running agent subprocess, so a controller
# (e.g. /bobby stop in Discord) can terminate it. Only one agent runs at a
# time by design; assignment happens in the thread running launch/resume.
_active_proc = None


def stop_agent(timeout=5):
    """
    Terminate the currently running agent subprocess, if any.

    Returns True if a running agent was found and stopped, False otherwise.
    Safe to call from any thread.
    """
    global _active_proc
    proc = _active_proc
    if proc is None or proc.poll() is not None:
        return False

    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    return True


def write_session_header(progress_file):
    """Write a session marker to the progress file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(progress_file, 'a') as f:
            f.write(f"\n=== New Agent Session: {timestamp} ===\n\n")
    except Exception as e:
        print(f"Error writing to progress file: {e}")


def launch_agent(context, workspace_dir, progress_file):
    """
    Launch Claude Code agent with task from meeting context.

    Synchronous/blocking — caller is responsible for threading if needed.

    Args:
        context: Recent meeting transcript or task description
        workspace_dir: Directory for the agent to work in
        progress_file: Path to agent_progress.txt

    Returns:
        int: Process return code, or -1 on error
    """
    write_session_header(progress_file)

    prompt = build_agent_prompt(context)

    cmd = ['claude', '-p', '--dangerously-skip-permissions'] + _agent_flags() + [prompt]

    print(f"Executing: {shlex.join(cmd[:-1])} [prompt]")
    print(f"Working directory: {workspace_dir}")
    print("Agent is now running...\n")

    global _active_proc
    try:
        _active_proc = subprocess.Popen(
            cmd,
            text=True,
            cwd=str(workspace_dir),
            env=_clean_agent_env(),
        )
        returncode = _active_proc.wait()
        print(f"\nAgent process exited with code: {returncode}")
        return returncode

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        return -1
    except Exception as e:
        print(f"ERROR launching agent: {e}")
        return -1
    finally:
        _active_proc = None


def resume_agent(answer, workspace_dir):
    """
    Resume Claude Code with answer to question.

    Synchronous/blocking — caller is responsible for threading if needed.

    Args:
        answer: Answer to the agent's question
        workspace_dir: Directory for the agent to work in

    Returns:
        int: Process return code, or -1 on error
    """
    prompt = f"""The answer to your question is: {answer}

Please continue with the task. Write progress updates to @agent_progress.txt using APPEND mode only (never overwrite). Use the same format: PROGRESS: and COMPLETE: prefixes."""

    cmd = (['claude', '-p', '--dangerously-skip-permissions']
           + _agent_flags() + ['--continue', prompt])

    print(f"Executing: {shlex.join(cmd[:-1])} [answer]")
    print("Agent is now running...\n")

    global _active_proc
    try:
        _active_proc = subprocess.Popen(
            cmd,
            text=True,
            cwd=str(workspace_dir),
            env=_clean_agent_env(),
        )
        returncode = _active_proc.wait()
        print(f"\nAgent process exited with code: {returncode}")
        return returncode

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        return -1
    except Exception as e:
        print(f"ERROR resuming agent: {e}")
        return -1
    finally:
        _active_proc = None
