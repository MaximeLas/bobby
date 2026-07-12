#!/usr/bin/env python3
"""
Automated tests for bobby.agent_runner prompt building.

Trigger detection, answer extraction, and context reading are covered by
test_orchestrator.py and test_brain.py; this module covers the agent prompt.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.agent_runner import build_agent_prompt


def test_prompt_contains_context():
    """The meeting context must be embedded in the agent prompt."""
    prompt = build_agent_prompt("[Max] Add a dark mode toggle please")
    assert "[Max] Add a dark mode toggle please" in prompt


def test_prompt_uses_default_dev_url():
    """Without an explicit dev_url, the config default must appear."""
    from bobby.config import DEV_SERVER_URL
    prompt = build_agent_prompt("some context")
    assert DEV_SERVER_URL in prompt, \
        f"Expected {DEV_SERVER_URL} in prompt"


def test_prompt_uses_explicit_dev_url():
    """An explicit dev_url must replace every hardcoded URL in the template."""
    prompt = build_agent_prompt("some context", dev_url="http://localhost:3000")
    assert "http://localhost:3000" in prompt
    assert "http://localhost:5173" not in prompt, \
        "Old hardcoded Vite URL leaked into the prompt"


def test_prompt_has_no_unfilled_placeholders():
    """All template placeholders must be filled after formatting."""
    prompt = build_agent_prompt("some context")
    assert "{context}" not in prompt
    assert "{dev_url}" not in prompt


ALL_TESTS = [
    ("Agent prompt: contains meeting context", test_prompt_contains_context),
    ("Agent prompt: default dev URL from config", test_prompt_uses_default_dev_url),
    ("Agent prompt: explicit dev URL replaces all", test_prompt_uses_explicit_dev_url),
    ("Agent prompt: no unfilled placeholders", test_prompt_has_no_unfilled_placeholders),
]
