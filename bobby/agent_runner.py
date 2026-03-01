#!/usr/bin/env python3
"""
Bobby Agent Runner - Shared agent logic

Pure agent/trigger logic shared between local mode (orchestrator.py) and
Discord mode (discord_bot.py). No TTS, no pause flags, no notifications —
each mode's controller handles I/O and announcements separately.
"""

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

    Args:
        text: Raw text to check for triggers

    Returns:
        "launch" if "hey bobby please build this" is found,
        "resume" if "thank you bobby" / "thanks bobby" is found,
        None if no trigger detected
    """
    normalized = normalize_text(text)

    if 'hey bobby please build this' in normalized:
        return "launch"
    elif 'thank you bobby' in normalized or 'thanks bobby' in normalized:
        return "resume"

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

def build_agent_prompt(context):
    """
    Build the system prompt for the Claude Code agent.

    Args:
        context: Recent meeting transcript or task description

    Returns:
        Complete prompt string
    """
    return f"""You are Bobby, an AI assistant helping in a live product meeting.

Recent meeting discussion:
{context}

Task: Build the feature requested in the discussion above.

IMPORTANT: The transcript may contain multiple speakers (Max, Michelle, Kevin) but without speaker labels.
Pay attention to conversational context to understand who is saying what and what the requirements are.

As you work, write LIVE updates to @agent_progress.txt in this format:
- PROGRESS: -> Doing something...
- PROGRESS:   ✓ Completed step
- QUESTION: Your question (then stop and wait)
- COMPLETE: Summary + URL

CRITICAL INSTRUCTIONS FOR PROGRESS UPDATES:

Write progress updates to @agent_progress.txt using EXACTLY this format:

1. FIRST: Immediately write this EXACT line: "PROGRESS: -> Starting task"
2. Do some work
3. Write ONE line: "PROGRESS:   ✓ [what you completed]"
4. Do more work
5. Write ONE line: "COMPLETE: [summary] at http://localhost:5173"

STRICT RULES:
- Each Write operation = EXACTLY ONE LINE starting with "PROGRESS:" or "COMPLETE:" or "QUESTION:"
- NO empty lines, NO numbered lists, NO markdown formatting
- ALWAYS use append mode (never overwrite the file)
- Write 3-5 updates total (not 20+)

Example - THREE separate Write operations:
  Write #1:  "PROGRESS: -> Starting task"
  Write #2:  "PROGRESS: -> Analyzing requirements"
  Write #3:  "PROGRESS:   ✓ Created component"
  Write #4:  "PROGRESS: -> Testing component"
  Write #5:  "PROGRESS:   ✓ Component tested"
  Write #6:  "COMPLETE: Feature live at http://localhost:5173"

WRONG (do NOT do this):
  - Writing empty lines
  - Writing "1. Task" or numbered lists
  - Writing multiple PROGRESS lines in one Write operation
  - Clearing or overwriting the file

If you need clarification, write QUESTION and stop.
Otherwise, complete the task autonomously.

Deploy to localhost (Vite will auto-reload).
Reference the full meeting transcript at @meeting_transcript.txt if you need more context."""


# --- Agent Launch/Resume ---

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

    print("Executing: claude -p --dangerously-skip-permissions [prompt]")
    print(f"Working directory: {workspace_dir}")
    print("Agent is now running...\n")

    try:
        result = subprocess.run(
            ['claude', '-p', '--dangerously-skip-permissions', prompt],
            capture_output=False,
            text=True,
            cwd=str(workspace_dir)
        )
        print(f"\nAgent process exited with code: {result.returncode}")
        return result.returncode

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        return -1
    except Exception as e:
        print(f"ERROR launching agent: {e}")
        return -1


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

Please continue with the task."""

    print("Executing: claude -p --continue [answer]")
    print("Agent is now running...\n")

    try:
        result = subprocess.run(
            ['claude', '-p', '--dangerously-skip-permissions', '--continue', prompt],
            capture_output=False,
            text=True,
            cwd=str(workspace_dir)
        )
        print(f"\nAgent process exited with code: {result.returncode}")
        return result.returncode

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        return -1
    except Exception as e:
        print(f"ERROR resuming agent: {e}")
        return -1
