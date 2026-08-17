#!/usr/bin/env python3
"""
Automated tests for the conversational brain (bobby/brain.py) and the
"converse" trigger route.

Does NOT call any LLM — the CLI call is mocked. Offline-safe.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.agent_runner import detect_trigger
from bobby import brain


# --- Trigger routing tests ---

def test_converse_basic():
    """Addressing Bobby without a build/resume phrase should route to converse."""
    assert detect_trigger("Hey Bobby, what do you think about this?") == "converse"


def test_converse_punctuation_and_case():
    """Normalization applies to the converse route too."""
    assert detect_trigger("HEY, BOBBY. How is it going?") == "converse"


def test_launch_takes_precedence_over_converse():
    """The launch phrase contains 'hey bobby' — it must still win."""
    assert detect_trigger("Hey Bobby, please build this: a footer") == "launch"


def test_resume_takes_precedence_over_converse():
    """Resume phrasing without 'hey bobby' still routes to resume."""
    assert detect_trigger("That should be blue. Thank you, Bobby!") == "resume"


def test_no_trigger_without_addressing_bobby():
    """Mentioning Bobby without 'hey bobby' should not trigger anything."""
    assert detect_trigger("I told Bobby about it yesterday") is None
    assert detect_trigger("let's discuss the roadmap") is None


# --- Prompt building tests ---

def test_prompt_contains_context():
    """The transcript context must be embedded in the prompt."""
    prompt = brain.build_brain_prompt("[Max] Hey Bobby, what time is it?")
    assert "[Max] Hey Bobby, what time is it?" in prompt


def test_prompt_without_progress_has_no_progress_section():
    """No progress tail -> no progress section in the prompt."""
    prompt = brain.build_brain_prompt("[Max] Hey Bobby, hello")
    assert "build task progress" not in prompt


def test_prompt_with_progress_includes_it():
    """A progress tail should appear in the prompt."""
    prompt = brain.build_brain_prompt(
        "[Max] Hey Bobby, how is the build going?",
        progress_tail="PROGRESS: → Adding dark mode toggle",
    )
    assert "PROGRESS: → Adding dark mode toggle" in prompt


# --- Speech stripping tests ---

def test_strip_markdown():
    """Markdown characters must not survive into spoken text."""
    assert brain.strip_for_speech("**Very** _nice_, `great` success!") == \
        "Very nice, great success!"


def test_strip_links_keeps_label():
    """Links collapse to their label."""
    assert brain.strip_for_speech("See [the app](http://localhost:5173) now") == \
        "See the app now"


def test_strip_collapses_whitespace():
    """Newlines and runs of spaces collapse to single spaces."""
    assert brain.strip_for_speech("One.\n\nTwo.   Three.") == "One. Two. Three."


# --- ask_brain behavior (mocked CLI) ---
# _api_available is forced False so these always exercise the CLI path,
# regardless of whether the test machine has ANTHROPIC_API_KEY set.

def test_ask_brain_success():
    """Happy path: CLI output is stripped and returned."""
    fake = MagicMock(returncode=0, stdout="Is going **very** nice!\n", stderr="")
    with patch.object(brain, "_api_available", return_value=False), \
         patch.object(brain.subprocess, "run", return_value=fake):
        assert brain.ask_brain("[Max] Hey Bobby, status?") == "Is going very nice!"


def test_ask_brain_failure_returns_none():
    """Non-zero CLI exit -> None (caller speaks the fallback line)."""
    fake = MagicMock(returncode=1, stdout="", stderr="boom")
    with patch.object(brain, "_api_available", return_value=False), \
         patch.object(brain.subprocess, "run", return_value=fake):
        assert brain.ask_brain("[Max] Hey Bobby, status?") is None


def test_ask_brain_empty_answer_returns_none():
    """Empty CLI output -> None, not an empty spoken line."""
    fake = MagicMock(returncode=0, stdout="   \n", stderr="")
    with patch.object(brain, "_api_available", return_value=False), \
         patch.object(brain.subprocess, "run", return_value=fake):
        assert brain.ask_brain("[Max] Hey Bobby, status?") is None


# --- API path and dispatch (mocked Anthropic client) ---

def test_api_unavailable_without_key():
    """No ANTHROPIC_API_KEY -> API path is off."""
    import os
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        assert brain._api_available() is False


def test_api_unavailable_without_package():
    """Key set but `anthropic` package missing -> API path is off."""
    import os
    import sys
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
         patch.dict(sys.modules, {"anthropic": None}):
        assert brain._api_available() is False


def test_dispatch_prefers_api():
    """When the API path is available, the CLI must not run."""
    cli = MagicMock()
    with patch.object(brain, "_api_available", return_value=True), \
         patch.object(brain, "_run_llm_api", return_value="**Very** nice answer."), \
         patch.object(brain, "_run_llm_cli", cli):
        assert brain.ask_brain("[Max] Hey Bobby, status?") == "Very nice answer."
        cli.assert_not_called()


def test_dispatch_api_failure_falls_back_to_cli():
    """An API error mid-meeting falls back to the CLI, not silence."""
    with patch.object(brain, "_api_available", return_value=True), \
         patch.object(brain, "_run_llm_api", side_effect=RuntimeError("401")), \
         patch.object(brain, "_run_llm_cli", return_value="CLI saves the day."):
        assert brain.ask_brain("[Max] Hey Bobby, status?") == "CLI saves the day."


def test_run_llm_api_extracts_text_blocks():
    """_run_llm_api joins text blocks and ignores non-text blocks."""
    import sys
    from types import SimpleNamespace

    blocks = [
        SimpleNamespace(type="thinking", thinking="hmm"),
        SimpleNamespace(type="text", text="Great "),
        SimpleNamespace(type="text", text="success!"),
    ]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = SimpleNamespace(content=blocks)
    fake_module = MagicMock()
    fake_module.Anthropic.return_value = fake_client

    with patch.dict(sys.modules, {"anthropic": fake_module}):
        assert brain._run_llm_api("prompt") == "Great success!"
        kwargs = fake_client.messages.create.call_args.kwargs
        assert kwargs["model"] == brain.BRAIN_API_MODEL
        assert kwargs["max_tokens"] == brain.BRAIN_API_MAX_TOKENS


ALL_TESTS = [
    ("Converse: basic 'hey bobby' routes to converse", test_converse_basic),
    ("Converse: punctuation and case normalized", test_converse_punctuation_and_case),
    ("Converse: launch phrase takes precedence", test_launch_takes_precedence_over_converse),
    ("Converse: resume phrase takes precedence", test_resume_takes_precedence_over_converse),
    ("Converse: no trigger without addressing Bobby", test_no_trigger_without_addressing_bobby),
    ("Prompt: contains transcript context", test_prompt_contains_context),
    ("Prompt: no progress section without progress", test_prompt_without_progress_has_no_progress_section),
    ("Prompt: includes progress tail when given", test_prompt_with_progress_includes_it),
    ("Speech: strips markdown", test_strip_markdown),
    ("Speech: strips links, keeps label", test_strip_links_keeps_label),
    ("Speech: collapses whitespace", test_strip_collapses_whitespace),
    ("ask_brain: success path strips and returns", test_ask_brain_success),
    ("ask_brain: CLI failure returns None", test_ask_brain_failure_returns_none),
    ("ask_brain: empty answer returns None", test_ask_brain_empty_answer_returns_none),
    ("API path: off without ANTHROPIC_API_KEY", test_api_unavailable_without_key),
    ("API path: off without anthropic package", test_api_unavailable_without_package),
    ("Dispatch: API preferred when available", test_dispatch_prefers_api),
    ("Dispatch: API failure falls back to CLI", test_dispatch_api_failure_falls_back_to_cli),
    ("API path: extracts text blocks from response", test_run_llm_api_extracts_text_blocks),
]
