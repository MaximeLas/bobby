#!/usr/bin/env python3
"""
Bobby Brain — conversational answers for "Hey Bobby, <anything>".

Turns Bobby from a voice-activated build button into a meeting participant:
utterances addressed to Bobby that are NOT the build/resume trigger get a
short spoken answer, grounded in the recent transcript (and, if an agent is
running, the tail of agent_progress.txt — so "Hey Bobby, how's it going?"
works mid-build).

Two LLM paths, picked automatically per call:
- Anthropic API (~1-3s): used when ANTHROPIC_API_KEY is set and the
  `anthropic` package is installed (`uv sync --extra brain`).
- `claude` CLI (~5-15s): the zero-config fallback — no API key, no new
  billing, rides the user's existing login. Also the safety net when an
  API call fails mid-meeting.
"""

import os
import re
import subprocess
import tempfile

from dotenv import load_dotenv

from bobby.agent_runner import _clean_agent_env
from bobby.prompts import BRAIN_PROMPT_TEMPLATE, BRAIN_PROGRESS_SECTION_TEMPLATE

# ANTHROPIC_API_KEY may live in .env alongside the other keys
load_dotenv()

# Fast model for meeting-speed answers; quality matters less than latency
# and the answers are 1-3 sentences anyway.
BRAIN_MODEL = "haiku"  # claude CLI model name
BRAIN_TIMEOUT_SECONDS = 90

# API path equivalents. Answers are capped small — the prompt demands
# 1-3 spoken sentences, so 300 tokens is generous headroom.
BRAIN_API_MODEL = "claude-haiku-4-5"
BRAIN_API_TIMEOUT_SECONDS = 30
BRAIN_API_MAX_TOKENS = 300


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


def _api_available():
    """
    True when the direct Anthropic API path can be used: ANTHROPIC_API_KEY
    is set AND the optional `anthropic` package is installed.

    Checked per call (not at import) so a key added to the environment
    mid-session takes effect without a restart.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _run_llm_api(prompt):
    """
    One-shot LLM call via the Anthropic API (~1-3s vs ~5-15s for the CLI).

    Any failure (auth, network, rate limit) raises — _run_llm catches and
    falls back to the CLI, so a bad key can't silence Bobby mid-meeting.
    """
    import anthropic

    client = anthropic.Anthropic(
        timeout=BRAIN_API_TIMEOUT_SECONDS,
        max_retries=1,  # a meeting answer that arrives late is worthless
    )
    response = client.messages.create(
        model=BRAIN_API_MODEL,
        max_tokens=BRAIN_API_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    return text.strip()


def _run_llm_cli(prompt):
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


def _run_llm(prompt):
    """
    Dispatch to the fastest available LLM path: API first, CLI fallback.
    """
    if _api_available():
        try:
            return _run_llm_api(prompt)
        except Exception as e:
            print(f"Brain API call failed ({e}); falling back to CLI")
    return _run_llm_cli(prompt)


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
