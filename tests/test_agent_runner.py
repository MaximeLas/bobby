#!/usr/bin/env python3
"""
Automated tests for bobby.agent_runner prompt building and command construction.

Trigger detection, answer extraction, and context reading are covered by
test_orchestrator.py and test_brain.py; this module covers the agent prompt and
the `claude` argv Bobby actually spawns. No agent is ever launched: Popen is
stubbed, so these stay offline and free.
"""

import importlib
import io
import os
import sys
import tempfile
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.agent_runner import build_agent_prompt, launch_agent, resume_agent


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


# --- Launch/resume command construction ---

BASE_CMD = ['claude', '-p', '--dangerously-skip-permissions']
LEAN_FLAGS = ('--strict-mcp-config', '--setting-sources', '--disable-slash-commands')


@contextmanager
def _config_env(**overrides):
    """Reload bobby.config under env overrides (None unsets), then restore."""
    from bobby import config

    saved = {name: os.environ.get(name) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        importlib.reload(config)
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        importlib.reload(config)


def _captured_cmd(run, *args):
    """Run a launch/resume path with Popen stubbed; return the argv it built."""
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        proc = MagicMock()
        proc.wait.return_value = 0
        return proc

    with patch("bobby.agent_runner.subprocess.Popen", side_effect=fake_popen):
        with redirect_stdout(io.StringIO()):
            run(*args)

    return captured["cmd"]


def _launch_cmd():
    with tempfile.TemporaryDirectory() as tmp:
        return _captured_cmd(
            launch_agent, "[Max] Add a dark mode toggle", tmp,
            Path(tmp) / "agent_progress.txt",
        )


def _resume_cmd():
    with tempfile.TemporaryDirectory() as tmp:
        return _captured_cmd(resume_agent, "use blue", tmp)


def test_launch_command_is_lean_by_default():
    """With no env set, the agent launches without the user's skills/MCP/settings."""
    with _config_env(BOBBY_LEAN_AGENT=None):
        cmd = _launch_cmd()

    assert cmd[:3] == BASE_CMD, f"base command changed: {cmd[:3]}"
    for flag in LEAN_FLAGS:
        assert flag in cmd, f"{flag} missing from lean launch: {cmd[:-1]}"
    assert cmd[cmd.index('--setting-sources') + 1] == '', \
        "--setting-sources must be followed by an empty value"
    assert cmd[-1].startswith("You are Bobby"), "prompt must stay the last argument"


def test_launch_command_without_lean_flags():
    """BOBBY_LEAN_AGENT=0 restores the inherited-config command exactly."""
    with _config_env(BOBBY_LEAN_AGENT="0"):
        cmd = _launch_cmd()

    assert cmd[:3] == BASE_CMD
    assert len(cmd) == 4, f"expected base command + prompt only, got: {cmd[:-1]}"
    for flag in LEAN_FLAGS:
        assert flag not in cmd, f"{flag} leaked in with lean mode off"


def test_resume_command_carries_lean_flags():
    """The resume path must be launched as leanly as the initial launch."""
    with _config_env(BOBBY_LEAN_AGENT=None):
        cmd = _resume_cmd()

    assert cmd[:3] == BASE_CMD
    for flag in LEAN_FLAGS:
        assert flag in cmd, f"{flag} missing from lean resume: {cmd[:-1]}"
    assert cmd[-2] == '--continue', f"--continue must precede the answer: {cmd[:-1]}"
    assert cmd[-1].startswith("The answer to your question is: use blue")


def test_no_budget_flag_by_default():
    """Without BOBBY_AGENT_MAX_BUDGET_USD there is no spend cap flag."""
    with _config_env(BOBBY_AGENT_MAX_BUDGET_USD=None):
        cmd = _launch_cmd()

    assert '--max-budget-usd' not in cmd


def test_budget_flag_when_env_set():
    """BOBBY_AGENT_MAX_BUDGET_USD becomes --max-budget-usd on both paths."""
    with _config_env(BOBBY_AGENT_MAX_BUDGET_USD="2.50"):
        launch = _launch_cmd()
        resume = _resume_cmd()

    for cmd in (launch, resume):
        assert cmd[cmd.index('--max-budget-usd') + 1] == "2.50", \
            f"budget value not passed through: {cmd[:-1]}"


ALL_TESTS = [
    ("Agent prompt: contains meeting context", test_prompt_contains_context),
    ("Agent prompt: default dev URL from config", test_prompt_uses_default_dev_url),
    ("Agent prompt: explicit dev URL replaces all", test_prompt_uses_explicit_dev_url),
    ("Agent prompt: no unfilled placeholders", test_prompt_has_no_unfilled_placeholders),
    ("Launch command: lean flags on by default", test_launch_command_is_lean_by_default),
    ("Launch command: BOBBY_LEAN_AGENT=0 drops them", test_launch_command_without_lean_flags),
    ("Resume command: carries lean flags + --continue", test_resume_command_carries_lean_flags),
    ("Budget flag: absent by default", test_no_budget_flag_by_default),
    ("Budget flag: set from BOBBY_AGENT_MAX_BUDGET_USD", test_budget_flag_when_env_set),
]
