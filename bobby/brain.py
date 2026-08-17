#!/usr/bin/env python3
"""
Bobby Brain — conversational answers for "Hey Bobby, <anything>".

Turns Bobby from a voice-activated build button into a meeting participant:
utterances addressed to Bobby that are NOT the build/resume trigger get a
short spoken answer, grounded in the recent transcript (and, if an agent is
running, the tail of agent_progress.txt — so "Hey Bobby, how's it going?"
works mid-build).

v1 uses the `claude` CLI (no API key, no new billing — rides the user's
existing login) with a fast model. Swap _run_llm() for a direct API call if
the ~5-15s CLI latency ever feels too slow in a live meeting.
"""

import re
import subprocess
import tempfile

from bobby.agent_runner import _clean_agent_env
from bobby.prompts import BRAIN_PROMPT_TEMPLATE, BRAIN_PROGRESS_SECTION_TEMPLATE

# Fast model for meeting-speed answers; quality matters less than latency
# and the answers are 1-3 sentences anyway.
BRAIN_MODEL = "haiku"
BRAIN_TIMEOUT_SECONDS = 90


def build_brain_prompt(context, progress_tail=None):
    """Build the spoken-answer prompt from transcript context and optional
    agent progress tail."""
    progress_section = (
        BRAIN_PROGRESS_SECTION_TEMPLATE.format(progress=progress_tail)
        if progress_tail and progress_tail.strip()
        else ""
    )
    return BRAIN_PROMPT_TEMPLATE.format(
        context=context, progress_section=progress_section
    )


def strip_for_speech(text):
    """
    Make LLM output safe for TTS: drop markdown remnants and collapse
    whitespace. The prompt forbids markdown, but models drift — a spoken
    "asterisk asterisk" mid-demo is worse than a belt-and-suspenders strip.
    """
    text = re.sub(r"[*_`#>|]", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [label](url) -> label
    return " ".join(text.split()).strip()


def _run_llm(prompt):
    """
    One-shot LLM call via the claude CLI. Runs in a neutral cwd so the CLI
    has no workspace to wander; the prompt instructs answering from provided
    context only. Parent-session env is stripped (see agent_runner).
    """
    result = subprocess.run(
        ["claude", "-p", "--model", BRAIN_MODEL, prompt],
        capture_output=True,
        text=True,
        cwd=tempfile.gettempdir(),
        env=_clean_agent_env(),
        timeout=BRAIN_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"brain LLM call failed (rc={result.returncode}): {result.stderr.strip()[:200]}"
        )
    return result.stdout.strip()


def ask_brain(context, progress_tail=None):
    """
    Answer the most recent "Hey Bobby" utterance in `context`.

    Synchronous/blocking (5-15s via CLI) — callers on an event loop must use
    asyncio.to_thread. Returns the spoken answer, or None on any failure
    (caller decides the fallback voice line).
    """
    prompt = build_brain_prompt(context, progress_tail)
    try:
        answer = strip_for_speech(_run_llm(prompt))
        return answer or None
    except Exception as e:
        print(f"Brain error: {e}")
        return None
